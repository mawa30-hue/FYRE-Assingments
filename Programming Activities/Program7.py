from machine import Pin, ADC
import time

#Team member names: Justin Ficca, Max Weiner,J.B. Volkert
#Purpose of the code: To read a moisture sensor
#Date code was started: 9/16/2026
#Date of last update: 9/16/2026
#Explination of AI use: ChatGPT was used to generate the whole code

# Arduino Nano ESP32
# A0 = GPIO1
ADC_PIN = 1

# Set up ADC
adc = ADC(Pin(ADC_PIN))
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_12BIT)

# CSV filename
filename = "voltage_log.csv"

# Number of samples
NUM_SAMPLES = 10

# Create CSV file
with open(filename, "w") as file:
    file.write("Sample,Voltage\n")

print("====================================")
print("ADC VOLTAGE LOGGER STARTED")
print("Recording 10 samples")
print("====================================")

for sample in range(1, NUM_SAMPLES + 1):

    # Read ADC value
    adc_value = adc.read()

    # Convert ADC value to voltage
    voltage = (adc_value / 4095) * 3.3

    # Display in REPL
    print(
        "Sample", sample,
        "| Voltage = {:.3f} V".format(voltage)
    )

    # Save to CSV
    with open(filename, "a") as file:
        file.write(
            "{},{:.3f} V\n".format(
                sample,
                voltage
            )
        )

    # Wait 1 second before next sample
    time.sleep(1)

print("")
print("====================================")
print("DATA COLLECTION COMPLETE")
print("10 samples recorded.")
print("Saved to:", filename)
print("====================================")