import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

pins = {"green":16, "yellow":20, "red":21}

GPIO.cleanup()
GPIO.setmode(GPIO.BCM)

for p in pins.values():
    GPIO.setup(p, GPIO.OUT)
    GPIO.output(p, GPIO.LOW)

for name, p in pins.items():
    print("ON:", name)
    GPIO.output(p, GPIO.HIGH)
    time.sleep(1.5)
    GPIO.output(p, GPIO.LOW)

GPIO.cleanup()
