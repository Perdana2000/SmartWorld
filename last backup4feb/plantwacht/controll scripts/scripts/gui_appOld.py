import os, sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # .../plantwacht/script-van-team
PROJECT_DIR = os.path.dirname(BASE_DIR)                 # .../plantwacht
sys.path.insert(0, PROJECT_DIR)


import tkinter as tk
import random
import time
import threading
import RPi.GPIO as GPIO

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# ✅ jouw servo functies (van scripts/servo_plantwacht.py)
from scripts.servo_plantwacht import open_kraan, dicht_kraan, status as servo_status


# ---------------------------------------------------------
# GPIO / ULTRASONIC SENSOR (HC-SR04)
# ---------------------------------------------------------
GPIO.setmode(GPIO.BCM)

# ✅ PIN CONFLICT FIX: NIET 18 gebruiken (want servo zit daar)
TRIG = 23
ECHO = 24

GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

def afstand():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    pulse_start = time.time()
    pulse_end = time.time()

    # simpele timeout bescherming
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
    afstand_cm = pulse_duration * 17150
    return round(afstand_cm, 2)


# ---------------------------------------------------------
# ADS1115 – MOISTURE SENSOR
# ---------------------------------------------------------
# i2c = busio.I2C(board.SCL, board.SDA)
# ads = ADS.ADS1115(i2c)
# ads.gain = 1
# 
# moisture_channel = AnalogIn(ads, ADS.P0)
# 
# # Kalibratiewaarden (AANPASSEN!)
# WET = 12000
# DRY = 26000
# 
# def read_moisture():
#     raw = moisture_channel.value
#     percent = (DRY - raw) * 100 / (DRY - WET)
#     percent = max(0, min(100, percent))
#     return int(percent), raw
#


import random

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
        return int(percent), raw

except Exception as e:
    USE_ADC = False
    print("ADC/ADS1115 niet beschikbaar -> MOCK moisture. Error:", e)

    def read_moisture():
        # fake values zodat GUI werkt
        percent = random.randint(0, 100)
        raw = random.randint(10000, 30000)
        return percent, raw


# ---------------------------------------------------------
# MOCK FUNCTIE (LICHT)
# ---------------------------------------------------------
def read_mock_light():
    return random.randint(100, 1000)


# ---------------------------------------------------------
# APP BASIS
# ---------------------------------------------------------
root = tk.Tk()
root.title("Smart Plant – Testversie")
root.geometry("480x320")
root.withdraw()

def clear_screen():
    for widget in root.winfo_children():
        widget.destroy()


# ---------------------------------------------------------
# STARTSCHERM
# ---------------------------------------------------------
def show_start_screen():
    clear_screen()
    tk.Label(root, text="Smart Plant Menu", font=("Arial", 22)).pack(pady=20)

    tk.Button(root, text="🌱 Vochtmeting", font=("Arial", 18), width=20, height=2,
              command=show_moisture_screen).pack(pady=10)

    tk.Button(root, text="☀ Lichtmeting", font=("Arial", 18), width=20, height=2,
              command=show_light_screen).pack(pady=10)

    tk.Button(root, text="💧 Water geven", font=("Arial", 18), width=20, height=2,
              command=show_water_screen).pack(pady=10)


# ---------------------------------------------------------
# SCHERM: VOCHTMETING
# ---------------------------------------------------------
def show_moisture_screen():
    clear_screen()
    moisture_percent, raw_value = read_moisture()

    tk.Label(root, text="Vochtmeting", font=("Arial", 22)).pack(pady=20)
    tk.Label(root, text=f"Vochtpercentage: {moisture_percent}%",
             font=("Arial", 20)).pack(pady=10)
    tk.Label(root, text=f"Ruwe waarde: {raw_value}",
             font=("Arial", 14)).pack(pady=10)

    tk.Button(root, text="← Terug", font=("Arial", 16),
              command=show_start_screen).pack(pady=30)


# ---------------------------------------------------------
# SCHERM: LICHTMETING
# ---------------------------------------------------------
def show_light_screen():
    clear_screen()
    light = read_mock_light()

    tk.Label(root, text="Lichtmeting", font=("Arial", 22)).pack(pady=20)
    tk.Label(root, text=f"Lichtsterkte: {light}",
             font=("Arial", 20)).pack(pady=20)

    tk.Button(root, text="← Terug", font=("Arial", 16),
              command=show_start_screen).pack(pady=30)


# ---------------------------------------------------------
# SCHERM: WATER GEVEN
# ---------------------------------------------------------
def show_water_screen():
    clear_screen()

    tk.Label(root, text="Water menu", font=("Arial", 22)).pack(pady=20)

    lbl = tk.Label(root, text=servo_status(), font=("Arial", 16))
    lbl.pack(pady=10)

    def run_in_thread(fn):
        def task():
            msg = fn()
            # update label terug in UI thread:
            root.after(0, lambda: lbl.config(text=msg))
        threading.Thread(target=task, daemon=True).start()

    frame = tk.Frame(root)
    frame.pack(pady=20)

    tk.Button(frame, text="OPEN", font=("Arial", 16),
              bg="green", fg="white", width=12, height=3,
              command=lambda: run_in_thread(open_kraan)).grid(row=0, column=0, padx=15)

    tk.Button(frame, text="DICHT", font=("Arial", 16),
              bg="red", fg="white", width=12, height=3,
              command=lambda: run_in_thread(dicht_kraan)).grid(row=0, column=1, padx=15)

    tk.Button(root, text="← Terug", font=("Arial", 16),
              command=show_start_screen).pack(pady=30)


# ---------------------------------------------------------
# START APP BIJ NABIJHEID
# ---------------------------------------------------------
def wacht_op_nabijheid(drempel_cm=50):
    try:
        print("Wacht op nabijheid...")
        while True:
            d = afstand()
            print(f"Afstand: {d} cm")
            if d <= drempel_cm:
                print("Iemand dichtbij! Start app...")
                root.deiconify()
                show_start_screen()
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        GPIO.cleanup()


# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
# wacht_op_nabijheid()
# root.mainloop()
# GPIO.cleanup()
root.deiconify()
show_start_screen()
root.mainloop()
