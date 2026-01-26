import time
import spidev
from gpiozero import DigitalInputDevice

import board
import busio
import digitalio
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import ili9341

# =========================
# DISPLAY (TFT) - JOUW PINS
# =========================
# CS  -> CE0
# D/C -> GPIO06
# RST -> GPIO05
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

tft_cs  = digitalio.DigitalInOut(board.CE0)
tft_dc  = digitalio.DigitalInOut(board.D6)
tft_rst = digitalio.DigitalInOut(board.D5)

# rotation moet in graden: 0/90/180/270
ROTATION = 90  # landscape
display = ili9341.ILI9341(
    spi,
    cs=tft_cs,
    dc=tft_dc,
    rst=tft_rst,
    rotation=ROTATION,
    baudrate=1000000
)

# Bepaal W/H op basis van rotation
if ROTATION in (90, 270):
    W, H = 320, 240
else:
    W, H = 240, 320

# =========================
# TOUCH (XPT2046) via spidev
# =========================
touch_spi = spidev.SpiDev()
touch_spi.open(0, 1)               # SPI0, CE1
touch_spi.max_speed_hz = 2000000
touch_spi.mode = 0

irq = DigitalInputDevice(22, pull_up=True)  # T_IRQ op GPIO22 (active-low)

CMD_X = 0xD0
CMD_Y = 0x90

def read_12bit(cmd: int) -> int:
    r = touch_spi.xfer2([cmd, 0x00, 0x00])
    val = ((r[1] << 8) | r[2]) >> 3
    return val & 0x0FFF

def get_touch_raw(samples=7):
    if irq.value:  # IRQ high = niet touched
        return None

    xs, ys = [], []
    for _ in range(samples):
        xs.append(read_12bit(CMD_X))
        ys.append(read_12bit(CMD_Y))
        time.sleep(0.001)

    xs.sort(); ys.sort()
    xs = xs[1:-1]
    ys = ys[1:-1]

    rx = sum(xs) // len(xs)
    ry = sum(ys) // len(ys)

    if rx in (0, 4095) or ry in (0, 4095):
        return None
    return rx, ry

# =========================
# TOUCH CALIBRATIE (start)
# =========================
TOUCH_X_MIN = 200
TOUCH_X_MAX = 3900
TOUCH_Y_MIN = 200
TOUCH_Y_MAX = 3900

# Vaak nodig bij landscape + jouw module:
TOUCH_SWAP_XY = True
TOUCH_INVERT_X = False
TOUCH_INVERT_Y = True

def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v

def map_range(v, in_min, in_max, out_min, out_max):
    v = clamp(v, in_min, in_max)
    return int((v - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

def touch_to_screen(rx, ry):
    if TOUCH_SWAP_XY:
        rx, ry = ry, rx

    x = map_range(rx, TOUCH_X_MIN, TOUCH_X_MAX, 0, W - 1)
    y = map_range(ry, TOUCH_Y_MIN, TOUCH_Y_MAX, 0, H - 1)

    if TOUCH_INVERT_X:
        x = (W - 1) - x
    if TOUCH_INVERT_Y:
        y = (H - 1) - y

    return x, y

# =========================
# FONTS (groter)
# =========================
def load_font(size):
    try:
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except:
        return ImageFont.load_default()

font_title = load_font(26)
font_btn   = load_font(20)
font_small = load_font(14)

# =========================
# UI (smaller buttons)
# =========================
MARGIN_X = 70
BTN_W = W - 2 * MARGIN_X
BTN_H = 52
GAP = 14
TITLE_Y = 8
TOP_Y = 55

buttons = [
    {"id": "moisture", "label": "Vochtmeting"},
    {"id": "light",    "label": "Lichtmeting"},
    {"id": "water",    "label": "Water geven"},
]

def button_rect(i):
    x1 = MARGIN_X
    y1 = TOP_Y + i * (BTN_H + GAP)
    x2 = x1 + BTN_W
    y2 = y1 + BTN_H
    return (x1, y1, x2, y2)

def point_in_rect(x, y, r):
    x1, y1, x2, y2 = r
    return x1 <= x <= x2 and y1 <= y <= y2

def do_action(action_id):
    print("ACTION:", action_id)

def draw_menu(selected_index=None, status_text=""):
    img = Image.new("RGB", (W, H), (235, 235, 235))
    d = ImageDraw.Draw(img)

    title = "Smart Plant Menu"
    tw, th = d.textsize(title, font=font_title)
    d.text(((W - tw)//2, TITLE_Y), title, font=font_title, fill=(0, 0, 0))

    for i, b in enumerate(buttons):
        r = button_rect(i)
        if selected_index == i:
            d.rectangle(r, outline=(0, 0, 0), width=3, fill=(210, 210, 210))
        else:
            d.rectangle(r, outline=(0, 0, 0), width=2, fill=(245, 245, 245))

        label = b["label"]
        lw, lh = d.textsize(label, font=font_btn)
        x1, y1, x2, y2 = r
        d.text(((x1 + x2 - lw)//2, (y1 + y2 - lh)//2),
               label, font=font_btn, fill=(0, 0, 0))

    if status_text:
        d.text((10, H - 18), status_text, font=font_small, fill=(20, 20, 20))

    return img

# =========================
# MAIN LOOP
# =========================
selected = None
status = "tik een knop"
display.image(draw_menu(selected, status))

last_press = 0
DEBOUNCE = 0.25

while True:
    raw = get_touch_raw()
    if raw and (time.time() - last_press) > DEBOUNCE:
        last_press = time.time()
        rx, ry = raw
        sx, sy = touch_to_screen(rx, ry)
        print(f"RAW: x={rx} y={ry}  -> MAP: x={sx} y={sy}")

        pressed = None
        for i in range(len(buttons)):
            if point_in_rect(sx, sy, button_rect(i)):
                pressed = i
                break

        if pressed is not None:
            selected = pressed
            status = f"gekozen: {buttons[pressed]['label']}"
            display.image(draw_menu(selected, status))
            do_action(buttons[pressed]["id"])
        else:
            selected = None
            status = f"tap: {sx},{sy}"
            display.image(draw_menu(selected, status))

    time.sleep(0.02)
