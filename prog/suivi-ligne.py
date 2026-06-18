import time
from lineTracking import LineTracker
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic

BASE_ANGLE = 98
TURN = 50
SEARCH_TIME = 0.5

try:
    motor = RobotMotor()
    tracker = LineTracker()
    ultrasonic = Ultrasonic()
    servos = RobotServos()

    angle = BASE_ANGLE
    last_angle = BASE_ANGLE

    servos.set_angle(0, angle)

    while True:
        movement = input("Appuie sur M pour démarrer : ")

        while movement.lower() == "m":

            distance = ultrasonic.get_distance()

            if distance < 20:
                motor.stop()
                movement = input("Obstacle détecté EN TEST ")
                break

            status = tracker.get_status()
            tracker.print_status()

            left = status["left"]
            middle = status["middle"]
            right = status["right"]


            if left == 0 and middle == 1 and right == 0:
                angle = BASE_ANGLE
                servos.set_angle(0, angle)
                motor.forward_slow()
                last_angle = angle
                print("ligne au centre -> tout droit")


            elif left == 1 and middle == 1 and right == 0:
                angle = BASE_ANGLE - TURN
                servos.set_angle(0, angle)
                motor.forward_slow()
                last_angle = angle
                print("ligne vers gauche -> tourne gauche")

            elif left == 1 and middle == 0 and right == 0:
                angle = BASE_ANGLE - TURN
                servos.set_angle(0, angle)
                motor.forward_slow()
                last_angle = angle
                print("ligne très à gauche -> tourne gauche")


            elif left == 0 and middle == 1 and right == 1:
                angle = BASE_ANGLE + TURN
                servos.set_angle(0, angle)
                motor.forward_slow()
                last_angle = angle
                print("ligne vers droite -> tourne droite")

            elif left == 0 and middle == 0 and right == 1:
                angle = BASE_ANGLE + TURN
                servos.set_angle(0, angle)
                motor.forward_slow()
                last_angle = angle
                print("ligne très à droite -> tourne droite")


            elif left == 0 and middle == 0 and right == 0:
                print("ligne perdue -> avance un peu pour chercher un pointillé")

                servos.set_angle(0, last_angle)

                start = time.time()
                found_line = False


                while time.time() - start < 2:  # à ajuster selon ta vitesse
                    motor.forward_slow()

                    status = tracker.get_status()
                    tracker.print_status()

                    if status["left"] == 1 or status["middle"] == 1 or status["right"] == 1:
                        print("ligne retrouvée")
                        found_line = True
                        break

                    time.sleep(0.05)


                if not found_line:
                    print("aucune ligne retrouvée -> recule avec la même trajectoire")
                    servos.set_angle(0, last_angle)
                    motor.backward_slow()
                    time.sleep(0.8)
                    motor.stop()


            elif left == 1 and middle == 1 and right == 1:
                angle = BASE_ANGLE
                servos.set_angle(0, angle)
                #motor.forward_slow()
                last_angle = angle
                print("a TESTER, 3 capteurs detectent !")
                #tester tourner a droite/gauche


            else:
                print("cas inattendu -> ralentir ou reculer")
                servos.set_angle(0, last_angle)
                motor.backward_slow()

except KeyboardInterrupt:
    motor.stop()
    servos.fermer(0)
    print("Nettoyage final réalisé")
    print("Fin du programme")
