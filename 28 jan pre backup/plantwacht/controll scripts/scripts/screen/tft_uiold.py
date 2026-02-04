import time
import threading
import spidev
from gpiozero import DigitalInputDevice

import board
import busio
import digitalio
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import ili9341


def load_font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except:
        return ImageFont.load_default()


class TFTUI(threading.Thread):
    """
    TFT + Touch UI, synced met jouw Controller.
    Touch code is direct gebaseerd op jouw werkende tft_menu_touch_landscape.py
    """
    def __init__(self, controller):
        super().__init__(daemon=True)
        self.c = controller
        self.running = True

        # =========================
        # DISPLAY (TFT) - JOUW PINS
        # =========================
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

        self.tft_cs  = digitalio.DigitalInOut(board.CE0)
        self.tft_dc  = digitalio.DigitalInOut(board.D6)
        self.tft_rst = digitalio.DigitalInOut(board.D5)

        self.ROTATION = 90  # landscape (moet 0/90/180/270)
        self.display = ili9341.ILI9341(
            spi,
            cs=self.tft_cs,
            dc=self.tft_dc,
            rst=self.tft_rst,
            rotation=self.ROTATION,
            baudrate=1000000  # houd 'm hetzelfde als jouw werkende script; later kunnen we sneller
        )

        # W/H op basis van rotation
        if self.ROTATION in (90, 270):
            self.W, self.H = 320, 240
        else:
            self.W, self.H = 240, 320

        # =========================
        # TOUCH (XPT2046) via spidev
        # =========================
        self.touch_spi = spidev.SpiDev()
        self.touch_spi.open(0, 1)               # SPI0, CE1 = /dev/spidev0.1
        self.touch_spi.max_speed_hz = 2000000
        self.touch_spi.mode = 0

        self.irq = DigitalInputDevice(22, pull_up=True)  # T_IRQ op GPIO22 (active-low)

        self.CMD_X = 0xD0
        self.CMD_Y = 0x90

        # =========================
        # TOUCH CALIBRATIE (zoals jouw werkende script)
        # =========================
        self.TOUCH_X_MIN = 200
        self.TOUCH_X_MAX = 3900
        self.TOUCH_Y_MIN = 200
        self.TOUCH_Y_MAX = 3900

        self.TOUCH_SWAP_XY = True
        self.TOUCH_INVERT_X = False
        self.TOUCH_INVERT_Y = True

        # =========================
        # UI fonts
        # =========================
        self.font_title = load_font(26)
        self.font_btn   = load_font(20)
        self.font_small = load_font(14)

        # =========================
        # UI layout (kleine buttons, landscape)
        # =========================
        self.MARGIN_X = 70
        self.BTN_W = self.W - 2 * self.MARGIN_X
        self.BTN_H = 52
        self.GAP = 14
        self.TITLE_Y = 8
        self.TOP_Y = 55

        # caching om redraw te beperken
        self._last_key = None

        # debounce
        self.last_press = 0
        self.DEBOUNCE = 0.25  # exact als werkende script

        # init draw
        self.display.image(self._draw_from_state(self.c.get_state_copy()))

        print("[TFTUI] gestart: TFT CE0 + Touch CE1 + IRQ GPIO22")

    # -------- touch helpers (1-op-1 uit jouw script) --------
    def read_12bit(self, cmd: int) -> int:
        r = self.touch_spi.xfer2([cmd, 0x00, 0x00])
        val = ((r[1] << 8) | r[2]) >> 3
        return val & 0x0FFF

    def get_touch_raw(self, samples=7):
        if self.irq.value:  # IRQ high = niet touched
            return None

        xs, ys = [], []
        for _ in range(samples):
            xs.append(self.read_12bit(self.CMD_X))
            ys.append(self.read_12bit(self.CMD_Y))
            time.sleep(0.001)

        xs.sort(); ys.sort()
        xs = xs[1:-1]
        ys = ys[1:-1]

        rx = sum(xs) // len(xs)
        ry = sum(ys) // len(ys)

        if rx in (0, 4095) or ry in (0, 4095):
            return None
        return rx, ry

    def clamp(self, v, lo, hi):
        return lo if v < lo else hi if v > hi else v

    def map_range(self, v, in_min, in_max, out_min, out_max):
        v = self.clamp(v, in_min, in_max)
        return int((v - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

    def touch_to_screen(self, rx, ry):
        if self.TOUCH_SWAP_XY:
            rx, ry = ry, rx

        x = self.map_range(rx, self.TOUCH_X_MIN, self.TOUCH_X_MAX, 0, self.W - 1)
        y = self.map_range(ry, self.TOUCH_Y_MIN, self.TOUCH_Y_MAX, 0, self.H - 1)

        if self.TOUCH_INVERT_X:
            x = (self.W - 1) - x
        if self.TOUCH_INVERT_Y:
            y = (self.H - 1) - y

        return x, y

    # -------- UI helpers --------
    def button_rect(self, i):
        x1 = self.MARGIN_X
        y1 = self.TOP_Y + i * (self.BTN_H + self.GAP)
        x2 = x1 + self.BTN_W
        y2 = y1 + self.BTN_H
        return (x1, y1, x2, y2)

    def point_in_rect(self, x, y, r):
        x1, y1, x2, y2 = r
        return x1 <= x <= x2 and y1 <= y <= y2

    def _draw_menu(self, status_text="tik een knop"):
        img = Image.new("RGB", (self.W, self.H), (235, 235, 235))
        d = ImageDraw.Draw(img)

        title = "Smart Plant Menu"
        tw, th = d.textsize(title, font=self.font_title)
        d.text(((self.W - tw)//2, self.TITLE_Y), title, font=self.font_title, fill=(0, 0, 0))

        labels = ["Vochtmeting", "Lichtmeting", "Water geven"]
        for i, label in enumerate(labels):
            r = self.button_rect(i)
            d.rectangle(r, outline=(0, 0, 0), width=2, fill=(245, 245, 245))
            lw, lh = d.textsize(label, font=self.font_btn)
            x1, y1, x2, y2 = r
            d.text(((x1 + x2 - lw)//2, (y1 + y2 - lh)//2),
                   label, font=self.font_btn, fill=(0, 0, 0))

        if status_text:
            d.text((10, self.H - 18), status_text, font=self.font_small, fill=(20, 20, 20))

        return img

    def _draw_page(self, screen_id, st):
        img = Image.new("RGB", (self.W, self.H), (235, 235, 235))
        d = ImageDraw.Draw(img)

        title_map = {
            "moisture": "Vochtmeting",
            "light": "Lichtmeting",
            "water": "Water geven",
        }
        title = title_map.get(screen_id, screen_id)
        tw, th = d.textsize(title, font=self.font_title)
        d.text(((self.W - tw)//2, self.TITLE_Y), title, font=self.font_title, fill=(0, 0, 0))

        # simple back button
        self.back_rect = (10, self.H-50, 120, self.H-10)
        d.rectangle(self.back_rect, outline=(0,0,0), width=2, fill=(245,245,245))
        d.text((22, self.H-42), "< Terug", font=self.font_btn, fill=(0,0,0))

        if screen_id == "moisture":
            d.text((20, 70), f"Vocht: {st.get('moisture_percent','-')} %", font=self.font_btn, fill=(0,0,0))
            d.text((20, 105), f"Raw: {st.get('moisture_raw','-')}", font=self.font_btn, fill=(0,0,0))
            self.refresh_rect = (self.W-140, self.H-50, self.W-10, self.H-10)
            d.rectangle(self.refresh_rect, outline=(0,0,0), width=2, fill=(245,245,245))
            d.text((self.W-132, self.H-42), "Vernieuw", font=self.font_btn, fill=(0,0,0))

        elif screen_id == "light":
            d.text((20, 80), f"Licht: {st.get('light','-')}", font=self.font_btn, fill=(0,0,0))
            self.refresh_rect = (self.W-140, self.H-50, self.W-10, self.H-10)
            d.rectangle(self.refresh_rect, outline=(0,0,0), width=2, fill=(245,245,245))
            d.text((self.W-132, self.H-42), "Vernieuw", font=self.font_btn, fill=(0,0,0))

        elif screen_id == "water":
            d.text((20, 70), str(st.get("servo_text","")), font=self.font_small, fill=(0,0,0))

            self.open_rect = (30, 120, 150, 190)
            self.close_rect = (170, 120, 290, 190)
            d.rectangle(self.open_rect, outline=(0,0,0), width=2, fill=(210,255,210))
            d.rectangle(self.close_rect, outline=(0,0,0), width=2, fill=(255,210,210))
            d.text((60, 145), "OPEN", font=self.font_btn, fill=(0,0,0))
            d.text((198, 145), "DICHT", font=self.font_btn, fill=(0,0,0))

        return img

    def _draw_from_state(self, st):
        screen_id = st.get("screen", "menu")

        # caching key
        key = (
            screen_id,
            st.get("moisture_percent"),
            st.get("moisture_raw"),
            st.get("light"),
            st.get("servo_text"),
        )
        if key == self._last_key:
            return None
        self._last_key = key

        if screen_id == "menu":
            return self._draw_menu()
        return self._draw_page(screen_id, st)

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            st = self.c.get_state_copy()

            img = self._draw_from_state(st)
            if img is not None:
                self.display.image(img)

            raw = self.get_touch_raw()
            if raw and (time.time() - self.last_press) > self.DEBOUNCE:
                self.last_press = time.time()
                rx, ry = raw
                sx, sy = self.touch_to_screen(rx, ry)

                # MENU
                if st.get("screen") == "menu":
                    if self.point_in_rect(sx, sy, self.button_rect(0)):
                        self.c.goto("moisture")
                    elif self.point_in_rect(sx, sy, self.button_rect(1)):
                        self.c.goto("light")
                    elif self.point_in_rect(sx, sy, self.button_rect(2)):
                        self.c.goto("water")

                # PAGES
                else:
                    if hasattr(self, "back_rect") and self.point_in_rect(sx, sy, self.back_rect):
                        self.c.goto("menu")

                    if st.get("screen") in ("moisture", "light"):
                        if hasattr(self, "refresh_rect") and self.point_in_rect(sx, sy, self.refresh_rect):
                            self.c.refresh_current()

                    if st.get("screen") == "water":
                        if hasattr(self, "open_rect") and self.point_in_rect(sx, sy, self.open_rect):
                            self.c.servo_open()
                        elif hasattr(self, "close_rect") and self.point_in_rect(sx, sy, self.close_rect):
                            self.c.servo_close()

            time.sleep(0.02)
