import os, sys, threading
import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
import time
import spidev
from gpiozero import DigitalInputDevice

import board
import busio
import digitalio
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import ili9341

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # .../controll scripts
sys.path.insert(0, BASE_DIR)  # zodat "scripts" gevonden wordt

from scripts.gui_view import start_gui
from scripts.screen.tft_ui import TFTUI

# Gebruik jouw lokale scripts map:
from scripts.sensors import read_moisture, read_light

# Als je servo file nog niet klaar is, kun je dit later koppelen.
# Voor nu: maak minimaal scripts/servo_plantwacht.py met open_kraan/dicht_kraan/status
try:
    from scripts.servo_plantwacht import open_kraan, dicht_kraan, status as servo_status
except Exception:
    def servo_status(): return "Servo: (nog niet gekoppeld)"
    def open_kraan(): return "Servo OPEN (dummy)"
    def dicht_kraan(): return "Servo DICHT (dummy)"


class Controller:
    def __init__(self):
        self._lock = threading.Lock()
        self._observers = []

        self.state = {
            "screen": "menu",
            "moisture_percent": None,
            "moisture_raw": None,
            "light": None,
            "servo_text": servo_status(),
        }

    def add_observer(self, fn):
        self._observers.append(fn)

    def _notify(self):
        for fn in self._observers:
            fn()

    def get_state_copy(self):
        with self._lock:
            return dict(self.state)

    def goto(self, screen):
        with self._lock:
            self.state["screen"] = screen

        # bij switch meteen data laden
        if screen == "moisture":
            self.refresh_moisture()
        elif screen == "light":
            self.refresh_light()
        elif screen == "water":
            with self._lock:
                self.state["servo_text"] = servo_status()
            self._notify()
        else:
            self._notify()

    def refresh_current(self):
        st = self.get_state_copy()
        if st["screen"] == "moisture":
            self.refresh_moisture()
        elif st["screen"] == "light":
            self.refresh_light()

    def refresh_moisture(self):
        p, raw = read_moisture()
        with self._lock:
            self.state["moisture_percent"] = p
            self.state["moisture_raw"] = raw
        self._notify()

    def refresh_light(self):
        val = read_light()
        with self._lock:
            self.state["light"] = val
        self._notify()

    def servo_open(self):
        def job():
            msg = open_kraan()
            with self._lock:
                self.state["servo_text"] = msg
            self._notify()
        threading.Thread(target=job, daemon=True).start()

    def servo_close(self):
        def job():
            msg = dicht_kraan()
            with self._lock:
                self.state["servo_text"] = msg
            self._notify()
        threading.Thread(target=job, daemon=True).start()


if __name__ == "__main__":
    c = Controller()

    # TFT start (thread)
    tft = TFTUI(c)
    tft.start()

    # GUI start (main thread)
    root = start_gui(c)

    # begin in menu
    c.goto("menu")

    root.mainloop()
