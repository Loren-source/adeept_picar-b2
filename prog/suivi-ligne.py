import time
from lineTracking import LineTracker
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic

try:
    motor = RobotMotor()
    tracker = LineTracker()
    ultrasonic = Ultrasonic()
    servos = RobotServos()

    angle = 98
    last_angle = angle
    servos.set_angle(0, angle)

    while True:
        movement = input("Appuie sur M pour démarrer : ")

        while movement.lower() == "m":
            status = tracker.get_status()
            tracker.print_status()

            distance = ultrasonic.get_distance()


            last_angle = angle


            angle = 98
            servos.set_angle(0, angle)

            if (
                status["left"] == 0 and
                status["middle"] == 0 and
                status["right"] == 0
            ):
                print("ligne perdue -> avance un peu pour chercher la suite")

                servos.set_angle(0, last_angle)

                found_line = False
                start = time.time()


                while time.time() - start < 0.7:
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
                    time.sleep(0.7)
                    motor.stop()

            elif (
                status["left"] == 1 and
                status["middle"] == 0 and
                status["right"] == 0
            ):
                angle = 98 + 60
                servos.set_angle(0, angle)
                motor.forward_slow()
                print("blanc a gauche -> tourne a droite")

            elif (
                status["left"] == 0 and
                status["middle"] == 0 and
                status["right"] == 1
            ):
                angle = 98 - 60
                servos.set_angle(0, angle)
                motor.forward_slow()
                print("blanc a droite -> tourne a gauche")

            elif (
                status["left"] == 0 and
                status["middle"] == 1 and
                status["right"] == 0
            ):
                angle = 98
                servos.set_angle(0, angle)
                motor.forward_slow()
                print("ligne au centre -> tout droit")

            elif (
                status["left"] == 1 and
                status["middle"] == 1 and
                status["right"] == 0
            ):
                angle = 98 - 60
                servos.set_angle(0, angle)
                motor.forward_slow()
                print("blanc a gauche et au centre -> tourne a droite")

            elif (
                status["left"] == 0 and
                status["middle"] == 1 and
                status["right"] == 1
            ):
                angle = 98 + 60
                servos.set_angle(0, angle)
                motor.forward_slow()
                print("blanc a droite et au centre -> tourne a gauche")

            elif (
                status["left"] == 1 and
                status["middle"] == 0 and
                status["right"] == 1
            ):
                angle = 98
                servos.set_angle(0, angle)
                motor.forward_slow()
                print("gauche et droite -> tout droit")

            elif (
                status["left"] == 1 and
                status["middle"] == 1 and
                status["right"] == 1
            ):
                motor.stop()
                print("ligne totalement perdue ou zone blanche -> stop")

            else:
                servos.set_angle(0, last_angle)
                motor.backward_slow()
                print("Situation inattendue, recule lentement")


            if distance < 20:
                motor.stop()
                movement = input("Obstacle détecté. Envoie M pour redémarrer : ")
                break

except KeyboardInterrupt:
    motor.stop()
    servos.fermer(0)
    print("Nettoyage final réalisé")
    print("Fin du programme")
