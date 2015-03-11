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


class R3Ari():
    def __init__(self):
        GObject.threads_init()
        Gst.init(None)
        self.mainloop_ = GObject.MainLoop()
        self.pipeline_ = None
        self.watch_id_ = None
        self.size_ = 10

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
            s = 'videotestsrc is-live=true  !xvimagesink' % ()
            self.pipeline_ = Gst.Pipeline.new()

            source = Gst.ElementFactory.make("videotestsrc")
            source.set_property("is-live", True)
            self.pipeline_.add(source)
            filter = Gst.ElementFactory.make("capsfilter")
            filter.set_property("caps", Gst.Caps.from_string("video/x-raw,format=I420,width=1280,height=720,framerate=50/1"))
            self.pipeline_.add(filter)
            conv1 = Gst.ElementFactory.make("videoconvert")
            self.pipeline_.add(conv1)
            q1 = Gst.ElementFactory.make("queue")
            self.pipeline_.add(q1)

            overlay = Gst.ElementFactory.make("rsvgoverlay")
            overlay.set_property("data", "<svg><circle cx='320' cy='240' r='%i' fill='red' /></svg>" % self.size_)
            self.pipeline_.add(overlay)
            GObject.timeout_add(20, self.updateMeter, overlay)

            conv2 = Gst.ElementFactory.make("videoconvert")
            self.pipeline_.add(conv2)
            sink = Gst.ElementFactory.make("xvimagesink")
            self.pipeline_.add(sink)

            source.link(filter)
            filter.link(q1)
            q1.link(conv1)

            conv1.link(overlay)
            overlay.link(conv2)

            conv2.link(sink)

            self.pipeline_.get_bus().add_signal_watch()
            self.watch_id_ = self.pipeline_.get_bus().connect('message::element', self.on_message)
            self.pipeline_.set_state(Gst.State.PLAYING)

            self.mainloop_.run()

        except GObject.GError, e:
            self.error('Could not create pipeline', e.message)
        except KeyboardInterrupt:
            pass
        finally:
            if self.pipeline_ and self.watch_id_:
                self.pipeline_.get_bus().disconnect(self.watch_id_)
                self.pipeline_.get_bus().remove_signal_watch()
                self.pipeline_.set_state(Gst.State.NULL)

    def updateMeter(self, overlay):
        self.size_ = self.size_ + 1 if self.size_ < 250 else 10
        overlay.set_property("data", "<svg><circle cx='320' cy='240' r='%i' fill='red' /></svg>" % self.size_)
        return True

if __name__ == '__main__':
    a = R3Ari()
    a.run()
