import time
import RPi.GPIO as GPIO

# ====== GPIO pins (BCM nummers) ======
LED_GREEN = 16
LED_YELLOW = 20
LED_RED = 21

# ====== Drempels (in %) ======
# <= 30%  -> rood (droog)
# <= 60%  -> geel (matig)
# >  60%  -> groen (goed)
RED_THR = 30
YELLOW_THR = 60


def setup_gpio():
    """Zet GPIO klaar."""
    GPIO.setwarnings(False)      # haalt 'channel already in use' waarschuwingen weg
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(LED_GREEN, GPIO.OUT)
    GPIO.setup(LED_YELLOW, GPIO.OUT)
    GPIO.setup(LED_RED, GPIO.OUT)

    all_off()


def all_off():
    """Zet alle lampjes uit."""
    GPIO.output(LED_GREEN, GPIO.LOW)
    GPIO.output(LED_YELLOW, GPIO.LOW)
    GPIO.output(LED_RED, GPIO.LOW)


def set_led(color):
    """
    Zet precies 1 lampje aan.
    color = "green" / "yellow" / "red"
    """
    all_off()

    if color == "green":
        GPIO.output(LED_GREEN, GPIO.HIGH)
    elif color == "yellow":
        GPIO.output(LED_YELLOW, GPIO.HIGH)
    elif color == "red":
        GPIO.output(LED_RED, GPIO.HIGH)


def moisture_to_color(moisture_percent):
    """
    Bepaalt welke kleur hoort bij de vochtwaarde (0-100%).
    """
    if moisture_percent <= RED_THR:
        return "red"
    elif moisture_percent <= YELLOW_THR:
        return "yellow"
    else:
        return "green"


def read_moisture_dummy():
    """
    Dummy waarden (0-100%).
    Later vervang je dit door echte sensor code.
    """
    values = [10, 25, 40, 55, 70, 85, 30, 15]
    for v in values:
        yield v


# ====== LATER: echte sensor read ======
# def read_sensor_percent():
#     # return 0..100 (percent)
#     # bv: adc_value = ...
#     # convert naar percent
#     # return percent
#     pass


def main():
    setup_gpio()

    try:
        for moisture in read_moisture_dummy():
            color = moisture_to_color(moisture)
            set_led(color)

            print(f"Vocht={moisture}% -> {color.upper()}")
            time.sleep(1.5)

    finally:
        # netjes opruimen als je stopt (ook bij error)
        all_off()
        GPIO.cleanup()


if __name__ == "__main__":
    main()
