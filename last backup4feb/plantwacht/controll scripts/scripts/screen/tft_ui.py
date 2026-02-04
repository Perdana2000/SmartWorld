import time
import threading
import spidev
from gpiozero import DigitalInputDevice
import os

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

    Touch verbeteringen:
    - median sampling (stabieler met vinger)
    - press->release click (minder dubbele taps)
    - grotere menu hitbox (makkelijker klikken)
    - iets snellere debounce
    """

    def __init__(self, controller):
        super().__init__(daemon=True)
        self.c = controller
        self.running = True

        # =========================
        # DISPLAY (TFT)
        # =========================
        spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

        self.tft_cs  = digitalio.DigitalInOut(board.CE0)
        self.tft_dc  = digitalio.DigitalInOut(board.D6)
        self.tft_rst = digitalio.DigitalInOut(board.D5)

        self.ROTATION = 90  # landscape
        self.display = ili9341.ILI9341(
            spi,
            cs=self.tft_cs,
            dc=self.tft_dc,
            rst=self.tft_rst,
            rotation=self.ROTATION,
            baudrate=1000000
        )

        if self.ROTATION in (90, 270):
            self.W, self.H = 320, 240
        else:
            self.W, self.H = 240, 320

        # =========================
        # TOUCH (XPT2046)
        # =========================
        self.touch_spi = spidev.SpiDev()
        self.touch_spi.open(0, 1)               # SPI0, CE1 = /dev/spidev0.1
        self.touch_spi.max_speed_hz = 2000000
        self.touch_spi.mode = 0

        self.irq = DigitalInputDevice(22, pull_up=True)  # T_IRQ op GPIO22 (active-low)

        self.CMD_X = 0xD0
        self.CMD_Y = 0x90

        # =========================
        # TOUCH CALIBRATIE (JOUW WAARDEN)
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
        self.font_title = load_font(24)
        self.font_btn   = load_font(16)
        self.font_small = load_font(12)
        self.font_big   = load_font(28)

        # =========================
        # UI layout
        # =========================
        self.MARGIN_X = 70
        self.BTN_W = self.W - 2 * self.MARGIN_X
        self.BTN_H = 45
        self.GAP = 5
        self.TITLE_Y = 8
        self.TOP_Y = 40

        # caching om redraw te beperken
        self._last_key = None

        # debounce
        self.last_press = 0
        self.DEBOUNCE = 0.18

        # =========================
        # SMILEY ASSETS
        # =========================
        self.GREEN_FROM = 70
        self.YELLOW_FROM = 35

        self.smileys = {"red": None, "yellow": None, "green": None}
        self._load_smileys()

        # init draw
        img = self._draw_from_state(self.c.get_state_copy())
        if img is not None:
            self.display.image(img)

        print("[TFTUI] gestart: TFT CE0 + Touch CE1 + IRQ GPIO22")

    # ---------- smiley helpers ----------
    def _asset_dir(self):
        base = os.path.dirname(os.path.abspath(__file__))  # .../scripts/screen
        scripts_dir = os.path.dirname(base)                # .../scripts
        return os.path.join(scripts_dir, "assets")

    def _open_first_existing(self, paths):
        for p in paths:
            if os.path.exists(p):
                return Image.open(p).convert("RGBA")
        return None

    def _load_smileys(self):
        assets = self._asset_dir()

        red_candidates = [
            os.path.join(assets, "red_smiley.png"),
            os.path.join(assets, "red smiley.png"),
        ]
        yellow_candidates = [
            os.path.join(assets, "yellow_smiley.png"),
            os.path.join(assets, "yellow smiley.png"),
        ]
        green_candidates = [
            os.path.join(assets, "green_smiley.png"),
            os.path.join(assets, "green smiley.png"),
        ]

        red = self._open_first_existing(red_candidates)
        yellow = self._open_first_existing(yellow_candidates)
        green = self._open_first_existing(green_candidates)

        target = (80, 80)
        if red: red = red.resize(target)
        if yellow: yellow = yellow.resize(target)
        if green: green = green.resize(target)

        self.smileys["red"] = red
        self.smileys["yellow"] = yellow
        self.smileys["green"] = green

        if not (red and yellow and green):
            print("⚠ Smiley images niet compleet geladen. Check scripts/assets + bestandsnamen.")

    def _status_color_and_key(self, pct):
        if pct is None:
            return (0, 0, 0), None
        try:
            p = int(pct)
        except Exception:
            return (0, 0, 0), None

        if p >= self.GREEN_FROM:
            return (0, 140, 0), "green"
        elif p >= self.YELLOW_FROM:
            return (180, 140, 0), "yellow"
        else:
            return (180, 0, 0), "red"

    # -------- touch helpers --------
    def read_12bit(self, cmd: int) -> int:
        r = self.touch_spi.xfer2([cmd, 0x00, 0x00])
        val = ((r[1] << 8) | r[2]) >> 3
        return val & 0x0FFF

    def get_touch_raw(self, samples=12):
        """
        Median sampling = veel stabieler voor vinger.
        """
        if self.irq.value:  # niet touched
            return None

        xs, ys = [], []
        for _ in range(samples):
            xs.append(self.read_12bit(self.CMD_X))
            ys.append(self.read_12bit(self.CMD_Y))
            time.sleep(0.0008)

        xs.sort(); ys.sort()
        rx = xs[len(xs)//2]
        ry = ys[len(ys)//2]

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

    def hit(self, x, y, r, pad=50):
        x1, y1, x2, y2 = r
        return (x1 - pad) <= x <= (x2 + pad) and (y1 - pad) <= y <= (y2 + pad)

    def _draw_menu(self, status_text=None):
        img = Image.new("RGB", (self.W, self.H), (235, 235, 235))
        d = ImageDraw.Draw(img)

        title = "Smart Plant Menu"
        tw, th = d.textsize(title, font=self.font_title)
        d.text(((self.W - tw)//2, self.TITLE_Y), title, font=self.font_title, fill=(0, 0, 0))

        labels = ["Vochtmeting", "Lichtmeting", "Water geven", "Dashboard"]
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

        title_map = {"moisture": "Vochtmeting", "light": "Lichtmeting", "water": "Water geven"}
        title = title_map.get(screen_id, screen_id)

        tw, th = d.textsize(title, font=self.font_title)
        d.text(((self.W - tw)//2, self.TITLE_Y), title, font=self.font_title, fill=(0, 0, 0))

        self.back_rect = (10, self.H - 50, 120, self.H - 10)
        d.rectangle(self.back_rect, outline=(0, 0, 0), width=2, fill=(245, 245, 245))
        d.text((22, self.H - 42), "< Terug", font=self.font_btn, fill=(0, 0, 0))

        if screen_id == "moisture":
            pct = st.get("moisture_percent", "-")
            raw = st.get("moisture_raw", "-")

            color, key = self._status_color_and_key(pct)

            smiley = self.smileys.get(key) if key else None
            if smiley:
                img.paste(smiley, (self.W - 95, 55), smiley)

            d.text((20, 65), "Waarde:", font=self.font_btn, fill=(0, 0, 0))
            d.text((20, 95), f"{pct} %", font=self.font_big, fill=color)
            d.text((20, 140), f"Raw: {raw}", font=self.font_btn, fill=(0, 0, 0))

            self.refresh_rect = (self.W - 140, self.H - 50, self.W - 10, self.H - 10)
            d.rectangle(self.refresh_rect, outline=(0, 0, 0), width=2, fill=(245, 245, 245))
            d.text((self.W - 132, self.H - 42), "Vernieuw", font=self.font_btn, fill=(0, 0, 0))

        elif screen_id == "light":
            d.text((20, 80), f"Licht: {st.get('light','-')}", font=self.font_btn, fill=(0, 0, 0))
            self.refresh_rect = (self.W - 140, self.H - 50, self.W - 10, self.H - 10)
            d.rectangle(self.refresh_rect, outline=(0, 0, 0), width=2, fill=(245, 245, 245))
            d.text((self.W - 132, self.H - 42), "Vernieuw", font=self.font_btn, fill=(0, 0, 0))

        elif screen_id == "water":
            d.text((20, 70), str(st.get("servo_text", "")), font=self.font_small, fill=(0, 0, 0))

            self.open_rect = (30, 120, 150, 190)
            self.close_rect = (170, 120, 290, 190)
            d.rectangle(self.open_rect, outline=(0, 0, 0), width=2, fill=(210, 255, 210))
            d.rectangle(self.close_rect, outline=(0, 0, 0), width=2, fill=(255, 210, 210))
            d.text((60, 145), "OPEN", font=self.font_btn, fill=(0, 0, 0))
            d.text((198, 145), "DICHT", font=self.font_btn, fill=(0, 0, 0))

        return img

    def _draw_from_state(self, st):
        screen_id = st.get("screen", "menu")

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

    def run(self):
        while self.running:
            st = self.c.get_state_copy()
                        # UI sleep/wake
            awake = st.get("ui_awake", True)

            if not awake:
                # scherm "uit": zwart + geen touch verwerking
                if getattr(self, "_was_asleep", False) is False:
                    img = Image.new("RGB", (self.W, self.H), (0, 0, 0))
                    self.display.image(img)
                    self._was_asleep = True
                time.sleep(0.05)
                continue
            else:
                self._was_asleep = False

            img = self._draw_from_state(st)
            if img is not None:
                self.display.image(img)

            # -------------------
            # TOUCH READ
            # -------------------
            raw = self.get_touch_raw(samples=15)
            if raw and (time.time() - self.last_press) > self.DEBOUNCE:
                self.last_press = time.time()

                rx, ry = raw
                sx, sy = self.touch_to_screen(rx, ry)

                print(f"[TOUCH] screen={st.get('screen')} raw=({rx},{ry}) -> sx={sx} sy={sy}")

                # MENU
                if st.get("screen") == "menu":
                    PAD = 80  # super groot, zodat je makkelijk klikt
                    if self.hit(sx, sy, self.button_rect(0), pad=90):
                        print("[TOUCH] -> moisture")
                        self.c.goto("moisture")
                    elif self.hit(sx, sy, self.button_rect(1), pad=90):
                        print("[TOUCH] -> light")
                        self.c.goto("light")
                    elif self.hit(sx, sy, self.button_rect(2), pad=90):
                        print("[TOUCH] -> water")
                        self.c.goto("water")
                    else:
                        print("[TOUCH] -> no hit")

                # PAGES
                else:
                    if hasattr(self, "back_rect") and self.hit(sx, sy, self.back_rect, pad=60):
                        self.c.goto("menu")

                    if st.get("screen") in ("moisture", "light"):
                        if hasattr(self, "refresh_rect") and self.hit(sx, sy, self.refresh_rect, pad=60):
                            self.c.refresh_current()

                    if st.get("screen") == "water":
                        if hasattr(self, "open_rect") and self.hit(sx, sy, self.open_rect, pad=70):
                            self.c.servo_open()
                        elif hasattr(self, "close_rect") and self.hit(sx, sy, self.close_rect, pad=70):
                            self.c.servo_close()

                # wacht tot loslaten (press->release)
                t0 = time.time()
                while self.get_touch_raw(samples=10) is not None and time.time() - t0 < 0.7:
                    time.sleep(0.01)

            time.sleep(0.01)

    def stop(self):
        self.running = False
