import time
from machine import PWM, Pin

# --- Pin Setup (Arduino Nano ESP32) ---
# Stepper driver pins (ULN2003 IN1-IN4 -> D2-D5)
pin_in1 = Pin("D2", Pin.OUT)
pin_in2 = Pin("D3", Pin.OUT)
pin_in3 = Pin("D4", Pin.OUT)
pin_in4 = Pin("D5", Pin.OUT)
stepper_pins = [pin_in1, pin_in2, pin_in3, pin_in4]

# Sensors, Button, LED, and Servo
light_sensor = Pin("D6", Pin.IN)
button = Pin("D7", Pin.IN, Pin.PULL_DOWN)  # Enables internal pull-down
servo_pin = Pin("D8", Pin.OUT)
led = Pin("D9", Pin.OUT)

# --- Configuration Settings ---
# Standard digital light modules output 0 (LOW) when light threshold is reached.
# Change to 1 if your sensor outputs HIGH when triggered.
LIGHT_DETECTED_STATE = 0

# 28BYJ-48 Half-Stepping Sequence (Smoother movement & higher torque)
STEP_SEQUENCE = [
    [1, 0, 0, 0],
    [1, 1, 0, 0],
    [0, 1, 0, 0],
    [0, 1, 1, 0],
    [0, 0, 1, 0],
    [0, 0, 1, 1],
    [0, 0, 0, 1],
    [1, 0, 0, 1],
]

# Standard 28BYJ-48 (~2048 steps per 360° rev in half-step mode)
STEPS_FOR_90_DEG = 512
stepper_step_index = 0

# --- Servo Motor Control Setup ---
servo_pwm = PWM(servo_pin, freq=50)  # 50Hz standard RC servo frequency
current_servo_angle = 0  # Tracks relative position


def set_servo_angle(angle):
    """Converts 0-180 degree angle to nanosecond pulse width for 50Hz PWM."""
    min_ns = 500_000  # 0.5 ms (0 degrees)
    max_ns = 2_500_000  # 2.5 ms (180 degrees)
    duty_ns = min_ns + int((angle / 180.0) * (max_ns - min_ns))
    servo_pwm.duty_ns(duty_ns)


def rotate_stepper_90():
    global stepper_step_index
    for _ in range(STEPS_FOR_90_DEG):
        for pin_idx in range(4):
            stepper_pins[pin_idx].value(STEP_SEQUENCE[stepper_step_index][pin_idx])
        stepper_step_index = (stepper_step_index + 1) % len(STEP_SEQUENCE)
        time.sleep_ms(2)  # Step delay (adjust to change motor speed)

    # De-energize coils after rotation to prevent overheating and save power
    for pin in stepper_pins:
        pin.value(0)


def rotate_servo_90_relative():
    global current_servo_angle
    # Advance angle by 90 degrees; wraps back to 0° if exceeding standard 180° limit
    current_servo_angle = (current_servo_angle + 90) % 270
    if current_servo_angle > 180:
        current_servo_angle = 0

    set_servo_angle(current_servo_angle)


# --- Initialization ---
set_servo_angle(current_servo_angle)
button_last_state = 0

print("[DEBUG] MicroPython control loop running...")

# --- Main Program Loop ---
while True:
    # 1. Light Sensor & LED Control
    if light_sensor.value() == LIGHT_DETECTED_STATE:
        led.value(1)
    else:
        led.value(0)

    # 2. Button State Monitoring (Rising-edge detection)
    button_state = button.value()
    if button_state == 1 and button_last_state == 0:
        print("[DEBUG] Button press detected on pin D7! Starting 90° rotations...")

        # Move both motors
        rotate_stepper_90()
        rotate_servo_90_relative()

        print(
            f"[DEBUG] Movement complete. Current Servo Angle: {current_servo_angle}°"
        )
        time.sleep_ms(250)  # Hardware debounce delay

    button_last_state = button_state
    time.sleep_ms(10)