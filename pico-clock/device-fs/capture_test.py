import rp2
from time import sleep, ticks_us, ticks_diff
from holtek.ht1632c.driver import HT1632C
from analogue_clock import AnalogueClock

print('******HELLO I AM MICROPYTHON CODE***')

def exec_with(freq: int):

    ac = AnalogueClock(HT1632C(base_pin_index=2, state_machine_id=0, freq = freq))
    ac.initialise()

    while True:
        for phase in range(10):
            ac.light_pixel_identification_step(phase)
