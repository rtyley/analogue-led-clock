from holtek.ht1632c.driver import HT1632C
from analogue_clock import AnalogueClock

ac = AnalogueClock(HT1632C(base_pin_index=2, state_machine_id=0, freq = 2000000))
ac.initialise()
