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

    center_led: int = 233

    hand_leds: list[list[int]] = [
        [244,242,241,240,239,238,237,236],
        [245,258,257,256,255,254,253,252],
        [259,274,273,272,271,270,269,268],
        [260,290,289,288,287,286,285,284],
        [261,306,305,304,303,302,301,300],
        [275,322,321,320,319,318,317,316],
        [276,338,337,336,335,334,333,332],
        [277,354,353,352,351,350,349,348],
        [291,370,369,368,367,366,365,364],
        [292,386,385,384,383,382,381,380],
        [293,402,401,400,399,398,397,396],
        [307,418,417,416,415,414,413,412],
        [308,434,433,432,431,430,429,428],
        [309,450,449,448,447,446,445,444],
        [323,466,465,464,463,462,461,460],
        [324,482,481,480,479,478,477,476],
        [325,6,5,4,3,2,1,0],
        [339,22,21,20,19,18,17,16],
        [340,38,37,36,35,34,33,32],
        [341,54,53,52,51,50,49,48],
        [355,70,69,68,67,66,65,64],
        [356,86,85,84,83,82,81,80],
        [357,102,101,100,99,98,97,96],
        [371,118,117,116,115,114,113,112],
        [372,134,133,132,131,130,129,128],
        [373,150,149,148,147,146,145,144],
        [387,166,165,164,163,162,161,160],
        [388,182,181,180,179,178,177,176],
        [389,198,197,196,195,194,193,192],
        [403,214,213,212,211,210,209,208],
        [404,71,223,222,221,220,219,218],
        [405,87,207,206,205,204,203,202],
        [419,103,191,190,189,188,187,186],
        [420,119,175,174,173,172,171,170],
        [421,135,159,158,157,156,155,154],
        [435,151,143,142,141,140,139,138],
        [436,167,127,126,125,124,123,122],
        [437,183,111,110,109,108,107,106],
        [451,199,95,94,93,92,91,90],
        [452,215,79,78,77,76,75,74],
        [453,72,63,62,61,60,59,58],
        [467,88,47,46,45,44,43,42],
        [468,104,31,30,29,28,27,26],
        [469,120,15,14,13,12,11,10],
        [483,136,491,490,489,488,487,486],
        [484,152,475,474,473,472,471,470],
        [485,168,459,458,457,456,455,454],
        [7,184,443,442,441,440,439,438],
        [8,200,427,426,425,424,423,422],
        [9,216,411,410,409,408,407,406],
        [23,73,395,394,393,392,391,390],
        [24,89,379,378,377,376,375,374],
        [25,105,363,362,361,360,359,358],
        [39,121,347,346,345,344,343,342],
        [40,137,331,330,329,328,327,326],
        [41,153,315,314,313,312,311,310],
        [55,169,299,298,297,296,295,294],
        [56,185,283,282,281,280,279,278],
        [57,201,267,266,265,264,263,262],
        [243,217,251,250,249,248,247,246]
    ]

    hour_marker_leds = [hand[-1] for hand in hand_leds[::5]]

    base_display_leds: list[int] = hour_marker_leds + [center_led]

    hour_hand_length = 5

    def leds_for(hour: int, minute: int) -> list[int]:
        return sorted(list(set(AnalogueClock.base_display_leds + AnalogueClock.hand_leds[round((((hour % 12) * 60) + minute) / 12)][:AnalogueClock.hour_hand_length] + AnalogueClock.hand_leds[minute])))


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
        self._write_mode_buffer = MultiChipWriteBuffer([236, 256])

    def initialise(self):
        self.driver.transmit([AnalogueClock.leaderC1, AnalogueClock.followerC1])
        self.driver.transmit([AnalogueClock.leaderAndFollowerC2, AnalogueClock.leaderAndFollowerC2])
        self.driver.transmit([AnalogueClock.leaderAndFollowerC3, AnalogueClock.leaderAndFollowerC3])
        self.driver.transmit([AnalogueClock.leaderAndFollowerC4, AnalogueClock.leaderAndFollowerC4])
        self.driver.transmit([AnalogueClock.leaderAndFollowerC5, AnalogueClock.leaderAndFollowerC5])

    def light_center(self, value):
        self._write_mode_buffer.write_pixel(AnalogueClock.center_led, value)
        self.transmit_write_mode_buffer()

    def light_hand(self, hand: int):
        for led in AnalogueClock.hand_leds[hand]:
                self._write_mode_buffer.write_pixel(led, True)
        self.transmit_write_mode_buffer()
        sleep(1)
        for led in AnalogueClock.hand_leds[hand]:
            self._write_mode_buffer.write_pixel(led, False)
        self.transmit_write_mode_buffer()

    @timed_function
    def light_time(self, hour: int, minute: int):
        leds = AnalogueClock.leds_for(hour, minute)
        self._write_mode_buffer.set_only(leds)
        self.transmit_write_mode_buffer()


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
