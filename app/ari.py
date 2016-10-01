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
from enum import Enum

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import GObject
from gi.repository import Gdk
from gi.repository import GdkX11
from gi.repository import Gtk
from gi.repository import Gst
from gi.repository import GstVideo

class State(Enum):
    idle = 1
    started = 2
    running = 3
    finished = 4

class R3Ari():

    def __init__(self, host="localhost", port=1234, width=1280, height=720,
                 serial_device='/dev/ttyACM0', threshold=0.60, ttl=300000000, falloff=25):
        GObject.threads_init()
        Gdk.init([])
        Gtk.init([])
        Gst.init([])

        self.win_ = None
        self.pipeline_ = None
        self.watch_id_ = None
        self.gaudi_id_ = None

        self.src_host_ = host
        self.src_port_ = port

        self.video_width_ = width
        self.video_height_ = height
        self.vu_width_ = 0.75*self.video_width_
        self.vu_height_ = 0.03*self.video_height_
        self.vu_spacing_ =  0.4*self.vu_height_

        self.msg_spacing_ = 0.05*self.video_height_
        self.msg_width_ = 0.7*self.video_width_
        self.msg_height_ = 0.3*self.video_height_

        self.lvl_th_ = threshold
        self.lvl_pkttl_ = ttl
        self.lvl_pkfalloff_ = falloff

        self.serial_device_name_ = serial_device
        self.serial_device_ = None
        self.serial_write_pending_ = ''

        self.state_ = State.idle

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
            Gtk.main_quit()
        elif t == Gst.MessageType.INFO:
            self.info(message.parse_info())
        elif t == Gst.MessageType.WARNING:
            self.warn(message.parse_warning())
        elif t == Gst.MessageType.ERROR:
            self.error(message.parse_error())
            Gtk.main_quit()
        elif t == Gst.MessageType.ELEMENT:
            s = message.get_structure()
            if s.get_name() == 'level':
#                sys.stdout.write("\r")
                l = self.lvl_clamp(s['peak'][0])
                lp = self.lvl_clamp(s['decay'][0])
                r = self.lvl_clamp(s['peak'][1])
                rp = self.lvl_clamp(s['decay'][1])
#                sys.stdout.write("left: %3.2f / %3.2f, right: %3.2f / %3.2f  " % (l, lp, r, rp))
#                sys.stdout.flush()
                self.updateMeter(self.lvl_conv(l), self.lvl_conv(lp), self.lvl_conv(r), self.lvl_conv(rp))

                if self.state_ == State.running:
                    max = self.lvl_conv(lp if lp > rp else rp)
                    if max < self.lvl_th_:
                        self.stueh_und_staad()

        return True

    def on_keypress(self, win, event):
        if event.keyval == Gdk.KEY_F11:
            if not self.win_is_fullscreen_:
                self.win_.fullscreen()
            else:
                self.win_.unfullscreen()

        elif event.keyval == Gdk.KEY_space:
            self.start_die_gaudi()

        elif event.keyval == Gdk.KEY_S:
            self.stueh_und_staad()

        elif event.keyval == Gdk.KEY_R:
            self.vagess_mas()

        elif event.keyval == Gdk.KEY_X:
            Gtk.main_quit()

    def on_window_state_change(self, win, event):
        self.win_is_fullscreen_ = bool(Gdk.WindowState.FULLSCREEN & event.new_window_state)



    def start_timer(self):
        self.elapsed_ms_ = 0
        clock = self.pipeline_.get_clock()
        now = clock.get_time()
        self.gaudi_id_ = clock.new_periodic_id(now, 20*Gst.MSECOND)
        clock.id_wait_async(self.gaudi_id_, self.die_gaudi, now)

    def stop_timer(self):
        if self.gaudi_id_:
            clock = self.pipeline_.get_clock()
            clock.id_unschedule(self.gaudi_id_)
