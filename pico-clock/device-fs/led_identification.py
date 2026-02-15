import rp2
from rp2 import PIO
from machine import Pin
from time import sleep, ticks_us, ticks_diff
import struct
from holtek.ht1632c.operations import *
from holtek.ht1632c.driver import HT1632C


print('******HELLO I AM MICROPYTHON CODE***')

def timed_function(f, *args, **kwargs):
    myname = str(f).split(' ')[1]
    def new_func(*args, **kwargs):
        t = ticks_us()
        result = f(*args, **kwargs)
        delta = ticks_diff(ticks_us(), t)
        print('Function {} Time = {:6.3f}ms'.format(myname, delta/1000))
        return result
    return new_func

d = HT1632C(base_pin_index=2, state_machine_id=0, freq = freq)

d.transmit([leaderC1, followerC1])
d.transmit([leaderAndFollowerC2, leaderAndFollowerC2])
d.transmit([leaderAndFollowerC3, leaderAndFollowerC3])
d.transmit([leaderAndFollowerC4, leaderAndFollowerC4])
d.transmit([leaderAndFollowerC5, leaderAndFollowerC5])

while True:
    num_blocks = 64

    for i in range(0, num_blocks * 4):
        full_blocks = i // 4
        partial_block = pow(2, i % 4) - 1

        blocks = ([0b1111] * full_blocks) + [partial_block] + ([0b0000] * (num_blocks - full_blocks - 1))
        d.transmit([WriteMode(0, blocks), WriteMode(0, blocks)])
