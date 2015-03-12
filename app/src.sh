#!/bin/sh
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

GST_LAUNCH=gst-launch-1.0
PORT=1234

$GST_LAUNCH decklinksrc name=src device-number=0 mode=10 connection=0 audio-input=0  \
               src.videosrc ! queue ! jpegenc ! mux.                                 \
               src.audiosrc ! queue ! mux.                                           \
               matroskamux name=mux streamable=yes ! tee name=vt                     \
               vt. ! queue ! gdppay ! tcpserversink port=$PORT


