import time
import RPi.GPIO as GPIO

LED_GREEN = 16
LED_YELLOW = 20
LED_RED = 21

# jouw kalibratie raw
DRY   = 4837
MOIST = 4939
WET   = 5274

# ===== DEMO tuning (brede geel zone) =====
# Geel moet al bij kleine druppels kunnen verschijnen:
MOIST_MARGIN = 60   # eerder geel
# Groen eerder als echt nat:
WET_MARGIN   = 140  # eerder groen

# anti-flikker
HYST_RAW = 10
MIN_HOLD = 0.35     # sneller dan eerst

_current = None
_last_change = 0.0

def setup_leds():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_GREEN, GPIO.OUT)
    GPIO.setup(LED_YELLOW, GPIO.OUT)
    GPIO.setup(LED_RED, GPIO.OUT)
    all_off()

def all_off():
    GPIO.output(LED_GREEN, False)
    GPIO.output(LED_YELLOW, False)
    GPIO.output(LED_RED, False)

def _set(color):
    GPIO.output(LED_GREEN, color == "GREEN")
    GPIO.output(LED_YELLOW, color == "YELLOW")
    GPIO.output(LED_RED, color == "RED")

def _desired(raw: int) -> str:
    if raw >= (WET - WET_MARGIN):
        return "GREEN"
    if raw >= (MOIST - MOIST_MARGIN):
        return "YELLOW"
    return "RED"

def set_leds_by_raw(raw: int) -> str:
    global _current, _last_change

    if raw is None:
        _current = None
        all_off()
        return "UNKNOWN"

    now = time.time()

    if _current is None:
        _current = _desired(raw)
        _set(_current)
        _last_change = now
        return _current

    if (now - _last_change) < MIN_HOLD:
        _set(_current)
        return _current

    if _current == "RED":
        if raw >= (MOIST - MOIST_MARGIN + HYST_RAW):
            _current = "YELLOW"
            _last_change = now

    elif _current == "YELLOW":
        if raw <= (MOIST - MOIST_MARGIN - HYST_RAW):
            _current = "RED"
            _last_change = now
        elif raw >= (WET - WET_MARGIN + HYST_RAW):
            _current = "GREEN"
            _last_change = now

    elif _current == "GREEN":
        if raw <= (WET - WET_MARGIN - HYST_RAW):
            _current = "YELLOW"
            _last_change = now

    _set(_current)
    return _current
