import time
from lineTracking import LineTracker
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic

BASE_ANGLE = 98
TURN = 35

FORWARD_SEARCH_TIME = 0.8
BACKWARD_TIME = 0.8

OBSTACLE_DISTANCE = 200

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
            status = tracker.get_status()
            tracker.print_status()
            distance = ultrasonic.get_distance()

            if (
                status["left"] == 0 and
                status["middle"] == 0 and
                status["right"] == 0
            ):
                print("pas de ligne -> avance un peu")

                servos.set_angle(0, last_angle)

                found_line = False
                start = time.time()

                while time.time() - start < FORWARD_SEARCH_TIME:
                    motor.forward_slow()

                    new_status = tracker.get_status()
                    tracker.print_status()

                    if not (
                        new_status["left"] == 0 and
                        new_status["middle"] == 0 and
                        new_status["right"] == 0
                    ):
                        found_line = True
                        print("ligne retrouvée")
                        break

                    time.sleep(0.05)

                if not found_line:
                    print("toujours pas de ligne -> recule")
                    servos.set_angle(0, last_angle)
                    motor.backward_slow()
                    time.sleep(BACKWARD_TIME)
                    motor.stop()

            elif (
                status["left"] == 1 and
                status["middle"] == 0 and
                status["right"] == 0
            ):
                angle = BASE_ANGLE + TURN
                servos.set_angle(0, angle)
                motor.forward_slow()
                last_angle = angle
                print("blanc a gauche -> tourne a droite")

            elif (
                status["left"] == 0 and
                status["middle"] == 0 and
                status["right"] == 1
            ):
                angle = BASE_ANGLE - TURN
                servos.set_angle(0, angle)
                motor.forward_slow()
                last_angle = angle
                print("blanc a droite -> tourne a gauche")

            elif (
                status["left"] == 0 and
                status["middle"] == 1 and
                status["right"] == 0
            ):
                angle = BASE_ANGLE
                servos.set_angle(0, angle)
                motor.forward_slow()
                last_angle = angle
                print("centre -> tout droit")

            elif (
                status["left"] == 1 and
                status["middle"] == 1 and
                status["right"] == 0
            ):
                angle = BASE_ANGLE - TURN
                servos.set_angle(0, angle)
                motor.forward_slow()
                last_angle = angle
                print("gauche et centre -> tourne gauche")

            elif (
                status["left"] == 0 and
                status["middle"] == 1 and
                status["right"] == 1
            ):
                angle = BASE_ANGLE + TURN
                servos.set_angle(0, angle)
                motor.forward_slow()
                last_angle = angle
                print("droite et centre -> tourne droite")

            elif (
                status["left"] == 1 and
                status["middle"] == 0 and
                status["right"] == 1
            ):
                angle = BASE_ANGLE
                servos.set_angle(0, angle)
                motor.forward_slow()
                last_angle = angle
                print("gauche et droite -> tout droit")

            elif (
                status["left"] == 1 and
                status["middle"] == 1 and
                status["right"] == 1
            ):
                angle = BASE_ANGLE
                servos.set_angle(0, angle)
                motor.forward_slow()
                last_angle = angle
                print("ligne large -> tout droit")

            else:
                servos.set_angle(0, last_angle)
                motor.backward_slow()
                print("situation inattendue -> recule")

            if distance < OBSTACLE_DISTANCE:
                motor.stop()
                movement = input("Obstacle. Envoie M pour redémarrer : ")
                break

            time.sleep(0.05)

except KeyboardInterrupt:
    motor.stop()
    servos.fermer(0)
    print("Nettoyage final réalisé")
    print("Fin du programme")
