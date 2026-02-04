import os, sys, threading
import RPi.GPIO as GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
import time
import spidev
from gpiozero import DigitalInputDevice
from scripts.ultrasonic_wake import start_ultrasonic_wake_thread

import board
import busio
import digitalio
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import ili9341

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from scripts.gui_view import start_gui
from scripts.screen.tft_ui import TFTUI

from scripts.sensors import read_moisture, read_light
from scripts.moisture_led_status import setup_leds, set_leds_by_raw


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
            "ui_awake": True,

            "moisture_percent": None,
            "moisture_raw": None,
            "moisture_led": "UNKNOWN",
            "light": None,
            "servo_text": servo_status(),
        }
    def set_awake(self, is_awake: bool):
        with self._lock:
            self.state["ui_awake"] = bool(is_awake)
        self._notify()

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

        if screen == "moisture":
            self.refresh_moisture(force_notify=True)
        elif screen == "light":
            self.refresh_light(force_notify=True)
        elif screen == "water":
            with self._lock:
                self.state["servo_text"] = servo_status()
            self._notify()
        else:
            self._notify()

    def refresh_moisture(self, force_notify=False):
        p, raw = read_moisture()
        led = set_leds_by_raw(raw)


        changed = False
        with self._lock:
            if force_notify:
                changed = True
            else:
                if self.state["moisture_percent"] != p: changed = True
                if self.state["moisture_led"] != led: changed = True
                # raw mag een beetje bewegen zonder notify (anders flikkert het)
                prev_raw = self.state["moisture_raw"]
                if prev_raw is None or abs(raw - prev_raw) >= 40:
                    changed = True

            self.state["moisture_percent"] = p
            self.state["moisture_raw"] = raw
            self.state["moisture_led"] = led

        if changed:
            self._notify()

    def refresh_light(self, force_notify=False):
        val = read_light()
        with self._lock:
            self.state["light"] = val
        if force_notify:
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
    start_ultrasonic_wake_thread(c)
    setup_leds()

    # TFT start (thread)
    tft = TFTUI(c)
    tft.start()

    # GUI start (main thread)
    root = start_gui(c)

    # auto loop: rustiger + re-entrancy guard
    running_tick = {"busy": False}

    def auto_moisture_tick():
        if running_tick["busy"]:
            root.after(700, auto_moisture_tick)
            return
        running_tick["busy"] = True
        try:
            c.refresh_moisture(force_notify=False)
        except Exception as e:
            print("moisture tick error:", e)
        finally:
            running_tick["busy"] = False
        root.after(300, auto_moisture_tick)

    auto_moisture_tick()

    c.goto("menu")
    root.mainloop()
