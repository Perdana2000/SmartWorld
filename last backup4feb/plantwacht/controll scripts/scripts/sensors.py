import time
from collections import deque
from statistics import median

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# VASTE KALIBRATIE (jouw waarden)
DRY   = 4837
MOIST = 4939
WET   = 5274

# ===== Snelle sample per tick =====
SAMPLES = 15            # snel genoeg
DELAY = 0.001           # klein (I2C call kost al tijd)

# ===== Stabiliteit over tijd =====
HISTORY_N = 9           # rolling median -> stabiel maar responsief
_raw_hist = deque(maxlen=HISTORY_N)

# ADC init
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
ads.gain = 1
ch0 = AnalogIn(ads, 0)  # A0


def clamp(x, lo=0, hi=100):
    return max(lo, min(hi, x))


def _read_raw_fast():
    vals = []
    for _ in range(SAMPLES):
        try:
            vals.append(int(ch0.value))
        except Exception:
            pass
        time.sleep(DELAY)

    if not vals:
        return None

    return int(median(vals))


def _piecewise_percent(raw, dry, moist, wet):
    # 3-punts mapping: (dry,0) (moist,50) (wet,100) met sort
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


def read_moisture():
    """
    Returns: (percent, raw_stable)
    raw_stable = rolling median over de laatste HISTORY_N metingen.
    """
    raw_fast = _read_raw_fast()

    if raw_fast is None:
        # fail-safe
        if _raw_hist:
            raw_stable = int(median(_raw_hist))
            pct = clamp(_piecewise_percent(raw_stable, DRY, MOIST, WET))
            return pct, raw_stable
        return 0, 0

    _raw_hist.append(raw_fast)

    raw_stable = int(median(_raw_hist))  # super stabiel, maar niet traag
    pct = clamp(_piecewise_percent(raw_stable, DRY, MOIST, WET))
    return pct, raw_stable


def read_light():
    return None  # skip
