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
            motor.drive_with_ramp(60, 1, 5)

            while True:                          # surveillance continue
                distance = ultrasonic.get_distance()
                print(f"Distance : {distance:.2f} mm")
                time.sleep(0.05)

                if distance < 600:
                    motor.stop()
                    movement = input("Envoie M pour redémarrer : ")
                    break                        # sort de la surveillance

        elif movement in ("A", "a"):
            motor.stop()
            print("Arrêt manuel")
            movement = input("Envoie M pour redémarrer : ")

        else:
            movement = input("Commande inconnue. M pour démarrer : ")

except KeyboardInterrupt:
    print("Fin de programme par Ctrl-C")

finally:
    ultrasonic.close()  # libère GPIO24
    motor.stop()
    print("Nettoyage final réalisé")