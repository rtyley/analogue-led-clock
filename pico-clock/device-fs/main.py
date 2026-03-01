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
d.alarm1.set(EVERY_SECOND)
print('******HELLO I AM THE MAIN CODE***')

ac = AnalogueClock(HT1632C(base_pin_index=2, state_machine_id=0, freq = 10*1000*1000))
ac.initialise()

while True:
    d.alarm1.clear()  # Clear pending alarm
    while not d.alarm1():  # Wait for alarm
        pass
    YY, MM, DD, hh, mm, ss, wday, _ = d.get_time()
    ac.light_time(hh, mm)
    time.sleep(0.3)  # Pin stays low for 300ms
