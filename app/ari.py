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

        self.video_width_ = 1920
        self.video_height_ = 1080
        self.meter_width_ = 1200
        self.meter_height_ = 23
        self.meter_spacing_ =  12

        self.l = 0.3
        self.r = 0.7

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

            source = "videotestsrc is-live=true"
            caps = "video/x-raw,width=%i,height=%i,framerate=50/2" % (self.video_width_, self.video_height_)
            source_bin = Gst.parse_bin_from_description("%s ! %s ! identity name=videosrc" % (source, caps), "source")
            self.pipeline_.add(source_bin)

            conv1 = Gst.ElementFactory.make("videoconvert")
            self.pipeline_.add(conv1)
            q1 = Gst.ElementFactory.make("queue")
            self.pipeline_.add(q1)

            overlay = Gst.ElementFactory.make("rsvgoverlay")
            overlay.set_property("data", self.getVumeterSVG(0, 0, 0, 0))
            self.pipeline_.add(overlay)
            GObject.timeout_add(20, self.updateMeter, overlay)

            conv2 = Gst.ElementFactory.make("videoconvert")
            self.pipeline_.add(conv2)
            sink = Gst.ElementFactory.make("xvimagesink")
            self.pipeline_.add(sink)

            source_bin.link(q1)
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

    def getVumeterSVG(self, l, lp, r, rp):
        svg = "<svg>\n"
        svg += "  <defs>\n"
        svg += "    <linearGradient id='vumeter' x1='0%' y1='0%' x2='100%' y2='0%'>\n"
        svg += "      <stop offset='0%' style='stop-color:rgb(0,255,0);stop-opacity:1' />\n"
        svg += "      <stop offset='100%' style='stop-color:rgb(255,0,0);stop-opacity:1' />\n"
        svg += "    </linearGradient>\n"
        svg += "  </defs>\n"

        box_w = self.meter_width_ + 2*self.meter_spacing_
        box_h = 2*self.meter_height_ + 3*self.meter_spacing_
        box_x = (self.video_width_ - box_w)/2
        box_y = self.meter_spacing_

        svg += "  <rect x='%i' y='%i' rx='%i' ry='%i' width='%i' height='%i' style='fill:black;opacity:0.3' />\n" %(
            box_x, box_y, self.meter_spacing_, self.meter_spacing_, box_w, box_h)

        svg += "  <rect x='%i' y='%i' width='%i' height='%i' style='fill:url(#vumeter);opacity:0.9' />\n" %(
            box_x + self.meter_spacing_, box_y + self.meter_spacing_, self.meter_width_*l, self.meter_height_)
        svg += "  <line x1='%i' y1='%i' x2='%i' y2='%i' style='stroke:rgb(255,0,0);stroke-width:3' />\n" %(
            box_x + self.meter_width_*lp, box_y + self.meter_spacing_, box_x + self.meter_width_*lp, box_y + self.meter_spacing_ + self.meter_height_)

        svg += "  <rect x='%i' y='%i' width='%i' height='%i' style='fill:url(#vumeter);opacity:0.9' />\n" %(
            box_x + self.meter_spacing_, box_y + self.meter_height_ + 2*self.meter_spacing_, self.meter_width_*r, self.meter_height_)
        svg += "  <line x1='%i' y1='%i' x2='%i' y2='%i' style='stroke:rgb(255,0,0);stroke-width:3' />\n" %(
            box_x + self.meter_width_*rp, box_y + self.meter_height_ + 2*self.meter_spacing_,
            box_x + self.meter_width_*rp, box_y + 2*self.meter_spacing_ + 2*self.meter_height_)

        svg += "</svg>\n"

        return svg

    def updateMeter(self, overlay):
        self.l += 0.01
        if self.l > 0.9:
            self.l = 0.0
        lp = self.l + 0.1

        self.r += 0.01
        if self.r > 0.9:
            self.r = 0.0
        rp = self.r + 0.1

        overlay.set_property("data", self.getVumeterSVG(self.l, lp, self.r, rp))
        return True

if __name__ == '__main__':
    a = R3Ari()
    a.run()
