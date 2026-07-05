#!/usr/bin/env python3

import time
import threading

from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic
from lineTracking import LineTracker


# ============================================================
# INITIALISATION
# ============================================================

robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()
ultrasonic = Ultrasonic()


# ============================================================
# REGLAGES
# ============================================================

ANGLE_CENTRE = 97

ANGLE_GAUCHE = 125
ANGLE_DROITE = 65

ANGLE_SCAN_GAUCHE = 150
ANGLE_SCAN_CENTRE = 97
ANGLE_SCAN_DROITE = 40


VITESSE_AVANCE = 35
VITESSE_CONTOURNEMENT = 22
VITESSE_RECENTRAGE = 28
VITESSE_STOP = 0


# Distances (en mm)

SEUIL_SCAN = 450          # Commencer à analyser l'obstacle (45 cm)
SEUIL_ARRET = 300         # Arrêt obligatoire à 30 cm
SEUIL_DANGER = 180        # Distance critique


# Valeur de secours si le capteur renvoie une erreur

DISTANCE_FAUSSE = 3000
#!/usr/bin/env python3

import time
import threading

from motor import RobotMotor
from servo import RobotServos
from ultrasonic import Ultrasonic
from lineTracking import LineTracker


# ============================================================
# INITIALISATION
# ============================================================

robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()
ultrasonic = Ultrasonic()


# ============================================================
# REGLAGES
# ============================================================

ANGLE_CENTRE = 97

ANGLE_GAUCHE = 125
ANGLE_DROITE = 65

ANGLE_SCAN_GAUCHE = 150
ANGLE_SCAN_CENTRE = 97
ANGLE_SCAN_DROITE = 40


VITESSE_AVANCE = 35
VITESSE_CONTOURNEMENT = 22
VITESSE_RECENTRAGE = 28
VITESSE_STOP = 0


# Distances (en mm)

SEUIL_SCAN = 450          # Commencer à analyser l'obstacle (45 cm)
SEUIL_ARRET = 300         # Arrêt obligatoire à 30 cm
SEUIL_DANGER = 180        # Distance critique


# Valeur de secours si le capteur renvoie une erreur

DISTANCE_FAUSSE = 3000

# ============================================================
# ETATS DU ROBOT
# ============================================================

ETAT_AVANCER = 0
ETAT_SCAN = 1
ETAT_ARRET = 2
ETAT_BRAQUER = 3
ETAT_CONTOURNER = 4
ETAT_RECENTRER = 5


etat_robot = ETAT_AVANCER


# ============================================================
# VARIABLES GLOBALES
# ============================================================

distance = DISTANCE_FAUSSE

distance_gauche = DISTANCE_FAUSSE
distance_centre = DISTANCE_FAUSSE
distance_droite = DISTANCE_FAUSSE

direction = None          # "gauche" ou "droite"

obstacle_detecte = False
scan_effectue = False

robot_actif = True


# ============================================================
# DEPLACEMENT
# ============================================================

def avancer(vitesse=VITESSE_AVANCE):

    servos.set_angle(0, ANGLE_CENTRE)
    robot.set_motor(1, vitesse)


def stopper():

    robot.set_motor(1, 0)


def tourner_gauche():

    servos.set_angle(0, ANGLE_GAUCHE)


def tourner_droite():

    servos.set_angle(0, ANGLE_DROITE)


def recentrer():

    servos.set_angle(0, ANGLE_CENTRE)
# ============================================================
# MESURE ULTRASON
# ============================================================

def mesurer_distance():

    try:
        d = ultrasonic.get_distance() * 1000

        if d <= 0:
            return DISTANCE_FAUSSE

        return d

    except:
        return DISTANCE_FAUSSE


# ============================================================
# SCAN DE L'OBSTACLE
# ============================================================

