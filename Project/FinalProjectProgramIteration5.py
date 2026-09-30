import os
import time
from machine import ADC, Pin

# ==========================================
# PIN CONFIGURATION (Arduino Nano ESP32)
# ==========================================
IN1 = Pin("D2", Pin.OUT)
IN2 = Pin("D3", Pin.OUT)
IN3 = Pin("D4", Pin.OUT)
IN4 = Pin("D5", Pin.OUT)
motor_pins = [IN1, IN2, IN3, IN4]

LIGHT_PIN = Pin("D6", Pin.IN)  # Digital light sensor (1 = Bright, 0 = Dark)
SWITCH_PIN = Pin(
    "D7", Pin.IN
)  # Master enable switch (1/HIGH when switch open)
LED_PIN = Pin("D9", Pin.OUT)  # Status LED

# Analog moisture sensor on A0 (0-3.3V ADC range)
moisture_adc = ADC(Pin("A0", Pin.IN))
moisture_adc.width(ADC.WIDTH_12BIT)

# ==========================================
# PARAMETERS & CONSTANTS
# ==========================================
STATE_FILE = "roof_state.txt"
TOTAL_STEPS = 8700
STEP_DELAY_MS = 2  # Default step delay
MOISTURE_THRESHOLD_V = 0.5  # Voltage threshold for rain detection
DRY_HOLD_TIME_SEC = 5  # Continuous dry & bright seconds required to open
DEBUG_INTERVAL_SEC = 1  # Console debug log frequency

# 8-step half-step sequence for ULN2003 / 28BYJ-48
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


# ==========================================
# NON-VOLATILE FLASH STATE PERSISTENCE
# ==========================================
def load_roof_state():
  """Loads state from Flash memory on boot. Defaults to CLOSED if no saved state exists."""
  try:
    with open(STATE_FILE, "r") as f:
      saved_state = f.read().strip()
      print(f"[BOOT] Loaded state from Flash memory: Roof is {saved_state}")
      return saved_state == "OPEN"
  except OSError:
    # Initial startup default: Roof starts CLOSED
    print("[BOOT] No state file found. Initializing roof state to CLOSED.")
    save_roof_state(False)
    return False


def save_roof_state(is_open):
  """Saves current roof state to internal Flash filesystem."""
  try:
    with open(STATE_FILE, "w") as f:
      f.write("OPEN" if is_open else "CLOSED")
    print(
        f"[FLASH] Saved state to memory: Roof is {'OPEN' if is_open else 'CLOSED'}"
    )
  except OSError as e:
    print(f"[ERROR] Failed to save state to Flash: {e}")


# ==========================================
# HELPER FUNCTIONS
# ==========================================
def disable_motor():
  """De-energizes motor coils to prevent overheating and power drain when stationary."""
  for pin in motor_pins:
    pin.value(0)


def read_moisture_voltage():
  """Reads ADC pin A0 raw value (0-4095) and calculates actual voltage (0-3.3V)."""
  raw_val = moisture_adc.read_uv()
  voltage = (raw_val / 1000000.0)
  return raw_val, voltage


def move_roof(target_open):
  """Executes uninterrupted 8,700-step motion sequence.

  Runs synchronously from step 0 to 8700 without reading sensors mid-run,
  guaranteeing the motor never changes direction mid-sequence.
  """
  global roof_is_open

  # Guard check: prevent movement if already in the target state
  if roof_is_open == target_open:
    return

  # Inverted stepper direction logic (target_open = -1, target_closed = 1)
  direction = -1 if target_open else 1
  action_str = "OPENING" if target_open else "CLOSING"
  print(f"\n[MOTOR] {action_str} roof ({TOTAL_STEPS} steps)...")

  # Atomic step execution loop (cannot be interrupted mid-travel)
  for step in range(TOTAL_STEPS):
    seq_idx = (step * direction) % len(STEP_SEQUENCE)
    pattern = STEP_SEQUENCE[seq_idx]
    for i, val in enumerate(pattern):
      motor_pins[i].value(val)

    # Flash LED every 50 steps (~100ms interval) while in motion
    if step % 50 == 0:
      LED_PIN.value(not LED_PIN.value())

    time.sleep_ms(STEP_DELAY_MS)

  # De-energize coils upon completion
  disable_motor()

  # Update state variables & write state immediately to Flash memory
  roof_is_open = target_open
  save_roof_state(roof_is_open)

  # Set LED status: ON when OPEN, OFF when CLOSED
  LED_PIN.value(1 if roof_is_open else 0)
  print(
      f"[MOTOR] Motion complete. Roof is now {'OPEN' if roof_is_open else 'CLOSED'}.\n"
  )


# ==========================================
# INITIALIZATION
# ==========================================
disable_motor()
roof_is_open = load_roof_state()  # Defaults to CLOSED (False) on first boot
LED_PIN.value(
    1 if roof_is_open else 0
)  # LED starts OFF when roof is initial CLOSED state

dry_start_time = None
last_debug_time = 0

print("--- Automated Roof Control System Active ---")

# ==========================================
# MAIN CONTROL LOOP
# ==========================================
while True:
  current_time = time.time()

  # 1. Master System Enable Check (D7 HIGH when switch open = Enabled)
  system_enabled = SWITCH_PIN.value() == 1

  # 2. Read Sensors
  raw_adc, voltage = read_moisture_voltage()
  is_wet = voltage < MOISTURE_THRESHOLD_V
  has_light = LIGHT_PIN.value() == 0  # 1 = Bright, 0 = Dark

  # 3. Debug Output
  if current_time - last_debug_time >= DEBUG_INTERVAL_SEC:
    sys_status = "ENABLED" if system_enabled else "DISABLED"
    light_status = "BRIGHT" if has_light else "DARK"
    wet_status = "WET" if is_wet else "DRY"
    print(
        f"[DEBUG] System: {sys_status} | Roof:"
        f" {'OPEN' if roof_is_open else 'CLOSED'} | Moisture Raw: {raw_adc:4d}"
        f" ({voltage:.3f}V - {wet_status}) | Light: {light_status}"
    )
    last_debug_time = current_time

  # 4. Handle System Disabled State
  if not system_enabled:
    dry_start_time = None
    time.sleep_ms(200)
    continue

  # 5. Automated Decision Tree
  if is_wet:
    # Trigger 1: Moisture Detected -> Close immediately
    dry_start_time = None
    if roof_is_open:
      print("[TRIGGER] Moisture threshold exceeded! Closing roof.")
      move_roof(target_open=False)

  elif not has_light:
    # Trigger 2: Darkness Detected -> Close immediately
    dry_start_time = None
    if roof_is_open:
      print("[TRIGGER] Darkness detected! Closing roof.")
      move_roof(target_open=False)

  else:
    # Trigger 3: Conditions are DRY and BRIGHT
    if dry_start_time is None:
      dry_start_time = current_time

    elapsed_dry_time = current_time - dry_start_time

    # Re-open roof if dry and bright conditions persist for 30 seconds
    if elapsed_dry_time >= DRY_HOLD_TIME_SEC and not roof_is_open:
      print(
          f"[TRIGGER] Dry & Bright sustained for {DRY_HOLD_TIME_SEC}s."
          " Re-opening roof."
      )
      move_roof(target_open=True)

  time.sleep_ms(100)