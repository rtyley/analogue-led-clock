import rp2
import struct
from machine import Pin
from rp2 import PIO
from time import sleep, ticks_us, ticks_diff

from holtek.ht1632c.driver import HT1632C
from holtek.ht1632c.multi_chip_write_buffer import *
from holtek.ht1632c.operations import *

def timed_function(f, *args, **kwargs):
    myname = str(f).split(' ')[1]
    def new_func(*args, **kwargs):
        t = ticks_us()
        result = f(*args, **kwargs)
        delta = ticks_diff(ticks_us(), t)
        print('Function {} Time = {:6.3f}ms'.format(myname, delta/1000))
        return result
    return new_func

class AnalogueClock:

    leaderC1 = CommandMode([
        0b00000000, # SYS DIS        100 0000-0000-X        Turn off both system oscillator and LED duty cycle generator
        0b00101100, # COM Option     100 0010-abXX-X ab=11: P-MOS open drain output and 16 COM option
        0b00011000, # RC Master Mode 100 0001-10XX-X        Set master mode and clock source from on-chip RC oscillator, the system clock output to OSC pin and synchronous signal output to SYN pin
        0b00000001, # SYS EN         100 0000-0001-X        Turn on system oscillator
        0b10101111, # PWM Duty       100 101X-1111-X        PWM 16/16 duty
        0b00001000, # BLINK Off      100 0000-1000-X        Turn off blinking function
        0b00000010, # LED Off        100 0000-0010-X        Turn off LED duty cycle generator
    ])

    followerC1 = CommandMode([
        0b00000000, # SYS DIS        100 0000-0000-X        Turn off both system oscillator and LED duty cycle generator
        0b00101100, # COM Option     100 0010-abXX-X ab=11: P-MOS open drain output and 16 COM option
        0b00010000, # SLAVE Mode     100 0001-0XXX-X        Set slave mode and clock source from external clock, the system clock input from OSC pin and synchronous signal input from SYN pin
        0b00000001, # SYS EN         100 0000-0001-X        Turn on system oscillator
        0b10101111, # PWM Duty       100 101X-1111-X        PWM 16/16 duty
        0b00001000, # BLINK Off      100 0000-1000-X        Turn off blinking function
        0b00000010, # LED Off        100 0000-0010-X        Turn off LED duty cycle generator
    ])

    leaderAndFollowerC2 = CommandMode([
        0b00000010 # LED Off          100 0000-0010-X        Turn off LED duty cycle generator
    ])

    leaderAndFollowerC3 = CommandMode([
        0b00000000 # SYS DIS          100 0000-0000-X        Turn off both system oscillator and LED duty cycle generator
    ])

    leaderAndFollowerC4 = CommandMode([
        0b00000001 # SYS EN           100 0000-0001-X        Turn on system oscillator
    ])

    leaderAndFollowerC5 = CommandMode([
        0b00000011  # LED On          100 0000-0011-X        Turn on LED duty cycle generator
    ])



    def __init__(
            self, driver: HT1632C
    ) -> None:
        self.driver = driver
        self._write_mode_buffer = MultiChipWriteBuffer([384, 384])

    def initialise(self):
        self.driver.transmit([AnalogueClock.leaderC1, AnalogueClock.followerC1])
        self.driver.transmit([AnalogueClock.leaderAndFollowerC2, AnalogueClock.leaderAndFollowerC2])
        self.driver.transmit([AnalogueClock.leaderAndFollowerC3, AnalogueClock.leaderAndFollowerC3])
        self.driver.transmit([AnalogueClock.leaderAndFollowerC4, AnalogueClock.leaderAndFollowerC4])
        self.driver.transmit([AnalogueClock.leaderAndFollowerC5, AnalogueClock.leaderAndFollowerC5])

    def light_pixel_identification_seq(self):
        self.set_all(True)
        sleep(4)
        for phase in range(10):
            self.light_pixel_identification_step(phase)
            sleep(1)

    @timed_function
    def light_pixel_identification_step(self, phase: int):
        for pixel_index in range(self._write_mode_buffer.total_pixels):
            self._write_mode_buffer.write_pixel(pixel_index, (pixel_index & (1 << phase)) != 0)
        self.transmit_write_mode_buffer()
        print(f"id: {phase}")

    @timed_function
    def set_all(self, value: bool):
        for pixel_index in range(self._write_mode_buffer.total_pixels):
            self._write_mode_buffer.write_pixel(pixel_index, value)
        self.transmit_write_mode_buffer()

    @timed_function
    def transmit_write_mode_buffer(self):
        self.driver.transmit_bytearray(self._write_mode_buffer.raw_bytearray)