def scanner_obstacle():

    global distance_gauche
    global distance_centre
    global distance_droite

    print("\n===== SCAN =====")

    # ----------- Gauche -----------

    servos.set_angle(1, SERVO_GAUCHE)
    time.sleep(0.35)

    distance_gauche = mesurer_distance()

    # ----------- Centre -----------

    servos.set_angle(1, SERVO_CENTRE)
    time.sleep(0.35)

    distance_centre = mesurer_distance()

    # ----------- Droite -----------

    servos.set_angle(1, SERVO_DROITE)
    time.sleep(0.35)

    distance_droite = mesurer_distance()

    # Retour au centre

    servos.set_angle(1, SERVO_CENTRE)

    print(
        f"G={distance_gauche:.0f}  "
        f"C={distance_centre:.0f}  "
        f"D={distance_droite:.0f}"
    )


# ============================================================
# CHOIX DE LA DIRECTION
# ============================================================

def choisir_direction():

    if distance_gauche >= distance_droite:
        return "gauche"

    return "droite"


# ============================================================
# DETECTION DES BORDURES
# 1 = NOIR
# 0 = BLANC
# ============================================================

def bordure_detectee():

    s = tracker.get_status()

    etat = (
        s["left"],
        s["middle"],
        s["right"]
    )

    print("[IR]", etat)

    # Au moins un capteur voit du noir
    if 1 in etat:
        return True

    return False


# ============================================================
# OBSTACLE DEVANT ?
# ============================================================

def obstacle_devant():

    d = mesurer_distance()

    print(f"[Distance] {d:.0f} mm")

    return d < DISTANCE_DETECTION
# ============================================================
# BOUCLE PRINCIPALE
# ============================================================

print("\nRobot prêt.\n")

try:

    while True:

        distance = mesurer_distance()

        print(f"Etat={etat_robot} | Distance={distance:.0f} mm")

        # =====================================================
        # AVANCER
        # =====================================================

        if etat_robot == ETAT_AVANCER:

            avancer()

            # Détection d'un obstacle à environ 45 cm
            if distance < DISTANCE_DETECTION:

                stopper()
                etat_robot = ETAT_SCAN

        # =====================================================
        # SCAN (UNE SEULE FOIS)
        # =====================================================

        elif etat_robot == ETAT_SCAN:

            scanner_obstacle()

            direction = choisir_direction()

            print("Direction choisie :", direction)

            etat_robot = ETAT_ARRET

        # =====================================================
        # APPROCHE
        # =====================================================

        elif etat_robot == ETAT_ARRET:

            # On s'approche doucement jusqu'à 30 cm

            if distance > DISTANCE_STOP:

                avancer(VITESSE_LENTE)

            else:

                stopper()

                time.sleep(0.2)

                etat_robot = ETAT_BRAQUER

        # =====================================================
        # BRAQUER
        # =====================================================

        elif etat_robot == ETAT_BRAQUER:

            if direction == "gauche":

                tourner_gauche()

            else:

                tourner_droite()

            robot.set_motor(1, VITESSE_TOURNER)

            # Tant qu'on ne voit PAS la bordure noire
            while not bordure_detectee():
                robot.set_motor(1, VITESSE_TOURNER)
                time.sleep(0.02)

            stopper()

            etat_robot = ETAT_CONTOURNER

        # =====================================================
        # CONTOURNEMENT
        # =====================================================

        elif etat_robot == ETAT_CONTOURNER:

            robot.set_motor(1, VITESSE_AVANCE)

            # On longe la bordure

            while bordure_detectee():
                robot.set_motor(1, VITESSE_AVANCE)
                time.sleep(0.02)

            stopper()

            etat_robot = ETAT_RECENTRER

        # =====================================================
        # RECENTRAGE
        # =====================================================

        elif etat_robot == ETAT_RECENTRER:

            recentrer()

            robot.set_motor(1, VITESSE_AVANCE)

            time.sleep(0.5)

            stopper()

            etat_robot = ETAT_AVANCER

        time.sleep(0.03)

except KeyboardInterrupt:

    print("\nInterruption utilisateur.")

finally:

    print("\nArrêt du robot...")

    robot.stopper()

    servos.set_angle(0, ANGLE_CENTRE)
    servos.set_angle(1, SERVO_CENTRE)
