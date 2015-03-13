/*
 *  ari
 *
 *  the realraum audience response indicator
 *
 *  Copyright (C) 2015 Christian Pointner <equinox@spreadspace.org>
 *
 *  This file is part of ari.
 *
 *  ari is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  any later version.
 *
 *  ari is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with ari. If not, see <http://www.gnu.org/licenses/>.
 */

#ifndef R3ARI_pump_h_INCLUDED
#define R3ARI_pump_h_INCLUDED

typedef enum { in, out } pump_dir_t;

void pump_init(void);
void pump_start(pump_dir_t dir);
void pump_stop(void);
void pump_task(void);

#endif
