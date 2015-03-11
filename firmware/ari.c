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

#include <avr/io.h>
#include <avr/wdt.h>
#include <avr/interrupt.h>
#include <avr/power.h>
#include <stdio.h>

#include "util.h"
#include "led.h"
#include "usbio.h"

#include "pump.h"


void handle_cmd(uint8_t cmd)
{
  switch(cmd) {
  case 'l': pump_start(left); break;
  case 'r': pump_start(right); break;
  case 's': pump_stop(); break;
  case '!': reset2bootloader(); break;
  default: printf("error\r\n"); return;
  }
  printf("ok\r\n");
}

int main(void)
{
  MCUSR &= ~(1 << WDRF);
  wdt_disable();

  cpu_init();
  jtag_disable();
  led_init();
  pump_init();
  usbio_init();
  pump_init();
  sei();

  for(;;) {
    int16_t BytesReceived = usbio_bytes_received();
    while(BytesReceived > 0) {
      int ReceivedByte = fgetc(stdin);
      if(ReceivedByte != EOF) {
        handle_cmd(ReceivedByte);
      }
      BytesReceived--;
    }

    usbio_task();
    pump_task();
  }
}
