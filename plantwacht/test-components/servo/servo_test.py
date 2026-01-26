import time
import pigpio

SERVO_GPIO = 18
pi = pigpio.pi()
if not pi.connected:
    raise SystemExit("pigpiod draait niet. Start: sudo systemctl start pigpiod")

def angle(a):
    a = max(0, min(180, a))
    pulse = 600 + (a/180)*1800   # 600..2400us
    pi.set_servo_pulsewidth(SERVO_GPIO, pulse)

try:
    for a in [0, 90, 180, 90, 0]:
        print("angle", a)
        angle(a)
        time.sleep(1)
finally:
    pi.set_servo_pulsewidth(SERVO_GPIO, 0)
    pi.stop()
