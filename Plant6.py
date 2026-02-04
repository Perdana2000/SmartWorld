import tkinter as tk
import time
import threading
import RPi.GPIO as GPIO
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from scripts.servo_plantwacht import open_kraan, dicht_kraan, status as servo_status

# ---------------------------------------------------------
# CONFIGURATIE & PINS
# ---------------------------------------------------------
GPIO.setmode(GPIO.BCM)
TRIG = 23  # Aangepast
ECHO = 24  # Aangepast
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

# Kalibratie waarden
WET = 12000
DRY = 26000


# ---------------------------------------------------------
# HARDWARE FUNCTIES
# ---------------------------------------------------------
def afstand():
    """Berekent afstand met HC-SR04 inclusief timeout bescherming."""
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    pulse_start = time.time()
    pulse_end = time.time()

    t0 = time.time()
    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
        if time.time() - t0 > 0.05: return 999  # Timeout

    t1 = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()
        if time.time() - t1 > 0.05: return 999

    pulse_duration = pulse_end - pulse_start
    return round(pulse_duration * 17150, 2)


def get_moisture_data():
    """Leest de ADS1115 uit. Geeft mock-data bij fouten."""
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        ads = ADS.ADS1115(i2c)
        chan = AnalogIn(ads, ADS.P0)
        raw = chan.value
        percent = max(0, min(100, (DRY - raw) * 100 / (DRY - WET)))
        return int(percent), raw
    except:
        return 50, 20000  # Mock data


# ---------------------------------------------------------
# GUI LOGICA
# ---------------------------------------------------------
root = tk.Tk()
root.title("Smart Plant – Final")
root.geometry("480x320")
root.withdraw()  # Start verborgen


def clear_screen():
    for widget in root.winfo_children():
        widget.destroy()


def show_start_screen():
    clear_screen()
    tk.Label(root, text="Smart Plant Menu", font=("Arial", 22)).pack(pady=20)
    tk.Button(root, text="🌱 Vochtmeting", font=("Arial", 18), width=20, command=show_moisture_screen).pack(pady=10)
    tk.Button(root, text="💧 Water geven", font=("Arial", 18), width=20, command=show_water_screen).pack(pady=10)


def show_moisture_screen():
    clear_screen()
    p, r = get_moisture_data()
    tk.Label(root, text="Vochtmeting", font=("Arial", 22)).pack(pady=20)
    tk.Label(root, text=f"{p}%", font=("Arial", 40), fg="blue").pack(pady=10)
    tk.Button(root, text="← Terug", command=show_start_screen).pack(pady=20)


def show_water_screen():
    clear_screen()
    tk.Label(root, text="Handmatig Water", font=("Arial", 22)).pack(pady=20)

    status_label = tk.Label(root, text=servo_status(), font=("Arial", 14))
    status_label.pack(pady=10)

    def water_task(action):
        if action == "open":
            msg = open_kraan()
        else:
            msg = dicht_kraan()
        status_label.config(text=msg)

    tk.Button(root, text="OPEN KRAAN", bg="green", fg="white", font=("Arial", 14),
              command=lambda: water_task("open")).pack(side="left", padx=40, pady=20)
    tk.Button(root, text="SLUIT KRAAN", bg="red", fg="white", font=("Arial", 14),
              command=lambda: water_task("dicht")).pack(side="right", padx=40, pady=20)
    tk.Button(root, text="← Terug", command=show_start_screen).pack(side="bottom", pady=20)


# ---------------------------------------------------------
# ACHTERGROND PROCES (Nabijheid)
# ---------------------------------------------------------
def proximity_check():
    """Wacht tot iemand binnen 50cm komt om het scherm te activeren."""
    while True:
        d = afstand()
        if d <= 50:
            root.after(0, root.deiconify)
            root.after(0, show_start_screen)
            break
        time.sleep(0.5)


# Start de nabijheidscheck in een aparte thread
threading.Thread(target=proximity_check, daemon=True).start()

root.mainloop()
GPIO.cleanup()