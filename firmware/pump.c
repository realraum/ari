/*
 *  tuer-rfid
 *
 *
 *  Copyright (C) 2013-2014 Christian Pointner <equinox@spreadspace.org>
 *                          Othmar Gsenger <otti@wirdorange.org>
 *
 *  This file is part of tuer-rfid.
 *
 *  tuer-rfid is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  any later version.
 *
 *  tuer-rfid is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with tuer-rfid. If not, see <http://www.gnu.org/licenses/>.
 */

#include <avr/sfr_defs.h>
#include <avr/interrupt.h>

#include "led.h"
#include "pump.h"

#define PUMP_PORT PORTF
#define PUMP_DDR DDRF
#define PUMP_OUTPUT_A1_BIT 4
#define PUMP_OUTPUT_A2_BIT 5
#define PUMP_ENABLE_A_BIT 0
#define PUMP_OUTPUT_B1_BIT 6
#define PUMP_OUTPUT_B2_BIT 7
#define PUMP_ENABLE_B_BIT 1

#define BLINK_DURATION 5 // *10 ms, duration of blink pulse
#define BLINK_DELAY 20   // *10 ms, 1/blink-frequency
uint8_t blink_cnt = 0;
uint8_t blink_flag;

// while running this gets called every ~10ms
ISR(TIMER0_COMPA_vect)
{
  blink_cnt++;
  if(blink_cnt == BLINK_DURATION)
    blink_flag = 0;
  else if(blink_cnt >= BLINK_DELAY) {
    blink_flag = 1;
    blink_cnt = 0;
  }
}

static void blink_start(void)
{
  led_off();
  blink_cnt = 0;
  blink_flag = 1;

  TCCR0A = 1<<WGM01;           // OC0A and OC0B as normal output, WGM = 2 (CTC)
  TCCR0B = 1<<CS02 | 1<<CS00;  // Prescaler 1:1024
  OCR0A = 155;                 // (1+155)*1024 = 159744 -> ~10 ms @ 16 MHz
  TCNT0 = 0;
  TIMSK0 = 1<<OCIE0A;
}

static void blink_stop(void)
{
  TCCR0B = 0; // no clock source
  TIMSK0 = 0; // disable timer interrupt

  blink_flag = 1;
  led_on();
}

void pump_init(void)
{
  PUMP_PORT &= ~(1<<PUMP_OUTPUT_A1_BIT | 1<<PUMP_OUTPUT_A2_BIT | 1<<PUMP_ENABLE_A_BIT |
                 1<<PUMP_OUTPUT_B1_BIT | 1<<PUMP_OUTPUT_B2_BIT | 1<<PUMP_ENABLE_B_BIT);

  PUMP_DDR |= (1<<PUMP_OUTPUT_A1_BIT | 1<<PUMP_OUTPUT_A2_BIT | 1<<PUMP_ENABLE_A_BIT |
               1<<PUMP_OUTPUT_B1_BIT | 1<<PUMP_OUTPUT_B2_BIT | 1<<PUMP_ENABLE_B_BIT);

  pump_stop();
}

void pump_start(pump_dir_t dir)
{
  switch(dir)
  {
  case left: {
    PUMP_PORT &= ~(1<<PUMP_OUTPUT_B2_BIT);
    PUMP_PORT |= (1<<PUMP_OUTPUT_B1_BIT |  1<<PUMP_ENABLE_B_BIT);
    break;
  }
  case right: {
    PUMP_PORT &= ~(1<<PUMP_OUTPUT_B1_BIT);
    PUMP_PORT |= (1<<PUMP_OUTPUT_B2_BIT |  1<<PUMP_ENABLE_B_BIT);
    break;
  }
  }
  blink_start();
}

void pump_stop(void)
{
  PUMP_PORT &= ~(1<<PUMP_OUTPUT_A1_BIT | 1<<PUMP_OUTPUT_A2_BIT | 1<<PUMP_ENABLE_A_BIT |
                 1<<PUMP_OUTPUT_B1_BIT | 1<<PUMP_OUTPUT_B2_BIT | 1<<PUMP_ENABLE_B_BIT);

  blink_stop();
}

void pump_task(void)
{
  if(blink_flag)
    led_on();
  else
    led_off();
}
