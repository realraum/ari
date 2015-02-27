#!/usr/bin/env python
##
##  r3ari
##
##
##  Copyright (C) 2015 Christian Pointner <equinox@spreadspace.org>
##
##
##  This file is part of r3ari.
##
##  r3ari is free software: you can redistribute it and/or modify
##  it under the terms of the GNU General Public License as published by
##  the Free Software Foundation, either version 3 of the License, or
##  any later version.
##
##  r3ari is distributed in the hope that it will be useful,
##  but WITHOUT ANY WARRANTY; without even the implied warranty of
##  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
##  GNU General Public License for more details.
##
##  You should have received a copy of the GNU General Public License
##  along with r3ari. If not, see <http://www.gnu.org/licenses/>.
##

import sys
import gobject

import pygst
pygst.require('0.10')
import gst


def clamp(x, min, max):
    if x < min:
        return min
    elif x > max:
        return max
    return x

class R3Ari():
    def __init__(self):
        self.mainloop_ = gobject.MainLoop()

    def error(self, message, arg=None):
        print "ERROR: %s (%s)" % (message, arg)

    def on_message(self, bus, message):
        if  message.structure.get_name() == 'level':
            s = message.structure
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
            s = 'alsasrc ! audio/x-raw-int,channels=2 ! level message=true ! fakesink'
            self.pipeline_ = gst.parse_launch(s)
            self.pipeline_.get_bus().add_signal_watch()
            self.watch_id_ = self.pipeline_.get_bus().connect('message::element', self.on_message)
            self.pipeline_.set_state(gst.STATE_PLAYING)

            self.mainloop_.run()

        except gobject.GError, e:
            self.error('Could not create pipeline', e.__str__)
        except KeyboardInterrupt:
            pass
        finally:
            self.pipeline_.get_bus().disconnect(self.watch_id_)
            self.pipeline_.get_bus().remove_signal_watch()
            self.pipeline_.set_state(gst.STATE_NULL)

if __name__ == '__main__':
    a = R3Ari()
    a.run()
