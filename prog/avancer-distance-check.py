import time
import threading
from ultra import Ultrasonic
from Spi_WS2812 import LED
from motor import RobotMotor

try:
    led        = LED()
    motor      = RobotMotor()
    ultrasonic = Ultrasonic()

    def feux_detresse():
        threads = [
            threading.Thread(target=led.piloter, args=(2, 'R', 255)),
            threading.Thread(target=led.piloter, args=(3, 'R', 255)),
            threading.Thread(target=led.piloter, args=(4, 'R', 255)),
            threading.Thread(target=led.piloter, args=(5, 'R', 255)),
            threading.Thread(target=led.piloter, args=(6, 'R', 255)),
            threading.Thread(target=led.piloter, args=(7, 'R', 255)),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    movement = input("Appuie sur M pour démarrer : ")

    while True:
        if movement == "M":
            motor.drive_with_ramp(1, 60, 5)

            while True:                          # surveillance continue
                distance = ultrasonic.get_distance()
                print(f"Distance : {distance:.2f} mm")
                time.sleep(0.05)

                if distance < 200:
                    motor.stop()
                    feux_detresse()
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
    motor.stop()
    print("Nettoyage final réalisé")