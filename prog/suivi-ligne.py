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

    angle_centre = 98
    servos.set_angle(0, angle_centre)

    while True:
        movement = input("Appuie sur M pour démarrer : ")

        # Si on redémarre après un arrêt sur obstacle, on éteint les feux de détresse
        motor.stop_feux()

        while movement in ('M', 'm'):
            status = tracker.get_status()
            tracker.print_status()
            distance = ultrasonic.get_distance()  # en mm

            angle = angle_centre
            servos.set_angle(0, angle)

            # --- Logique de suivi de ligne ---
            if status['left'] == 0 and status['middle'] == 0 and status['right'] == 0:
                motor.backward_slow()
                print("pas de ligne -> tout droit")

            elif status['left'] == 1 and status['middle'] == 0 and status['right'] == 0:
                servos.set_angle(0, angle + 60)  # tester prudemment, roues décollées
                motor.forward_slow()
                print("blanc a gauche -> tourne a droite")

            elif status['left'] == 0 and status['middle'] == 0 and status['right'] == 1:
                servos.set_angle(0, angle - 60)
                motor.forward_slow()
                print("blanc a droite -> tourne a gauche")

            elif status['left'] == 0 and status['middle'] == 1 and status['right'] == 0:
                motor.forward_slow()
                print("improbable -> tout droit")

            elif status['left'] == 1 and status['middle'] == 1 and status['right'] == 0:
                servos.set_angle(0, angle - 60)
                motor.forward_slow()
                print("blanc a gauche et au centre -> tourne a droite")

            elif status['left'] == 0 and status['middle'] == 1 and status['right'] == 1:
                servos.set_angle(0, angle + 60)
                motor.forward_slow()
                print("blanc a droite et au centre -> tourne a gauche")

            elif status['left'] == 1 and status['middle'] == 0 and status['right'] == 1:
                motor.forward_slow()
                print("gauche et droite -> tout droit")

            elif status['left'] == 1 and status['middle'] == 1 and status['right'] == 1:
                # A valider physiquement : sortie complete de ligne ou intersection ?
                motor.stop()
                print("3 capteurs actifs -> arret de securite")

            else:
                motor.backward_slow()
                print("Situation inattendue, recule lentement")

            # --- Détection d'obstacle (Tâche 9) ---
            if distance < 200:  # 200 mm = 20 cm
                motor.stop()  # déclenche déjà les feux de détresse
                movement = input("Obstacle détecté. Envoie M pour redémarrer : ")
                break

except KeyboardInterrupt:
    motor.stop()
    servos.fermer()
    print("Nettoyage final réalisé")
    print("Fin du programme")
