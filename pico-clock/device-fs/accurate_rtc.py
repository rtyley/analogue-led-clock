from machine import I2C, Pin
from DS3231.ds3231_gen import *

i2c = I2C(0, scl=Pin(29), sda=Pin(28))

print('Scanning I2C bus...')
devices = i2c.scan()

print(f'{len(devices)} device(s) found.')
for device in devices:
    print(f'Decimal Address: {device} | Hex Address: {hex(device)}')

ACCURATE_RTC = DS3231(i2c)
