import time
from machine import ADC, PWM, Pin

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

# Analog Moisture Sensor Setup (A0)
moisture_adc = ADC(Pin("A0"))
moisture_adc.atten(ADC.ATTN_11DB)  # Configure attenuation for 0–3.3V voltage range

# --- Configuration Settings ---
LIGHT_DETECTED_STATE = 0

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

STEPS_FOR_90_DEG = 512
stepper_step_index = 0

servo_pwm = PWM(servo_pin, freq=50)
current_servo_angle = 0


def set_servo_angle(angle):
    min_ns = 500_000  # 0.5 ms
    max_ns = 2_500_000  # 2.5 ms
    duty_ns = min_ns + int((angle / 180.0) * (max_ns - min_ns))
    servo_pwm.duty_ns(duty_ns)


def rotate_stepper_90():
    global stepper_step_index
    for _ in range(STEPS_FOR_90_DEG):
        for pin_idx in range(4):
            stepper_pins[pin_idx].value(STEP_SEQUENCE[stepper_step_index][pin_idx])
        stepper_step_index = (stepper_step_index + 1) % len(STEP_SEQUENCE)
        time.sleep_ms(2)

    for pin in stepper_pins:
        pin.value(0)


def rotate_servo_90_relative():
    global current_servo_angle
    current_servo_angle = (current_servo_angle + 90) % 270
    if current_servo_angle > 180:
        current_servo_angle = 0

    set_servo_angle(current_servo_angle)


# --- Initialization ---
set_servo_angle(current_servo_angle)
button_last_state = 0
last_sensor_read_time = time.ticks_ms()

print("[DEBUG] MicroPython control loop running...")

# --- Main Program Loop ---
while True:
    current_time = time.ticks_ms()

    # 1. Moisture Sensor Monitoring (Non-blocking check every 1000 ms)
    if time.ticks_diff(current_time, last_sensor_read_time) >= 1000:
        raw_val = moisture_adc.read_u16()
        voltage = (raw_val / 65535.0) * 3.3
        print(f"[DEBUG] Moisture Sensor Voltage: {voltage:.2f} V")
        last_sensor_read_time = current_time

    # 2. Light Sensor & LED Control
    if light_sensor.value() == LIGHT_DETECTED_STATE:
        led.value(1)
    else:
        led.value(0)

    # 3. Button State Monitoring (Rising-edge detection)
    button_state = button.value()
    if button_state == 1 and button_last_state == 0:
        print("[DEBUG] Button press detected on pin D7! Starting 90° rotations...")

        rotate_stepper_90()
        rotate_servo_90_relative()

        print(
            f"[DEBUG] Movement complete. Current Servo Angle: {current_servo_angle}°"
        )
        time.sleep_ms(250)  # Hardware debounce delay

    button_last_state = button_state
    time.sleep_ms(10)
