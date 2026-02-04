import time
import random

# ---------- MOISTURE (ADS1115 of mock) ----------
USE_ADC = True

try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn

    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    ads.gain = 1
    moisture_channel = AnalogIn(ads, ADS.P0)

    WET = 12000
    DRY = 26000

    def read_moisture():
        raw = moisture_channel.value
        percent = (DRY - raw) * 100 / (DRY - WET)
        percent = max(0, min(100, percent))
        return int(percent), int(raw)

except Exception as e:
    USE_ADC = False
    print("ADS1115 niet beschikbaar -> mock moisture:", e)

    def read_moisture():
        return random.randint(0, 100), random.randint(10000, 30000)

# ---------- LICHT (nu mock) ----------
def read_light():
    return random.randint(100, 1000)

# ---------- ULTRASONIC (HC-SR04) ----------
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

TRIG = 23
ECHO = 24

GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def afstand_cm():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    pulse_start = time.time()
    pulse_end = time.time()

    t0 = time.time()
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
        if time.time() - t0 > 0.05:
            return 999

    t1 = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()
        if time.time() - t1 > 0.05:
            return 999

    pulse_duration = pulse_end - pulse_start
    return round(pulse_duration * 17150, 2)

def cleanup_gpio():
    GPIO.cleanup()
