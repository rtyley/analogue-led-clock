from machine import I2C, Pin
from DS3231.ds3231_gen import *

i2c = I2C(0, scl=Pin(29), sda=Pin(28))

ACCURATE_RTC = DS3231(i2c)
