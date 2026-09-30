import time
from machine import ADC, PWM, Pin

# --- Pin Setup (Arduino Nano ESP32) ---
# Stepper driver pins (ULN2003 IN1-IN4 -> D2-D5)
pin_in1 = Pin("D2", Pin.OUT)
pin_in2 = Pin("D3", Pin.OUT)
pin_in3 = Pin("D4", Pin.OUT)
pin_in4 = Pin("D5", Pin.OUT)
stepper_pins = [pin_in1, pin_in2, pin_in3, pin_in4]

# Sensors, Switch, Servo, and LED
light_sensor = Pin("D6", Pin.IN)
switch = Pin("D7", Pin.IN, Pin.PULL_DOWN)  # Pin D7 goes HIGH (1) when switch is OPEN
servo_pin = Pin("D8", Pin.OUT)
led = Pin("D9", Pin.OUT)

# Analog Moisture Sensor Setup (Pin A0)
moisture_adc = ADC(Pin("A0"))
moisture_adc.atten(ADC.ATTN_11DB)  # 0–3.3V range

# --- Configuration Settings ---
LIGHT_DETECTED_STATE = 0  # Standard modules output LOW (0) when light is detected
MOISTURE_VOLTAGE_THRESHOLD = 0.15  # Volts
CHECK_INTERVAL_MS = 30_000  # 30 seconds
STEPS_FOR_MOVEMENT = 8700

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

stepper_step_index = 0
servo_pwm = PWM(servo_pin, freq=50)

# --- State Tracking Variables ---
# System starts with the roof in the OPEN state
motors_are_open = True
clear_condition_start_time = None
last_sensor_read_time = time.ticks_ms()


def set_servo_angle(angle):
    """Sets servo position (0° for CLOSED, 90° for OPEN)."""
    min_ns = 500_000  # 0°
    max_ns = 2_500_000  # 180°
    duty_ns = min_ns + int((angle / 180.0) * (max_ns - min_ns))
    servo_pwm.duty_ns(duty_ns)


def rotate_stepper_with_led_flash(steps, forward=True):
    """Rotates stepper motor while toggling the LED every 200 ms."""
    global stepper_step_index
    step_dir = 1 if forward else -1
    last_led_toggle = time.ticks_ms()

    for _ in range(steps):
        stepper_step_index = (stepper_step_index + step_dir) % len(STEP_SEQUENCE)
        for pin_idx in range(4):
            stepper_pins[pin_idx].value(
                STEP_SEQUENCE[stepper_step_index][pin_idx]
            )

        # Toggle LED every 200 ms while moving
        now = time.ticks_ms()
        if time.ticks_diff(now, last_led_toggle) >= 200:
            led.value(not led.value())
            last_led_toggle = now

        time.sleep_ms(2)

    # Turn off stepper coils to prevent heat build-up
    for pin in stepper_pins:
        pin.value(0)


def set_motor_position(open_position):
    """Moves both motors to OPEN or CLOSED position with LED movement flashing."""
    global motors_are_open

    if open_position and not motors_are_open:
        print("[DEBUG] Opening Roof: 8700 steps forward, Servo to 90°...")
        rotate_stepper_with_led_flash(STEPS_FOR_MOVEMENT, forward=True)
        set_servo_angle(90)
        motors_are_open = True
        led.value(1)  # Solid ON when open

    elif not open_position and motors_are_open:
        print("[DEBUG] Closing Roof: 8700 steps reverse, Servo to 0°...")
        rotate_stepper_with_led_flash(STEPS_FOR_MOVEMENT, forward=False)
        set_servo_angle(0)
        motors_are_open = False
        led.value(0)  # Solid OFF when closed


# --- Initial Hardware State (Starts OPEN) ---
set_servo_angle(90)
led.value(1)

print("[DEBUG] Automated Roof System Initialized (Starting OPEN).")

# --- Main Program Loop ---
while True:
    current_time = time.ticks_ms()

    # 1. Analog Moisture Reading & Debug Console Output (Every 1 Second)
    raw_val = moisture_adc.read_u16()
    voltage = (raw_val / 65535.0) * 3.3

    if time.ticks_diff(current_time, last_sensor_read_time) >= 1000:
        is_switch_open = switch.value() == 1
        has_light = light_sensor.value() == LIGHT_DETECTED_STATE
        print(
            f"[DEBUG] Moisture: {voltage:.2f}V | Light: {'YES' if has_light else 'NO'} | "
            f"System: {'ON (Switch Open)' if is_switch_open else 'OFF (Switch Closed)'} | "
            f"Roof State: {'OPEN' if motors_are_open else 'CLOSED'}"
        )
        last_sensor_read_time = current_time

    # 2. System Logic Execution
    is_switch_open = switch.value() == 1  # HIGH (1) when switch is OPEN (System ON)

    if is_switch_open:
        has_light = light_sensor.value() == LIGHT_DETECTED_STATE
        has_moisture = voltage > MOISTURE_VOLTAGE_THRESHOLD

        # Close immediately if it is dark OR if moisture is detected (>0.15V)
        if has_moisture or not has_light:
            clear_condition_start_time = None  # Reset timer
            set_motor_position(open_position=False)

        # If conditions are clear (Light present AND No Moisture), wait 30 seconds before opening
        else:
            if clear_condition_start_time is None:
                clear_condition_start_time = current_time
                print(
                    "[DEBUG] Light detected & Dry condition verified. Timing 30s before opening..."
                )

            # Check if clear conditions have persisted continuously for 30 seconds
            if (
                time.ticks_diff(current_time, clear_condition_start_time)
                >= CHECK_INTERVAL_MS
            ):
                set_motor_position(open_position=True)

    else:
        # Switch is CLOSED -> System disabled, roof stays in whatever state it was last in
        clear_condition_start_time = None

    time.sleep_ms(10)
