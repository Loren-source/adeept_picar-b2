import time
from gpiozero import LED as GPIO_LED   # CORRECTION 3 : ajout import phares
from ultra import Ultrasonic
from Spi_WS2812 import LED
from motor import RobotMotor

# CORRECTION 1 : constante 200mm = 20cm
DISTANCE_ARRET = 200

# CORRECTION 3 : phares RGB
r_rouge = GPIO_LED(1)
l_rouge = GPIO_LED(13)

def phares_rouge():
    r_rouge.off()   # logique inversée
    l_rouge.off()

def phares_off():
    r_rouge.on()
    l_rouge.on()

# CORRECTION 2 : rampe de décélération
def deceleration(vitesse_depart, duree=1.0):
    steps = 20
    delay = duree / steps
    for i in range(steps):
        v = round(vitesse_depart * (steps - i) / steps)
        motor.set_motor(1, v)
        time.sleep(delay)
    motor.stop()

try:
    led        = LED()
    motor      = RobotMotor()
    ultrasonic = Ultrasonic()
    movement = input("Appuie sur M pour démarrer : ")
    while True:
        if movement == "M":
            motor.drive_with_ramp(20, 1, 5)
            distance1 = ultrasonic.get_distance()
            print(f"Distance : {distance1:.2f} mm")
            time.sleep(0.05)
            while True:                          # surveillance continue
                distance = ultrasonic.get_distance()
                print(f"Distance : {distance:.2f} mm")
                time.sleep(0.05)
                if distance < DISTANCE_ARRET:    # CORRECTION 1 : 200 au lieu de 600
                    deceleration(20, 1.0)        # CORRECTION 2 : rampe au lieu de motor.stop()
                    phares_rouge()               # CORRECTION 3 : phares RGB
                    movement = input("Envoie M pour redémarrer : ")
                    break                        # sort de la surveillance
        elif movement in ("A", "a"):
            deceleration(20, 1.0)               # CORRECTION 2 : rampe au lieu de motor.stop()
            phares_rouge()                      # CORRECTION 3 : phares RGB
            print("Arrêt manuel")
            movement = input("Envoie M pour redémarrer : ")
        else:
            movement = input("Commande inconnue. M pour démarrer : ")
except KeyboardInterrupt:
    print("Fin de programme par Ctrl-C")
finally:
    motor.stop()                                # CORRECTION 4 : supprimé ultrasonic.close()
    print("Nettoyage final réalisé")
