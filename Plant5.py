import tkinter as tk
import random
import time
import RPi.GPIO as GPIO
import threading

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# ---------------------------------------------------------
# GPIO / ULTRASONIC SENSOR (HC-SR04)
# ---------------------------------------------------------
GPIO.setmode(GPIO.BCM)
TRIG = 16
ECHO = 18
GPIO.setup(TRIG, GPIO.OUT)
GPIO.setup(ECHO, GPIO.IN)

SERVO_PIN = 6

GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

def move_servo(angle):
    duty = 2 + (angle / 18)
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)
    pwm.ChangeDutyCycle(0)

def afstand():
    GPIO.output(TRIG, True)
    time.sleep(0.00001)
    GPIO.output(TRIG, False)

    pulse_start = time.time()
    pulse_end = time.time()

    while GPIO.input(ECHO) == 0:
        pulse_start = time.time()
    while GPIO.input(ECHO) == 1:
        pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    afstand_cm = pulse_duration * 17150
    return round(afstand_cm, 2)

# ---------------------------------------------------------
# ADS1115 – MOISTURE SENSOR
# ---------------------------------------------------------
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
ads.gain = 1  # ±4.096V (geschikt voor 3.3V)

moisture_channel = AnalogIn(ads,0)
light_channel = AnalogIn(ads,2)

# Kalibratiewaarden (AANPASSEN!)
WET = 12000    # natte grond / water
DRY = 26000    # droge lucht

def read_moisture():
    raw = moisture_channel.value
    percent = (DRY - raw) * 100 / (DRY - WET)
    percent = max(0, min(100, percent))
    return int(percent), raw

# ---------------------------------------------------------
# MOCK FUNCTIES (ALLEEN LICHT & SERVO) Welke versie van de servo bestanden werkt er nu?
# ---------------------------------------------------------
DARK = 2000
BRIGHT = 30000

def read_light():
    raw = light_channel.value
    
    percent = (raw - DARK) * 100 / (BRIGHT - DARK)
    percent = max(0, min(100, percent))
    
    return int(percent), raw

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
    
    light_percent, raw_value = read_light()

    tk.Label(root, text="Lichtmeting", font=("Arial", 22)).pack(pady=20)
    
    tk.Label(root, text=f"Lichtsterkte: {light_percent}%",
             font=("Arial", 20)).pack(pady=10)
    tk.Label(root, text=f"Ruwe waarde: {raw_value}",
             font=("Arial", 14)).pack(pady=10)
    tk.Button(root, text="← Terug", font=("Arial", 16),
              command=show_start_screen).pack(pady=30)

# ---------------------------------------------------------
# SCHERM: WATER GEVEN
# ---------------------------------------------------------
def show_water_screen():
    clear_screen()
    tk.Label(root, text="Water geven?", font=("Arial", 22)).pack(pady=30)

    frame = tk.Frame(root)
    frame.pack(pady=20)

    tk.Button(frame, text="❌ Niet water geven", font=("Arial", 16),
              bg="red", fg="white", width=15, height=3,
              command=show_start_screen).grid(row=0, column=0, padx=20)

    tk.Button(frame, text="✔ Water geven", font=("Arial", 16),
              bg="green", fg="white", width=15, height=3,
              command=water_action).grid(row=0, column=1, padx=20)

    tk.Button(root, text="← Terug", font=("Arial", 16),
              command=show_start_screen).pack(pady=30)

# ---------------------------------------------------------
# WATER ACTIE
# ---------------------------------------------------------
def water_action():
    clear_screen()
    tk.Label(root, text="Water wordt gegeven...", font=("Arial", 22)).pack(pady=40)
    root.update()
    
    print("Servo draait...")
    move_servo(90)
    time.sleep(1)
    move_servo(0)
    
    tk.Label(root, text="Water geven klaar!", font=("Arial", 18)).pack(pady=20)
    tk.Button(root, text="← Terug", font=("Arial", 16),
              command=show_start_screen).pack(pady=40)

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

def Moisture_Automatic_Reading():
    
    while True:
        percent, raw = read_moisture()
        
        print(f"Vocht: {percent}% Ruwe waarde: {raw}")
        
        time.sleep(5)
              
thread = threading.Thread(target=Moisture_Automatic_Reading, daemon=True)
thread.start()

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------

wacht_op_nabijheid()
root.mainloop()
Moisture_Automatic_Reading()