#            clock.id_unref(self.gaudi_id_)
            self.gaudi_id_ = None

    def start_die_gaudi(self):
        if not self.state_ == State.idle:
            return

        self.state_ = State.started
        self.updateMessage("Applaus!")
        self.serial_write('+')
        self.start_timer()

    def los_lei_lafen(self):
        if not self.state_ == State.started:
            return

        self.state_ = State.running
        self.updateMessage(None)

    def stueh_und_staad(self):
        if not self.state_ == State.running:
            return

        self.state_ = State.finished
        self.serial_write('s')
        self.stop_timer()
        m = int(self.elapsed_ms_/60000)
        s = int((self.elapsed_ms_%60000)/1000)
        ms = int((self.elapsed_ms_%1000)/100)
        self.updateMessage("%02i:%02i.%i" % (m, s, ms))

    def vagess_mas(self):
        self.state_ = State.idle
        self.serial_write('s')
        self.stop_timer()
        self.updateMessage(None)


    def die_gaudi(self, clock, now, start, _):
        if self.state_ == State.started or self.state_ == State.running:
            self.elapsed_ms_ = (now-start)/Gst.MSECOND
            if self.elapsed_ms_ >= 4000:
                self.los_lei_lafen()
                return True
            elif self.elapsed_ms_ > 2000:
                o = 1.0 - (self.elapsed_ms_ - 2000)/2000.0
                self.updateMessage("Applaus!", o)
                return True

        return False

    def on_serial_data_read(self, fd, cond, dev):
        data = dev.read(10)
        return True

    def on_serial_data_write(self, fd, cond, dev):
        dev.write(self.serial_write_pending_)
        self.serial_write_pending_ = '' # remove only bytes written from buffer
        return False

    def serial_write(self, data):
        l = len(self.serial_write_pending_)
        self.serial_write_pending_ += data
        if l == 0 and len(self.serial_write_pending_) > 0:
            dev = self.serial_device_
            GObject.io_add_watch(dev.fileno(), GObject.IO_OUT, self.on_serial_data_write, dev)

    def open_serial_device(self):
        import serial

        try:
            dev = serial.Serial(port=self.serial_device_name_, timeout=0.001)
            dev.flushInput()
            dev.flushOutput()
            GObject.io_add_watch(dev.fileno(), GObject.IO_IN | GObject.IO_PRI, self.on_serial_data_read, dev)

            return dev

        except (ValueError, serial.SerialException), msg:
            self.error("opening serial device:", msg)
            return None


    def create_video_pipeline(self):
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

        self.vu_overlay_ = Gst.ElementFactory.make("rsvgoverlay")
        self.updateMeter(0, 0, 0, 0)
        self.pipeline_.add(self.vu_overlay_)
        self.msg_overlay_ = Gst.ElementFactory.make("rsvgoverlay")
        self.updateMessage(None)
        self.pipeline_.add(self.msg_overlay_)

        conv_vout = Gst.ElementFactory.make("videoconvert")
        self.pipeline_.add(conv_vout)
        self.vsink_ = Gst.ElementFactory.make("xvimagesink")
        self.pipeline_.add(self.vsink_)


        q_vin.link(conv_vin)
        conv_vin.link(scale_vin)
        scale_vin.link(cf_vin)
        cf_vin.link(q_vscaled)
        q_vscaled.link(conv_vscaled)
        conv_vscaled.link(self.vu_overlay_)
        self.vu_overlay_.link(self.msg_overlay_)
        self.msg_overlay_.link(conv_vout)
        conv_vout.link(self.vsink_)

        return q_vin.get_static_pad("sink")


    def create_audio_pipeline(self):
        q_ain = Gst.ElementFactory.make("queue")
        self.pipeline_.add(q_ain)
        conv_ain = Gst.ElementFactory.make("audioconvert")
        self.pipeline_.add(conv_ain)

        level = Gst.ElementFactory.make("level", "level")
        level.set_property("message", True)
        level.set_property("peak-ttl", self.lvl_pkttl_)
        level.set_property("peak-falloff", self.lvl_pkfalloff_)
        self.pipeline_.add(level)

        asink = Gst.ElementFactory.make("fakesink")
        self.pipeline_.add(asink)

        q_ain.link(conv_ain)
        conv_ain.link(level)
        level.link(asink)

        return q_ain.get_static_pad("sink")

    def create_pipeline(self):
        self.pipeline_ = Gst.Pipeline.new()

        source = "tcpclientsrc host=%s port=%i ! queue ! gdpdepay" % (self.src_host_, self.src_port_)
        source_bin = Gst.parse_bin_from_description(source, "source")
        self.pipeline_.add(source_bin)
        decoder = Gst.ElementFactory.make("decodebin")
        self.pipeline_.add(decoder)

        vin_pad = self.create_video_pipeline()
        ain_pad = self.create_audio_pipeline()

        source_bin.link(decoder)
        sink_pads = {"video": vin_pad, "audio": ain_pad}
        decoder.connect("pad-added", self.decoder_callback, sink_pads)

        self.pipeline_.get_bus().add_signal_watch()
        self.watch_id_ = self.pipeline_.get_bus().connect('message', self.on_message)


    def create_window(self):

        self.win_ = Gtk.Window()
        self.win_.set_title("r3 audience response indicator")
        self.win_.connect("delete_event", lambda w,e: Gtk.main_quit())
        self.win_.connect("key-press-event", self.on_keypress)
        self.win_.connect("window-state-event", self.on_window_state_change)
        self.win_is_fullscreen_ = False

        canvas = Gtk.DrawingArea()
        canvas.set_size_request(self.video_width_, self.video_height_)
        self.win_.add(canvas)

        self.win_.show_all()

        return canvas.get_window().get_xid()


    def run(self):
        try:
            if(self.serial_device_name_):
                self.serial_device_ = self.open_serial_device()
                if not self.serial_device_:
                    return
                self.serial_write('s')

            self.create_pipeline()
            xid = self.create_window()

            self.vsink_.set_property("force-aspect-ratio", True)
            self.vsink_.set_window_handle(xid)

            self.pipeline_.set_state(Gst.State.PLAYING)
            self.win_.fullscreen()
            Gtk.main()

        except GObject.GError, e:
            self.error('Could not create pipeline', e.message)
        except KeyboardInterrupt:
            pass
        finally:
            if self.pipeline_ and self.watch_id_:
                self.pipeline_.get_bus().disconnect(self.watch_id_)
                self.pipeline_.get_bus().remove_signal_watch()
                self.pipeline_.set_state(Gst.State.NULL)
            if self.serial_device_:
                self.serial_device_.write('s')

    def decoder_callback(self, decoder, srcpad, sinks):
        for name, sinkpad in sinks.items():
            if sinkpad.is_linked():
                continue

            if sinkpad.can_link(srcpad):
                srcpad.link(sinkpad)


    def lvl_clamp(self, x):
        if x < -90.0:
            return -90.0
        elif x > 0.0:
            return 0.0
        return x

    def lvl_conv(self, x):
        x += 90.0
        return x/90.0


    def getMessageSVG(self, msg, opacity):
        svg = "<svg>\n"

        box_w = self.msg_width_
        box_h = self.msg_height_
        box_x = (self.video_width_ - box_w)/2
        box_y = (self.video_height_ - box_h)/2
        text_size = self.msg_height_ - 2*self.msg_spacing_
        text_x = box_x + self.msg_width_/2
        text_y = box_y + self.msg_spacing_ + text_size

        svg += "  <rect x='%i' y='%i' rx='%i' ry='%i' width='%i' height='%i' style='fill:black;opacity:%f' />\n" %(
            box_x, box_y, 0.5*self.msg_spacing_, 0.5*self.msg_spacing_, box_w, box_h, 0.5*opacity)
        svg += "  <text text-anchor='middle' dy='-0.17em' x='%i' y='%i' fill='white' " %(text_x, text_y)
        svg += "style='font-size: %i; font-family: Ubuntu; font-weight: bold; fill-opacity: %f'" %(text_size, opacity)
        svg += ">%s</text>\n" % (msg)

        svg += "</svg>\n"

        return svg

    def updateMessage(self, msg, opacity=1.0):
        if not msg:
            self.msg_overlay_.set_property("data", "")
        else:
            self.msg_overlay_.set_property("data", self.getMessageSVG(msg, opacity))
        return True

    def getVumeterSVG(self, l, lp, r, rp):
        max = lp if lp > rp else rp

        svg = "<svg>\n"
        svg += "  <defs>\n"
        svg += "    <linearGradient id='vumeter' x1='0%' y1='0%' x2='100%' y2='0%'>\n"
        if max > self.lvl_th_ and not self.state_ == State.finished:
            svg += "      <stop offset='0%' style='stop-color:rgb(0,255,0);stop-opacity:1' />\n"
            svg += "      <stop offset='100%' style='stop-color:rgb(255,0,0);stop-opacity:1' />\n"
        else:
            svg += "      <stop offset='0%' style='stop-color:rgb(42,42,42);stop-opacity:1' />\n"
            svg += "      <stop offset='100%' style='stop-color:rgb(200,200,200);stop-opacity:1' />\n"
        svg += "    </linearGradient>\n"
        svg += "  </defs>\n"

        box_w = self.vu_width_ + 2*self.vu_spacing_
        box_h = 2*self.vu_height_ + 3*self.vu_spacing_
        box_x = (self.video_width_ - box_w)/2
        box_y = 2*self.vu_spacing_

        svg += "  <rect x='%i' y='%i' rx='%i' ry='%i' width='%i' height='%i' style='fill:black;opacity:0.5' />\n" %(
            box_x, box_y, self.vu_spacing_, self.vu_spacing_, box_w, box_h)
        svg += "  <line x1='%i' y1='%i' x2='%i' y2='%i' style='stroke:white;stroke-width:%i' />\n" %(
            box_x + self.vu_width_*self.lvl_th_, box_y + 0.5*self.vu_spacing_,
            box_x + self.vu_width_*self.lvl_th_, box_y + 2.5*self.vu_spacing_ + 2*self.vu_height_, 0.5*self.vu_spacing_)

        svg += "  <rect x='%i' y='%i' width='%i' height='%i' style='fill:url(#vumeter);opacity:0.9' />\n" %(
            box_x + self.vu_spacing_, box_y + self.vu_spacing_, self.vu_width_*l, self.vu_height_)
        svg += "  <line x1='%i' y1='%i' x2='%i' y2='%i' style='stroke:rgb(255,0,0);stroke-width:%i' />\n" %(
            box_x + self.vu_width_*lp, box_y + 0.75*self.vu_spacing_,
            box_x + self.vu_width_*lp, box_y + 1.25*self.vu_spacing_ + self.vu_height_, self.vu_spacing_)

        svg += "  <rect x='%i' y='%i' width='%i' height='%i' style='fill:url(#vumeter);opacity:0.9' />\n" %(
            box_x + self.vu_spacing_, box_y + self.vu_height_ + 2*self.vu_spacing_, self.vu_width_*r, self.vu_height_)
        svg += "  <line x1='%i' y1='%i' x2='%i' y2='%i' style='stroke:rgb(255,0,0);stroke-width:%i' />\n" %(
            box_x + self.vu_width_*rp, box_y + self.vu_height_ + 1.75*self.vu_spacing_,
            box_x + self.vu_width_*rp, box_y + 2*self.vu_height_ + 2.25*self.vu_spacing_, self.vu_spacing_)

        svg += "</svg>\n"

        return svg

    def updateMeter(self, l, lp, r, rp):
        self.vu_overlay_.set_property("data", self.getVumeterSVG(l, lp, r, rp))
        return True



