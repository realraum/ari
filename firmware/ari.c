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


#define PWM_VAL OCR1BL

void pwm_init(void)
{
  DDRB |= (1<<PB6);
  TCCR1B = 0;
  TCNT1 = 0;
  OCR1B = 0;
  TCCR1A = (1<<COM1B1) | (1<<WGM10);
  TCCR1B = (1<<WGM12);
}

inline void pwm_on(void)
{
  TCCR1B = (TCCR1B & 0xF8) | (1<<CS10);
}

inline void pwm_off(void)
{
  TCCR1B = (TCCR1B & 0xF8);
  TCNT1 = 0;
}

inline void pwm_set(uint8_t val)
{
  PWM_VAL = val;
}

inline void pwm_inc(void)
{
  if(PWM_VAL < 255)
    PWM_VAL++;
}

inline void pwm_dec(void)
{
  if(PWM_VAL > 0)
    PWM_VAL--;
}


void handle_cmd(uint8_t cmd)
{
  switch(cmd) {
  case '0': led_off(); break;
  case '1': led_on(); break;
  case 't': led_toggle(); break;
  case '+': pwm_inc(); printf("pwm = %d\r\n", PWM_VAL);  break;
  case '-': pwm_dec(); printf("pwm = %d\r\n", PWM_VAL); break;
  case 'r': reset2bootloader(); break;
  default: printf("error\r\n"); return;
  }
  printf("ok\r\n");
}

int main(void)
{
  MCUSR &= ~(1 << WDRF);
  wdt_disable();

  cpu_init();
  led_init();
  usbio_init();
  pwm_init();
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
  }
}
