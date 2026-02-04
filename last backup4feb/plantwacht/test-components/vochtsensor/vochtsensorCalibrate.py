import time
from statistics import mean
import RPi.GPIO as GPIO

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

LED_GREEN = 16
LED_YELLOW = 20
LED_RED = 21

SAMPLES = 40
DELAY = 0.02

GREEN_FROM = 70
YELLOW_FROM = 35

# "snap back to dry" settings
DRY_SNAP_MARGIN = 15     # raw dichtbij DRY binnen marge
DRY_SNAP_SECONDS = 3.0   # zo lang dichtbij dry -> force 0%

def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))

def set_leds(pct):
    if pct >= GREEN_FROM:
        GPIO.output(LED_GREEN, True); GPIO.output(LED_YELLOW, False); GPIO.output(LED_RED, False)
        return "GREEN"
    elif pct >= YELLOW_FROM:
        GPIO.output(LED_GREEN, False); GPIO.output(LED_YELLOW, True); GPIO.output(LED_RED, False)
        return "YELLOW"
    else:
        GPIO.output(LED_GREEN, False); GPIO.output(LED_YELLOW, False); GPIO.output(LED_RED, True)
        return "RED"

def read_avg(ch):
    vals = []
    for _ in range(SAMPLES):
        vals.append(ch.value)
        time.sleep(DELAY)
    return int(mean(vals))

def piecewise_percent(raw, dry, moist, wet):
    pts = [(dry, 0), (moist, 50), (wet, 100)]
    pts.sort(key=lambda x: x[0])

    if raw <= pts[0][0]:
        return pts[0][1]
    if raw >= pts[2][0]:
        return pts[2][1]

    for (x1, y1), (x2, y2) in [(pts[0], pts[1]), (pts[1], pts[2])]:
        if x1 <= raw <= x2:
            if x2 == x1:
                return y1
            t = (raw - x1) / (x2 - x1)
            return int(round(y1 + t * (y2 - y1)))
    return 0

def main():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_GREEN, GPIO.OUT)
    GPIO.setup(LED_YELLOW, GPIO.OUT)
    GPIO.setup(LED_RED, GPIO.OUT)

    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    ads.gain = 1
    ch = AnalogIn(ads, 0)

    print("\n=== 3-PUNTS KALIBRATIE (DEMO) v2 ===")
    print("BELANGRIJK:")
    print("- Gebruik voor DRY: NIEUW kurkdroog papier (of zonder papier).")
    print("- Als je zoutwater gebruikt: sensor/papier blijft geleidend -> pak nieuw papier.\n")

    input("1) DROOG: druk ENTER...")
    dry = read_avg(ch)
    print(f"DRY avg_raw = {dry}")

    input("2) HALF-NAT (YELLOW): licht vochtig. ENTER...")
    moist = read_avg(ch)
    print(f"MOIST avg_raw = {moist}")

    input("3) NAT (GREEN): doorweekt/in water. ENTER...")
    wet = read_avg(ch)
    print(f"WET avg_raw = {wet}")

    span = max(dry, moist, wet) - min(dry, moist, wet)
    if span < 200:
        print("\n⚠️ WARNING: Je DRY/MOIST/WET liggen te dicht bij elkaar (span < 200).")
        print("Dat betekent: je test-opstelling geeft bijna geen verschil -> % en LEDs worden instabiel.")
        print("Fix: nieuw papier, beter contact, of gebruik een sponsje.\n")

    print(f"\nKalibratie: DRY={dry}, MOIST={moist}, WET={wet}")
    print("Live... Ctrl+C om te stoppen.\n")

    dry_close_start = None

    try:
        while True:
            raw = read_avg(ch)
            pct = clamp(piecewise_percent(raw, dry, moist, wet))

            # Snap back to dry (voorkomt 'blijft geel hangen')
            if abs(raw - dry) <= DRY_SNAP_MARGIN:
                if dry_close_start is None:
                    dry_close_start = time.time()
                elif (time.time() - dry_close_start) >= DRY_SNAP_SECONDS:
                    pct = 0
            else:
                dry_close_start = None

            led = set_leds(pct)
            print(f"raw={raw}  moisture={pct}%  LED={led}")
            time.sleep(0.3)

    except KeyboardInterrupt:
        pass
    finally:
        GPIO.output(LED_GREEN, False)
        GPIO.output(LED_YELLOW, False)
        GPIO.output(LED_RED, False)
        GPIO.cleanup()

if __name__ == "__main__":
    main()


