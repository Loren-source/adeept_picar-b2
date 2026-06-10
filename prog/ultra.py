from gpiozero import DistanceSensor
from time import sleep

Tr = 23
Ec = 24
#sensor = DistanceSensor(echo=Ec, trigger=Tr, max_distance=2) # Maximum detection distance 2m.

# Get the distance of ultrasonic detection.
#def checkdist():
    #return (sensor.distance) *100 # Unit: cm

#if __name__ == "__main__":
 #   while True:
  #      distance = checkdist()
   #     print("%.2f cm" %distance)
    #    sleep(0.05)

class Ultrasonic:
    def __init__(self, trigger_pin=Tr, echo_pin=Ec, max_distance=2):
        self.sensor = DistanceSensor(echo=echo_pin, trigger=trigger_pin, max_distance=max_distance)

    def get_distance(self):
        return self.sensor.distance * 10  # Return distance in mm

if __name__ == "__main__":
    ultrasonic = Ultrasonic()
    try:
        while True:
            distance = ultrasonic.get_distance()
            print(f"Distance: {distance:.2f} mm")
            sleep(0.05)
    except KeyboardInterrupt:
        pass