#!/usr/bin/env python
##
##  ari
##
##  the realraum audience response indicator
##
##
##  Copyright (C) 2015 Christian Pointner <equinox@spreadspace.org>
##
##  This file is part of ari.
##
##  ari is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  any later version.
##
##  ari is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with ari. If not, see <http://www.gnu.org/licenses/>.
##

import sys
import getopt

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject

def clamp(x, min, max):
    if x < min:
        return min
    elif x > max:
        return max
    return x

class R3Ari():
    def __init__(self, device, channels):
        GObject.threads_init()
        Gst.init(None)
        self.device_ = device
        self.channels_ = channels
        self.mainloop_ = GObject.MainLoop()
        self.pipeline_ = None

    def error(self, message, arg=None):
        print "ERROR: %s (%s)" % (message, arg)

    def on_message(self, bus, message):
        s = message.get_structure()
        if s.get_name() == 'level':
            sys.stdout.write("\r")
            for i in range(0, len(s['peak'])):
                decay = clamp(s['decay'][i], -90.0, 0.0)
                peak = clamp(s['peak'][i], -90.0, 0.0)
                # if peak > decay:
                #     print "ERROR: peak bigger than decay!"

                sys.stdout.write("channel %d: %3.2f / %3.2f,   " % (i, decay, peak))

            sys.stdout.flush()

        return True

    def run(self):
        try:
            s = 'alsasrc device=%s ! audio/x-raw,channels=%i ! level message=true ! fakesink' % (self.device_, self.channels_)
            self.pipeline_ = Gst.parse_launch(s)
            self.pipeline_.get_bus().add_signal_watch()
            self.watch_id_ = self.pipeline_.get_bus().connect('message::element', self.on_message)
            self.pipeline_.set_state(Gst.State.PLAYING)

            self.mainloop_.run()

        except GObject.GError, e:
            self.error('Could not create pipeline', e.message)
        except KeyboardInterrupt:
            pass
        finally:
            if self.pipeline_:
                self.pipeline_.get_bus().disconnect(self.watch_id_)
                self.pipeline_.get_bus().remove_signal_watch()
                self.pipeline_.set_state(Gst.State.NULL)

if __name__ == '__main__':
    usage = '''realraum Audience Reaction Indicator.
Usage:
    vumeter.py --device <alsa device> --channels <num>

Options:
    -h, --help              this help message.
    -v, --version           version info.
    --device=N              the alsa device to open (default: 'default').
    --channels=N            number of audio channels (default: 2).
'''

    device = 'default'
    channels = 2
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hv", ["help", "version", "device=", "channels=" ])
        for o, a in opts:
            if o in ("-h", "--help"):
                print >> sys.stderr, usage
                sys.exit(0)
            elif o in ("-v", "--version"):
                print >> sys.stderr, "Gstreamer Version %d.%d.%d.%d" % Gst.version()
                sys.exit(0)
            elif o == "--device":
                device = a
            elif o == "--channels":
                channels = int(a)

        if len(args) > 1:
            raise getopt.GetoptError('Too many arguments')

    except getopt.GetoptError, msg:
        print >> sys.stderr, "ERROR: %s" % msg
        print >> sys.stderr, usage
        sys.exit(2)


    a = R3Ari(device, channels)
    a.run()
