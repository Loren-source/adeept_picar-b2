import time
import smbus

class ADS7830(object):
    def __init__(self):
        self.cmd = 0x84
        self.bus=smbus.SMBus(1)
        self.address = 0x48 # 0x48 is the default i2c address for ADS7830 Module.   
        
    def analogRead(self, chn): # ADS7830 has 8 ADC input pins, chn:0,1,2,3,4,5,6,7
        value = self.bus.read_byte_data(self.address, self.cmd|(((chn<<2 | chn>>1)&0x07)<<4))
        return value

if __name__ == "__main__":
    adc = ADS7830()
    try:
        while True:
            ldr_gauche = adc.analogRead(1)   
            ldr_droite = adc.analogRead(2)   
            print(f"Gauche: {ldr_gauche:3d}   Droite: {ldr_droite:3d}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
           
        
   

