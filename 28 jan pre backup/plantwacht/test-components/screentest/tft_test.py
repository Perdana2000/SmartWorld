import time
import board
import busio
import digitalio
from adafruit_rgb_display import ili9341

print("starting...")

# SPI bus
spi = busio.SPI(board.SCK, MOSI=board.MOSI, MISO=board.MISO)

# JOUW WIRING:
# CS  -> CE0
# D/C -> GPIO06
# RST -> GPIO05
cs = digitalio.DigitalInOut(board.CE0)
dc = digitalio.DigitalInOut(board.D6)
rst = digitalio.DigitalInOut(board.D5)

print("init display...")
display = ili9341.ILI9341(
    spi,
    cs=cs,
    dc=dc,
    rst=rst,
    rotation=0,
    baudrate=1000000  # 1 MHz voor stabiel testen
)

colors = [
    ("red", 0xF800),
    ("green", 0x07E0),
    ("blue", 0x001F),
    ("white", 0xFFFF),
    ("black", 0x0000),
]

print("loop...")
while True:
    for name, c in colors:
        print("fill:", name)
        display.fill(c)
        time.sleep(1)
