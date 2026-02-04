import time
import threading
import RPi.GPIO as GPIO
from collections import deque

# PINS (BCM)
TRIG_PIN = 23
ECHO_PIN = 19

# instellingen
THRESHOLD_CM = 70
POLL_HZ = 8                     # 8x per seconde meten
HYSTERESIS_CM = 8               # voorkomt flappen rond 70cm
ON_CONFIRM = 2                  # aantal metingen onder threshold -> aan
OFF_CONFIRM = 3                 # aantal metingen boven threshold+hysteresis -> uit

SPEED_OF_SOUND = 34300  # cm/s

# filtering
FILTER_N = 5                    # moving average over laatste N geldige metingen
VALID_MIN_CM = 2
VALID_MAX_CM = 500


def _setup():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG_PIN, GPIO.OUT)
    GPIO.setup(ECHO_PIN, GPIO.IN)
    GPIO.output(TRIG_PIN, False)
    time.sleep(0.05)


def read_distance_cm(timeout_s=0.03):
    """
    HC-SR04 distance in cm.
    returns float cm or None if timeout/invalid.
    """
    # trigger pulse 10us
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, False)

    start = time.time()

    # wait for echo high
    while GPIO.input(ECHO_PIN) == 0:
        if time.time() - start > timeout_s:
            return None
    pulse_start = time.time()

    # wait for echo low
    while GPIO.input(ECHO_PIN) == 1:
        if time.time() - pulse_start > timeout_s:
            return None
    pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance = (pulse_duration * SPEED_OF_SOUND) / 2.0

    if distance < VALID_MIN_CM or distance > VALID_MAX_CM:
        return None

    return distance


def start_ultrasonic_wake_thread(controller, debug=True):
    """
    Background thread: toggles controller.ui_awake based on distance.
    """
    _setup()

    def worker():
        awake = True
        on_hits = 0
        off_hits = 0

        # smoothing buffer
        buf = deque(maxlen=FILTER_N)

        # start state: keep UI on at boot
        try:
            controller.set_awake(True)
        except Exception:
            pass

        period = 1.0 / float(POLL_HZ)

        while True:
            d = read_distance_cm()

            # debug print zonder crash
            if debug:
                if d is None:
                    print("[ULTRA] timeout/invalid")
                else:
                    print(f"[ULTRA] {d:.1f} cm")

            # ignore invalid reads
            if d is None:
                time.sleep(period)
                continue

            # update filter
            buf.append(d)
            d_f = sum(buf) / len(buf)

            # decide zones with hysteresis using filtered distance
            if awake:
                # to go OFF: needs to be clearly far (threshold + hysteresis)
                if d_f > (THRESHOLD_CM + HYSTERESIS_CM):
                    off_hits += 1
                    on_hits = 0
                else:
                    off_hits = 0

                if off_hits >= OFF_CONFIRM:
                    awake = False
                    off_hits = 0
                    try:
                        controller.set_awake(False)
                    except Exception:
                        pass

            else:
                # to go ON: needs to be under/equal threshold
                if d_f <= THRESHOLD_CM:
                    on_hits += 1
                    off_hits = 0
                else:
                    on_hits = 0

                if on_hits >= ON_CONFIRM:
                    awake = True
                    on_hits = 0
                    try:
                        controller.set_awake(True)
                    except Exception:
                        pass

            time.sleep(period)

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return t
