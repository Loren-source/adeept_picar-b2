import time
import threading
from ultra import Ultrasonic
from Spi_WS2812 import LED
from motor import RobotMotor

try:
    led        = LED()
    motor      = RobotMotor()
    ultrasonic = Ultrasonic()

    movement = input("Appuie sur M pour démarrer : ")

    while True:
        if movement == "M":
            motor.stop_feux()                        # CORRECTION 2 : éteint les feux avant de repartir
            motor.drive_with_ramp(20, 1, 1)          # CORRECTION 3 : rampe 1s au lieu de 5s
            distance1 = ultrasonic.get_distance()
            print(f"Distance : {distance1:.2f} mm")
            time.sleep(0.05)

            while True:                              # surveillance continue
                distance = ultrasonic.get_distance()
                print(f"Distance : {distance:.2f} mm")
                time.sleep(0.05)

                if distance < 200:
                    motor.stop()                     # arrêt + feux de détresse (défini dans motor.py)
                    movement = input("Envoie M pour redémarrer : ")
                    break                            # sort de la surveillance

        elif movement in ("A", "a"):
            motor.stop()
            print("Arrêt manuel")
            movement = input("Envoie M pour redémarrer : ")

        else:
            movement = input("Commande inconnue. M pour démarrer : ")

except KeyboardInterrupt:
    print("Fin de programme")

finally:
    # CORRECTION 1 : suppression de ultrasonic.close() qui n'existe pas
    motor.stop()
    print("Nettoyage final réalisé")
