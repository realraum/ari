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
RECORD_D=/srv/piday15
FILENAME=`date +%Y-%m-%d_%H-%M-%S`

$GST_LAUNCH tcpclientsrc host=localhost port=$PORT ! queue ! gdpdepay ! matroskademux !   \
               matroskamux ! filesink location=$RECORD_D/$FILENAME.mkv
