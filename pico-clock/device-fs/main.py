from machine import Pin, I2C
import sys
from DS3231.ds3231_gen import *
from analogue_clock import AnalogueClock
from holtek.ht1632c.driver import HT1632C
from tzif_parser import TimeZoneInfo

i2c = I2C(0, scl=Pin(13), sda=Pin(12))

d = DS3231(i2c)
# d.set_time()

print(d.get_time())
d.alarm1.set(EVERY_SECOND)
print('******HELLO I AM THE MAIN CODE***')

tz_info = TimeZoneInfo.read("Eurppe/Amsterdam")

print(tz_info)
print(tz_info.header)
print(tz_info.body)
print(tz_info.footer)

ac = AnalogueClock(HT1632C(base_pin_index=2, state_machine_id=0, freq = 10*1000*1000))
ac.initialise()

try:
    while True:
        d.alarm1.clear()  # Clear pending alarm
        while not d.alarm1():  # Wait for alarm
            pass
        YY, MM, DD, hh, mm, ss, wday, _ = d.get_time()
        ac.light_time(hh, mm)
        time.sleep(0.3)  # Pin stays low for 300ms
except Exception as e:
    print("Fatal error in main:")
    sys.print_exception(e)

# Following a normal Exception or main() exiting, reset the board.
# Following a non-Exception error such as KeyboardInterrupt (Ctrl-C),
# this code will drop to a REPL. Place machine.reset() in a finally
# block to always reset, instead.
machine.reset()


