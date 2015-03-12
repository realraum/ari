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

def lvl_clamp(x):
    if x < -90.0:
        return -90.0
    elif x > 0.0:
        return 0.0
    return x

def lvl_conv(x):
    x += 90.0
    return x/90.0

class R3Ari():
    def __init__(self):
        GObject.threads_init()
        Gst.init(None)
        GObject.set_prgname("r3 audience response indicator")
        self.mainloop_ = GObject.MainLoop()
        self.pipeline_ = None
        self.watch_id_ = None

        self.video_width_ = 1280
        self.video_height_ = 720
        self.meter_width_ = 0.75*self.video_width_
        self.meter_height_ = 0.03*self.video_height_
        self.meter_spacing_ =  0.4*self.meter_height_
        self.threshold_ = 0.3

    def info(self, message, arg=None):
        print "INFO: %s (%s)" % (message, arg)

    def warn(self, message, arg=None):
        print "WARNING: %s (%s)" % (message, arg)

    def error(self, message, arg=None):
        print "ERROR: %s (%s)" % (message, arg)

    def on_message(self, bus, message):
        t = message.type
        if t == Gst.MessageType.EOS:
            self.info("got EOS - closing application")
            self.mainloop_.quit()
        elif t == Gst.MessageType.INFO:
            self.info(message.parse_info())
        elif t == Gst.MessageType.WARNING:
            self.warn(message.parse_warning())
        elif t == Gst.MessageType.ERROR:
            self.error(message.parse_error())
            self.mainloop_.quit()
        elif t == Gst.MessageType.ELEMENT:
            s = message.get_structure()
            if s.get_name() == 'level':
                sys.stdout.write("\r")
                l = lvl_clamp(s['peak'][0])
                lp = lvl_clamp(s['decay'][0])
                r = lvl_clamp(s['peak'][1])
                rp = lvl_clamp(s['decay'][1])
                sys.stdout.write("left: %3.2f / %3.2f, right: %3.2f / %3.2f  " % (l, lp, r, rp))
                sys.stdout.flush()
                self.updateMeter(lvl_conv(l), lvl_conv(lp), lvl_conv(r), lvl_conv(rp))

        return True

    def run(self):
        try:
            self.pipeline_ = Gst.Pipeline.new()

	    source = "tcpclientsrc host=localhost port=1234 ! queue ! gdpdepay"
            source_bin = Gst.parse_bin_from_description(source, "source")
            self.pipeline_.add(source_bin)
            decoder = Gst.ElementFactory.make("decodebin")
            self.pipeline_.add(decoder)


            q_vin = Gst.ElementFactory.make("queue")
            self.pipeline_.add(q_vin)
            conv_vin = Gst.ElementFactory.make("videoconvert")
            self.pipeline_.add(conv_vin)

            scale_vin = Gst.ElementFactory.make("videoscale")
            self.pipeline_.add(scale_vin)
            cf_vin = Gst.ElementFactory.make("capsfilter")
            caps_vin = Gst.Caps.from_string("video/x-raw,width=%i,height=%i" % (self.video_width_, self.video_height_))
            cf_vin.set_property("caps", caps_vin)
            self.pipeline_.add(cf_vin)

            q_vscaled = Gst.ElementFactory.make("queue")
            self.pipeline_.add(q_vscaled)
            conv_vscaled = Gst.ElementFactory.make("videoconvert")
            self.pipeline_.add(conv_vscaled)
            self.overlay_ = Gst.ElementFactory.make("rsvgoverlay")
            self.overlay_.set_property("data", self.getVumeterSVG(0, 0, 0, 0))
            self.pipeline_.add(self.overlay_)
            conv_vout = Gst.ElementFactory.make("videoconvert")

            self.pipeline_.add(conv_vout)
            vsink = Gst.ElementFactory.make("xvimagesink")
            self.pipeline_.add(vsink)


            q_vin.link(conv_vin)
            conv_vin.link(scale_vin)
            scale_vin.link(cf_vin)
            cf_vin.link(q_vscaled)
            q_vscaled.link(conv_vscaled)
            conv_vscaled.link(self.overlay_)
            self.overlay_.link(conv_vout)
            conv_vout.link(vsink)



            q_ain = Gst.ElementFactory.make("queue")
            self.pipeline_.add(q_ain)
            conv_ain = Gst.ElementFactory.make("audioconvert")
            self.pipeline_.add(conv_ain)
            level = Gst.ElementFactory.make("level", "level")
            level.set_property("message", True)
            self.pipeline_.add(level)
            asink = Gst.ElementFactory.make("fakesink")
            self.pipeline_.add(asink)

            q_ain.link(conv_ain)
            conv_ain.link(level)
            level.link(asink)


            source_bin.link(decoder)
            sink_pads = {"video": q_vin.get_static_pad("sink"),
                         "audio": q_ain.get_static_pad("sink")}
            decoder.connect("pad-added", self.decoder_callback, sink_pads)


            self.pipeline_.get_bus().add_signal_watch()
            self.watch_id_ = self.pipeline_.get_bus().connect('message', self.on_message)
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


    def decoder_callback(self, decoder, srcpad, sinks):
        for name, sinkpad in sinks.items():
            if sinkpad.is_linked():
                continue

            if sinkpad.can_link(srcpad):
                srcpad.link(sinkpad)


    def getVumeterSVG(self, l, lp, r, rp):
        avg = (lp + rp) / 2

        svg = "<svg>\n"
        svg += "  <defs>\n"
        svg += "    <linearGradient id='vumeter' x1='0%' y1='0%' x2='100%' y2='0%'>\n"
        if avg > self.threshold_:
            svg += "      <stop offset='0%' style='stop-color:rgb(0,255,0);stop-opacity:1' />\n"
            svg += "      <stop offset='100%' style='stop-color:rgb(255,0,0);stop-opacity:1' />\n"
        else:
            svg += "      <stop offset='0%' style='stop-color:rgb(42,42,42);stop-opacity:1' />\n"
            svg += "      <stop offset='100%' style='stop-color:rgb(200,200,200);stop-opacity:1' />\n"
        svg += "    </linearGradient>\n"
        svg += "  </defs>\n"

        box_w = self.meter_width_ + 2*self.meter_spacing_
        box_h = 2*self.meter_height_ + 3*self.meter_spacing_
        box_x = (self.video_width_ - box_w)/2
        box_y = self.meter_spacing_

        svg += "  <rect x='%i' y='%i' rx='%i' ry='%i' width='%i' height='%i' style='fill:black;opacity:0.3' />\n" %(
            box_x, box_y, self.meter_spacing_, self.meter_spacing_, box_w, box_h)
        svg += "  <line x1='%i' y1='%i' x2='%i' y2='%i' style='stroke:white;stroke-width:3' />\n" %(
            box_x + self.meter_width_*self.threshold_, box_y + 0.5*self.meter_spacing_,
            box_x + self.meter_width_*self.threshold_, box_y + 2.5*self.meter_spacing_ + 2*self.meter_height_)

        svg += "  <rect x='%i' y='%i' width='%i' height='%i' style='fill:url(#vumeter);opacity:0.9' />\n" %(
            box_x + self.meter_spacing_, box_y + self.meter_spacing_, self.meter_width_*l, self.meter_height_)
        svg += "  <line x1='%i' y1='%i' x2='%i' y2='%i' style='stroke:rgb(255,0,0);stroke-width:5' />\n" %(
            box_x + self.meter_width_*lp, box_y + 0.75*self.meter_spacing_, box_x + self.meter_width_*lp, box_y + 1.25*self.meter_spacing_ + self.meter_height_)

        svg += "  <rect x='%i' y='%i' width='%i' height='%i' style='fill:url(#vumeter);opacity:0.9' />\n" %(
            box_x + self.meter_spacing_, box_y + self.meter_height_ + 2*self.meter_spacing_, self.meter_width_*r, self.meter_height_)
        svg += "  <line x1='%i' y1='%i' x2='%i' y2='%i' style='stroke:rgb(255,0,0);stroke-width:5' />\n" %(
            box_x + self.meter_width_*rp, box_y + self.meter_height_ + 1.75*self.meter_spacing_,
            box_x + self.meter_width_*rp, box_y + 2*self.meter_height_ + 2.25*self.meter_spacing_)

        svg += "</svg>\n"

        return svg

    def updateMeter(self, l, lp, r, rp):
        self.overlay_.set_property("data", self.getVumeterSVG(l, lp, r, rp))
        return True



if __name__ == '__main__':
    a = R3Ari()
    a.run()
