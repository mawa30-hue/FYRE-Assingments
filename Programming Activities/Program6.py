from machine import Pin, PWM
import time

#Team member names: Justin Ficca, Max Weiner,J.B. Volkert
#Purpose of the code: To move the servo from 180 degrees to 0 degrees
#Date code was started: 9/16/2026
#Date of last update: 9/16/2026
#Explination of AI use: ChatGPT was used to generate the whole code

# Arduino Nano ESP32 pin mapping
BUTTON_PIN = 8      # D5 = GPIO8
SERVO_PIN = 38      # D11 = GPIO38

# -------------------------------
# Button setup
# -------------------------------
# Button supplies 3.3V when pressed
# Not pressed = 0
# Pressed = 1
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_DOWN)

# -------------------------------
# Servo setup
# -------------------------------
servo = PWM(Pin(SERVO_PIN))

# Standard hobby servo frequency
servo.freq(50)

# Starting position
servo_position = 0

# Used to detect a new button press
last_button_state = button.value()


def move_servo(angle):
    """
    Move servo to approximately 0-180 degrees.

    Typical servo pulse widths:
    0 degrees   = about 500 us
    180 degrees = about 2500 us
    """

    min_us = 500
    max_us = 2500

    pulse_us = min_us + (angle / 180) * (max_us - min_us)

    # Convert pulse width to duty_u16
    # 50 Hz = 20,000 us period
    duty = int((pulse_us / 20000) * 65535)

    servo.duty_u16(duty)

    print("Servo commanded to:", angle, "degrees")
    print("PWM duty:", duty)


# Start servo at 0 degrees
move_servo(0)

print("===================================")
print("SERVO TOGGLE PROGRAM STARTED")
print("D5  = Button")
print("D11 = Servo PWM")
print("===================================")


while True:

    current_button_state = button.value()

    # Detect button going from LOW to HIGH
    if current_button_state == 1 and last_button_state == 0:

        print("")
        print(">>> BUTTON PRESSED")

        # Debounce
        time.sleep_ms(40)

        if button.value() == 1:

            # Toggle servo position
            if servo_position == 0:
                servo_position = 180
            else:
                servo_position = 0

            move_servo(servo_position)

            # Wait for the button to be released
            # This prevents one long press from counting multiple times
            while button.value() == 1:
                time.sleep_ms(10)

            print(">>> BUTTON RELEASED")
            print("Current servo position:", servo_position)

    last_button_state = button.value()

    time.sleep_ms(5)