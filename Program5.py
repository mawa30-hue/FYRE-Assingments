from machine import Pin
import time

# -------------------------------------------------
# Arduino Nano ESP32 pin mappings
# D2 = GPIO5
# D3 = GPIO6
# D4 = GPIO7
# D5 = GPIO8
# -------------------------------------------------

ARM_LED_PIN = 5       # Arduino D2
ALARM_LED_PIN = 6     # Arduino D3
PHOTO_PIN = 7         # Arduino D4
SWITCH_PIN = 8        # Arduino D5


# -------------------------------------------------
# PIN SETUP
# -------------------------------------------------

arm_led = Pin(ARM_LED_PIN, Pin.OUT)
alarm_led = Pin(ALARM_LED_PIN, Pin.OUT)

# Button sends 3.3V into D5 when pressed
# Not pressed = 0
# Pressed = 1
switch = Pin(SWITCH_PIN, Pin.IN, Pin.PULL_DOWN)

# Photosensor digital input
photosensor = Pin(PHOTO_PIN, Pin.IN)


# -------------------------------------------------
# INITIAL STATE
# -------------------------------------------------

armed = False

arm_led.value(0)
alarm_led.value(0)

last_switch_state = switch.value()

alarm_led_state = 0

last_flash_time = time.ticks_ms()
last_debug_time = time.ticks_ms()


print("")
print("==========================================")
print("SYSTEM STARTED")
print("==========================================")
print("D5 = ARM/DISARM BUTTON")
print("D4 = PHOTOSENSOR")
print("D2 = ARMED LED")
print("D3 = WARNING LED")
print("")
print("BUTTON:")
print("0 = NOT PRESSED")
print("1 = PRESSED")
print("==========================================")
print("")


# -------------------------------------------------
# MAIN LOOP
# -------------------------------------------------

while True:

    current_switch_state = switch.value()
    photo_state = photosensor.value()


    # -------------------------------------------------
    # DETECT BUTTON PRESS
    # Rising edge: 0 -> 1
    # -------------------------------------------------

    if current_switch_state == 1 and last_switch_state == 0:

        print("")
        print(">>> D5 BUTTON PRESS DETECTED")

        # Debounce
        time.sleep_ms(40)

        # Check that button is still pressed
        if switch.value() == 1:

            armed = not armed

            if armed:
                print(">>> SYSTEM IS NOW ARMED")
            else:
                print(">>> SYSTEM IS NOW UNARMED")

            # Wait for release
            while switch.value() == 1:
                time.sleep_ms(10)

            print(">>> BUTTON RELEASED")
            print("")

    last_switch_state = switch.value()


    # -------------------------------------------------
    # SYSTEM UNARMED
    # -------------------------------------------------

    if armed == False:

        # D2 OFF
        arm_led.value(0)

        # D3 OFF
        alarm_led.value(0)

        alarm_led_state = 0

        last_flash_time = time.ticks_ms()


    # -------------------------------------------------
    # SYSTEM ARMED
    # -------------------------------------------------

    else:

        # D2 stays ON while armed
        arm_led.value(1)

        photo_state = photosensor.value()


        # -------------------------------------------------
        # PHOTOSENSOR DETECTS POWER
        # -------------------------------------------------

        if photo_state == 1:

            # Warning LED OFF
            alarm_led.value(0)

            alarm_led_state = 0

            last_flash_time = time.ticks_ms()


        # -------------------------------------------------
        # PHOTOSENSOR DOES NOT DETECT POWER
        # -------------------------------------------------

        else:

            current_time = time.ticks_ms()

            # Toggle D3 every 0.25 seconds
            if time.ticks_diff(current_time,
                               last_flash_time) >= 250:

                alarm_led_state = not alarm_led_state

                alarm_led.value(alarm_led_state)

                last_flash_time = current_time


    # -------------------------------------------------
    # DEBUG OUTPUT
    # -------------------------------------------------

    current_time = time.ticks_ms()

    if time.ticks_diff(current_time,
                       last_debug_time) >= 250:

        print(
            "D5 BUTTON =", switch.value(),
            "| ARMED =", armed,
            "| D4 PHOTO =", photosensor.value(),
            "| D2 ARM LED =", arm_led.value(),
            "| D3 WARNING LED =", alarm_led.value()
        )

        last_debug_time = current_time


    time.sleep_ms(5)