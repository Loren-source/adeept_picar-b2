import time
import sys
import select
from lineTracking import LineTracker
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic

BASE_ANGLE = 98
TURN = 50
SEARCH_TIME = 2          # durée de recherche de ligne perdue (ajusté selon ta logique)
DISTANCE_OBSTACLE_MM = 200   # 20 cm par défaut, paramétrable ici


def lire_clavier():
    """Lit une commande clavier si disponible, sans bloquer la boucle."""
    rlist, _, _ = select.select([sys.stdin], [], [], 0)
    if rlist:
        return sys.stdin.readline().strip()
    return None


try:
    motor      = RobotMotor()
    tracker    = LineTracker()
    ultrasonic = Ultrasonic()
    servos     = RobotServos()

    angle      = BASE_ANGLE
    last_angle = BASE_ANGLE
    servos.set_angle(0, angle)

    en_marche = False

    print("M pour démarrer | A pour arrêter")

    while True:

        # ── Lecture commande clavier ──────────────────────────────────────
        if en_marche:
            cmd = lire_clavier()          # non bloquant pendant la marche
        else:
            cmd = input("\nCommande (M / A) : ").strip()

        if cmd and cmd.lower() == "m":
            print("Départ en marche avant...")
            motor.stop_feux()
            en_marche = True

        elif cmd and cmd.lower() == "a":
            print("Arrêt manuel.")
            motor.set_motor(1, 0)
            motor.stop_feux()
            en_marche = False

        # ── Boucle de suivi de ligne (uniquement si en marche) ──────────────
        if en_marche:

            distance = ultrasonic.get_distance()    # en mm

            if distance < DISTANCE_OBSTACLE_MM:
                motor.stop()                         # arrêt + feux de détresse
                print(f"Obstacle détecté à {distance:.0f} mm !")
                en_marche = False
                continue

            status = tracker.get_status()
            tracker.print_status()
            left   = status["left"]
            middle = status["middle"]
            right  = status["right"]

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

                while time.time() - start < SEARCH_TIME:
                    motor.forward_slow()

                    # surveillance obstacle même pendant la recherche
                    distance = ultrasonic.get_distance()
                    if distance < DISTANCE_OBSTACLE_MM:
                        motor.stop()
                        print(f"Obstacle pendant la recherche, à {distance:.0f} mm !")
                        en_marche = False
                        break

                    status = tracker.get_status()
                    tracker.print_status()
                    if status["left"] == 1 or status["middle"] == 1 or status["right"] == 1:
                        print("ligne retrouvée")
                        found_line = True
                        break
                    time.sleep(0.05)

                if not en_marche:
                    continue

                if not found_line:
                    print("aucune ligne retrouvée -> recule avec la même trajectoire")
                    servos.set_angle(0, last_angle)
                    motor.backward_slow()
                    time.sleep(0.8)
                    motor.set_motor(1, 0)

            elif left == 1 and middle == 1 and right == 1:
                angle = BASE_ANGLE
                servos.set_angle(0, angle)
                motor.set_motor(1, 0)            # arrêt par sécurité, cas à valider
                last_angle = angle
                print("3 capteurs détectent -> arrêt (cas à valider/ajuster)")

            else:
                print("cas inattendu -> ralentir ou reculer")
                servos.set_angle(0, last_angle)
                motor.backward_slow()

        time.sleep(0.02)

except KeyboardInterrupt:
    motor.set_motor(1, 0)
    motor.stop_feux()
    servos.fermer()
    print("Nettoyage final réalisé")
    print("Fin du programme")
