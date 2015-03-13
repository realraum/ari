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

#include <avr/sfr_defs.h>
#include <avr/interrupt.h>

#include "led.h"
#include "rgb.h"

#define RGB_PORT PORTB
#define RGB_DDR DDRB
#define RGB_RED_BIT 5
#define RGB_GREEN_BIT 6
#define RGB_BLUE_BIT 7

#define RGB_PWM_CS0 CS10
#define RGB_PWM_TCCRA TCCR1A
#define RGB_PWM_TCCRB TCCR1B
#define RGB_PWM_TCCRC TCCR1C
#define RGB_PWM_TCNT TCNT1
#define RGB_PWM_RED OCR1A
#define RGB_PWM_GREEN OCR1B
#define RGB_PWM_BLUE OCR1C

#define RGB_PWM_MAX 0x03FF

void pwm_init(void)
{
  RGB_PWM_TCCRA = 0xFF;
  RGB_PWM_TCCRB = 0x08;
  RGB_PWM_TCCRC = 0x00;
  RGB_PWM_TCNT = 0;

  RGB_PWM_TCCRB |= (1<<RGB_PWM_CS0);
}

void pwm_stop(void)
{
  RGB_PWM_TCCRA = 0x03;
  RGB_PWM_TCCRB = 0x08;
}

void rgb_init(void)
{
  RGB_PORT |= (1<<RGB_RED_BIT | 1<<RGB_GREEN_BIT | 1<<RGB_BLUE_BIT);
  RGB_DDR |= (1<<RGB_RED_BIT | 1<<RGB_GREEN_BIT | 1<<RGB_BLUE_BIT);

  rgb_stop();
}

void rgb_start()
{
  RGB_PWM_RED = 0;
  RGB_PWM_GREEN = RGB_PWM_MAX/100;
  RGB_PWM_BLUE = RGB_PWM_MAX;
  pwm_init();
}

void rgb_stop(void)
{
  pwm_stop();
  RGB_PORT |= (1<<RGB_RED_BIT | 1<<RGB_GREEN_BIT | 1<<RGB_BLUE_BIT);
}

void rgb_task(void)
{
  static uint32_t cnt = 0;
  if(cnt >= 100) {
    RGB_PWM_RED = (RGB_PWM_RED > 0) ? RGB_PWM_RED*2 : 1;
    RGB_PWM_GREEN = (RGB_PWM_GREEN > 0) ? RGB_PWM_GREEN*2 : 1;
    RGB_PWM_BLUE = (RGB_PWM_BLUE > 0) ? RGB_PWM_BLUE*2 : 1;

    RGB_PWM_RED = (RGB_PWM_RED > RGB_PWM_MAX) ? RGB_PWM_RED : 0;
    RGB_PWM_GREEN = (RGB_PWM_GREEN > RGB_PWM_MAX) ? RGB_PWM_GREEN : 0;
    RGB_PWM_BLUE = (RGB_PWM_BLUE > RGB_PWM_MAX) ? RGB_PWM_BLUE : 0;
    cnt = 0;
  } else {
    cnt++;
  }
}
