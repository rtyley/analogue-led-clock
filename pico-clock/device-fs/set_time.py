from time import sleep_us, ticks_ms, ticks_diff, ticks_add

from select import select
from sys import stdin

from accurate_rtc import ACCURATE_RTC

# ACCURATE_RTC.set_aging_offset(-4)
print(ACCURATE_RTC.temperature())

def readDeadlineAndTimeToDeadlineFromUSB():
    ch, buffer = '',''
    ticks_ms_for_read_instant = ticks_ms()
    while stdin in select([stdin], [], [], 0)[0]:
        ch = stdin.read(1)
        buffer = buffer+ch
    if buffer:
        print("Received USB data!")
        for i in range(len(buffer)):
            if buffer[i] == 'T':
                break
        buffer = buffer[i:]
        last_in_buff = buffer[-1]
        if buffer[:1] == 'T' and (last_in_buff == ':' or last_in_buff == ';'):
            buffData = buffer[1:-1]
            buffFields = [int(x) for x in buffData.split(',')]
            deadLineFields = buffFields[:-1]
            deadLineFields.append(0)
            timeToDeadLine = buffFields[-1]
            print(f"timeToDeadLine: {timeToDeadLine}")
            return deadLineFields, ticks_add(ticks_ms_for_read_instant, timeToDeadLine), last_in_buff == ':'


lastSecondPrinted = ACCURATE_RTC.get_time()[5]
ticks_at_clock_second_transition = 0
last_ticks_read = ticks_ms()
while True:
    ds3231Time = ACCURATE_RTC.get_time()
    clock_read_at_ticks = ticks_ms()
    time_between_reads = ticks_diff(last_ticks_read, clock_read_at_ticks)
    last_ticks_read = clock_read_at_ticks
    loop_too_slow = time_between_reads > 1
    if loop_too_slow:
        print(f'time_between_reads TOO LONG: {time_between_reads}')
    else:
        secondsFromDS3231Time = ds3231Time[5]
        if secondsFromDS3231Time != lastSecondPrinted:
            ticks_at_clock_second_transition = clock_read_at_ticks % 1000
            if secondsFromDS3231Time % 10 == 0:
                print(f'DS3231 RTC : {ds3231Time}')
                print(ACCURATE_RTC)
            print(f'DS3231 seconds : {secondsFromDS3231Time} - ticks_at_clock_second_transition : {ticks_at_clock_second_transition}')
            lastSecondPrinted = secondsFromDS3231Time

    receivedTimeDataFromUsb = readDeadlineAndTimeToDeadlineFromUSB()
    if receivedTimeDataFromUsb and not loop_too_slow:
        deadLineFields, deadline_ticks, set_time = receivedTimeDataFromUsb
        (year, month, day, hour, minute, second, wday, yday) = deadLineFields

        ticks_until_deadline = ticks_diff(deadline_ticks, ticks_ms())
        if ticks_until_deadline < 0:
            print(f"Missed the deadline by {ticks_until_deadline}ms")
        else:
            if set_time:
                while ticks_diff(deadline_ticks, ticks_ms()) > 0:
                    sleep_us(100)  # *ticks_diff(deadline, time.ticks_ms())
                ACCURATE_RTC.set_time(deadLineFields)
                print("*TIME SET*")
            deadline_transition_ticks = deadline_ticks % 1000
            offset = ticks_at_clock_second_transition - deadline_transition_ticks
            print(f"Deadline suggests ticks_at_clock_second_transition should be: {deadline_transition_ticks}")
            print(f"offset: {offset}")
            print(f"Saved time from USB\t: {deadLineFields}")
            print(f"DS3231 now says\t: {ACCURATE_RTC.get_time()}")
