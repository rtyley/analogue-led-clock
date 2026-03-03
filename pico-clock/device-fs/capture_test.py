import rp2
from time import sleep, ticks_us, ticks_diff
from holtek.ht1632c.driver import HT1632C
from analogue_clock import AnalogueClock
from DS3231.ds3231_gen import *
from machine import Pin, I2C

i2c = I2C(0, scl=Pin(13), sda=Pin(12))

d = DS3231(i2c)
# d.set_time()

print(d.get_time())
print('******HELLO I AM MICROPYTHON CODE***')



def exec_with(freq: int):

    ac = AnalogueClock(HT1632C(base_pin_index=2, state_machine_id=0, freq = freq))
    ac.initialise()
    # ac._write_mode_buffer.correctness_test()
    while True:
        for hour in range(12):
            for min in range(60):
                ac.light_time(hour, min)

