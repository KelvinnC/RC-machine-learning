#!/usr/bin/env python3
import time
import board, busio
from adafruit_pca9685 import PCA9685
from evdev import InputDevice, list_devices, ecodes

# Hardware mapping
STEER_CH     = 1
THROTTLE_CH  = 0

# PWM endpoints
STEER_MIN    = 150
STEER_MAX    = 600
STEER_CENTER = (STEER_MIN + STEER_MAX) // 2
dead_zone = 5

THROTTLE_REV = 205   # 1.0 ms full reverse
THROTTLE_STOP= 307   # 1.5 ms neutral/arm
THROTTLE_MAX = 410   # 2.0 ms full forward

def map_range(x, a, b, c, d):
    return int((x - a) / (b - a) * (d - c) + c)

# Init I2C + PCA9685
i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 50

def set_pwm(ch, pulse):
    pca.channels[ch].duty_cycle = pulse

# Center steering immediately
print("? Centering steering servo")
set_pwm(STEER_CH, STEER_CENTER)
time.sleep(1)

# Arm ESC on throttle channel
print("Holding neutral throttle for ESC arming")
set_pwm(THROTTLE_CH, THROTTLE_STOP)
time.sleep(2)
print("NOW connect your battery ? you should hear the ESC arm beeps")
time.sleep(3)
print("ESC should now be armed (solid green LED)")
