import rp2
from time import sleep, ticks_us, ticks_diff
from holtek.ht1632c.driver import HT1632C
from analogue_clock import AnalogueClock

print('******HELLO I AM MICROPYTHON CODE***')

def exec_with(freq: int):

    ac = AnalogueClock(HT1632C(base_pin_index=2, state_machine_id=0, freq = freq))
    ac.initialise()
    # ac._write_mode_buffer.correctness_test()
    while True:
        for hour in range(12):
            for min in range(60):
                ac.light_time(hour, min)