if __name__ == '__main__':
    usage = '''
realraum Audience Reaction Indicator.
Usage:
    ari.py [options]

Options:
    -h, --help              this help message.
    -v, --version           version info.
    --host=H                the hostname of the source stream (default: localhost).
    --port=P                the port of the source stream (default: 1234).
    --width=W               the width of the video window (default: 1280).
    --height=H              the height of the video window (default: 720).
    --serial-device=D       the serial device to the robot (default: /dev/ttyACM0).
    --no-robot              don't connect to the robot.
    --threshold=T           the audio level threshold 0.0-1.0 (default: 0.60).
    --ttl=T                 the audio level peak ttl in ns (default: 300000000).
    --falloff=F             the audio level peak fall in db/sec (default: 25).
'''

    host = "localhost"
    port = 1234
    width = 1280
    height = 720
    serial_device = '/dev/ttyACM0'
    threshold = 0.60
    ttl = 300000000
    falloff = 25
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hv", ["help", "version", "host=", "port=", "width=", "height=",
                                                        "serial-device=", "no-robot",
                                                        "threshold=", "ttl=", "falloff=" ])
        for o, a in opts:
            if o in ("-h", "--help"):
                print >> sys.stderr, usage
                sys.exit(0)
            elif o in ("-v", "--version"):
                print >> sys.stderr, "realraum ari Version 1.0"
                print >> sys.stderr, "  using Gstreamer Version %d.%d.%d.%d" % Gst.version()
                sys.exit(0)
            elif o == "--host":
                host = a
            elif o == "--port":
                try:
                    port = int(a)
                    if port < 1 or port > 65535:
                        raise getopt.GetoptError('port must be a number between 1 and 65535', o)
                except ValueError:
                    raise getopt.GetoptError('port must be a number between 1 and 65535', o)
            elif o == "--width":
                try:
                    width = int(a)
                    if width < 0:
                        raise getopt.GetoptError('width must be a positive number', o)
                except ValueError:
                    raise getopt.GetoptError('width must be a positive number', o)
            elif o == "--height":
                try:
                    height = int(a)
                    if height < 0:
                        raise getopt.GetoptError('height must be a positive number', o)
                except ValueError:
                    raise getopt.GetoptError('height must be a positive number', o)
            elif o == "--serial-device":
                serial_device = a
            elif o == "--no-robot":
                serial_device = None
            elif o == "--threshold":
                try:
                    threshold = float(a)
                    if threshold < 0.0 or threshold > 1.0:
                        raise getopt.GetoptError('threshold must be a number between 0.0 and 1.0', o)
                except ValueError:
                    raise getopt.GetoptError('threshold must be a number between 0.0 and 1.0', o)
            elif o == "--ttl":
                try:
                    ttl = int(a)
                    if ttl < 0:
                        raise getopt.GetoptError('ttl must be a positive number', o)
                except ValueError:
                    raise getopt.GetoptError('ttl must be a positive number', o)
            elif o == "--falloff":
                try:
                    falloff = int(a)
                    if falloff < 0:
                        raise getopt.GetoptError('falloff must be a positive number', o)
                except ValueError:
                    raise getopt.GetoptError('falloff must be a positive number', o)

        if len(args) > 1:
            raise getopt.GetoptError('Too many arguments')

    except getopt.GetoptError, msg:
        print >> sys.stderr, "ERROR: %s" % msg
        print >> sys.stderr, usage
        sys.exit(2)


    a = R3Ari(host=host, port=port, width=width, height=height, serial_device=serial_device,
              threshold=threshold, ttl=ttl, falloff=falloff)
    a.run()
