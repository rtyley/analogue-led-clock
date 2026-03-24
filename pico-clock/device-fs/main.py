from datetime import datetime

import sys
from DS3231.ds3231_gen import *
from analogue_clock import AnalogueClock
from holtek.ht1632c.driver import HT1632C
from tzif_parser import TimeZoneInfo

from accurate_rtc import ACCURATE_RTC

# ACCURATE_RTC.set_time()

print(ACCURATE_RTC.get_time())
ACCURATE_RTC.alarm1.set(EVERY_SECOND)
print('******HELLO I AM THE MAIN CODE***')

timezone_name = open('/timezone.txt').readline().strip()
print(f'timezone_name={timezone_name}')

tz_info = TimeZoneInfo.read(timezone_name)

print(tz_info)
current_transition_index = tz_info.body.find_transition_index(datetime.now())
print(current_transition_index)

ac = AnalogueClock(HT1632C(base_pin_index=2, state_machine_id=0, freq = 10*1000*1000))
ac.initialise()

try:
    while True:
        ACCURATE_RTC.alarm1.clear()  # Clear pending alarm
        while not ACCURATE_RTC.alarm1():  # Wait for alarm
            pass
        YY, MM, DD, hh, mm, ss, wday, _ = ACCURATE_RTC.get_time()

        resolved = tz_info.resolve(datetime(YY, MM, DD, hh, mm, ss))
        print(f'local_time={resolved.local_time}')
        print(f'resolution_time={resolved.resolution_time}')
        print(f'next_transition={resolved.next_transition}')
        print(f'utc_offset_secs={resolved.utc_offset_secs}')

        local_time = resolved.local_time
        ac.light_time(local_time.hour, local_time.minute)
        time.sleep(0.3)  # Pin stays low for 300ms

except Exception as e:
    print("Fatal error in main:")
    sys.print_exception(e)

# Following a normal Exception or main() exiting, reset the board.
# Following a non-Exception error such as KeyboardInterrupt (Ctrl-C),
# this code will drop to a REPL. Place machine.reset() in a finally
# block to always reset, instead.
machine.reset()


