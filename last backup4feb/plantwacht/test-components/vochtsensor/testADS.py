import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

def main():
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)

    # Standaard goed om te beginnen
    ads.gain = 1

    # Lees alle 4 kanalen zodat je meteen ziet waar je sensor zit
    ch0 = AnalogIn(ads, 0)
    ch1 = AnalogIn(ads, 1)
    ch2 = AnalogIn(ads, 2)
    ch3 = AnalogIn(ads, 3)


    print("ADS1115 live.")
    while True:
        print(
            f"A0: raw={ch0.value:5d}  V={ch0.voltage:.3f} | "
            f"A1: raw={ch1.value:5d}  V={ch1.voltage:.3f} | "
            f"A2: raw={ch2.value:5d}  V={ch2.voltage:.3f} | "
            f"A3: raw={ch3.value:5d}  V={ch3.voltage:.3f}"
        )
        time.sleep(0.5)

if __name__ == "__main__":
    main()

