#Blinking Program

#Import Modules
import machine # Module with all microcontroller stuff
import time # Module with time methods
# Make led object
# Green led is GPIO Pin 0
led = machine.Pin(0,machine.Pin.OUT) 
#infinite loop
while True: 
  led.value(1) # Turn on LED
  time.sleep(0.5) # 0.5s Delay
  led.value(0) # Turn off LED
  time.sleep(0.5) # 0.5s Delay
  