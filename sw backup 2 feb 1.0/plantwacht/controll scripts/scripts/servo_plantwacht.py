import time
import pigpio

SERVO_GPIO = 18

# MG90S (kan je later tunen)
MIN_US = 600
MAX_US = 2400

# Kraan posities (tune dit op jouw mechaniek)
CLOSED_ANGLE = 60
OPEN_ANGLE = 70

MOVE_TIME = 0.8

pi = None
kraan_status = "unknown"   # "open" / "dicht" / "unknown"

def start_pi():
    global pi
    if pi is None:
        pi = pigpio.pi()
        if not pi.connected:
            raise SystemExit("pigpiod draait niet. Start: sudo systemctl start pigpiod")

def angle_to_pulse(a):
    a = max(0, min(180, a))
    return int(MIN_US + (a/180) * (MAX_US - MIN_US))

def move_to(angle):
    start_pi()
    pulse = angle_to_pulse(angle)
    pi.set_servo_pulsewidth(SERVO_GPIO, pulse)
    time.sleep(MOVE_TIME)

def open_kraan():
    global kraan_status
    if kraan_status == "open":
        return "Kraan staat al open."
    move_to(OPEN_ANGLE)
    kraan_status = "open"
    return "Kraan is nu OPEN."

def dicht_kraan():
    global kraan_status
    if kraan_status == "dicht":
        return "Kraan is al dicht."
    move_to(CLOSED_ANGLE)
    kraan_status = "dicht"
    return "Kraan is nu DICHT."

def status():
    if kraan_status == "unknown":
        return "Status onbekend (nog niks gedaan)."
    return f"Status: {kraan_status}"

def stop_all():
    global pi
    if pi is not None:
        pi.set_servo_pulsewidth(SERVO_GPIO, 0)
        pi.stop()
        pi = None

if __name__ == "__main__":
    # snelle test
    print(open_kraan())
    time.sleep(2)
    print(dicht_kraan())
    stop_all()
