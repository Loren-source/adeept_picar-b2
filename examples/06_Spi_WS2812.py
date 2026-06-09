import time
from rpi_ws281x import *

class LED:
        def __init__(self):
            self.LED_COUNT = 14 # Set to the total number of LED lights on the robot
            # which can be more than the total number of LED lights
            # connected to the Raspberry Pi
            self.LED_PIN = 10 # GPIO pin
            self.LED_FREQ_HZ = 800000 # LED signal frequency in hertz (usually 800khz)
            self.LED_DMA = 10 # DMA channel to use for generating signal
            self.LED_BRIGHTNESS = 255 # Set to 0 for darkest and 255 for brightest
            self.LED_INVERT = False # True to invert the signal
            self.LED_CHANNEL = 0
            # Create NeoPixel object with appropriate configuration.
            self.strip = Adafruit_NeoPixel(self.LED_COUNT, self.LED_PIN, self.LED_FREQ_HZ,
            self.LED_DMA, self.LED_INVERT, self.LED_BRIGHTNESS, self.LED_CHANNEL)
            # Intialize the library (must be called once before other functions).
            self.strip.begin()

        def colorWipe(self, R, G, B):
            # This function is used to change the color of the LED
            color = Color(R,G,B)
            for i in range(self.strip.numPixels()):
                # Only one LED light color can be set at a time, so a cycle is required
                self.strip.setPixelColor(i, color)
                self.strip.show() # After calling the show method, the color will really change
# This code will control all the WS2812 lights to switch among the three colors
# Press CTRL+C to exit the program.

        def piloter(self, num_led, color, bright):                                        #initialisation de la fonction
            if color == "R":                                                                
                self.strip.setPixelColor(num_led, Color(bright,0,0))                      #on apelle la LED voulue num_led puis in ajuste sa couleur via (R,G,B) en jouant sur la brillance bright 
            elif color == "G":
                self.strip.setPixelColor(num_led, Color(0,bright,0))

            elif color == "B":
                self.strip.setPixelColor(num_led, Color(0,0,bright))

            elif color == "N":
                self.strip.setPixelColor(num_led, Color(0,0,0))

            self.strip.show()



if __name__ == '__main__':
    led = LED()

    led.piloter(0, "R")
    time.sleep(1000)

    led.piloter(1, "G")
    time.sleep(1000)

    led.piloter(2, "B")
