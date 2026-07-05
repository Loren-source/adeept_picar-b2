#!/usr/bin/env python3

import time

from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic
from lineTracking import LineTracker


# ============================================================
# INITIALISATION
# ============================================================

robot = RobotMotor()
servos = RobotServos()
ultrasonic = Ultrasonic()
tracker = LineTracker()


# ============================================================
# REGLAGES
# ============================================================

# Servo de direction
ANGLE_CENTRE = 97
ANGLE_GAUCHE = 125
ANGLE_DROITE = 65

# Servo de l'ultrason
ANGLE_SCAN_GAUCHE = 150
ANGLE_SCAN_CENTRE = 97
ANGLE_SCAN_DROITE = 40


# ============================================================
# VITESSES
# ============================================================

VITESSE_AVANCE = 35          # déplacement normal
VITESSE_APPROCHE = 15        # approche de l'obstacle
VITESSE_CONTOURNEMENT = 18   # pendant le contournement
VITESSE_SORTIE = 22          # sortie de l'obstacle


# ============================================================
# DISTANCES (mm)
# ============================================================

DISTANCE_SCAN = 450          # début du scan (45 cm)
DISTANCE_BRAQUAGE = 300      # début du contournement (30 cm)
DISTANCE_CRITIQUE = 180      # sécurité


DISTANCE_FAUSSE = 3000


# ============================================================
# ETATS
# ============================================================

ETAT_AVANCER = 0
ETAT_SCAN = 1
ETAT_APPROCHE = 2
ETAT_BRAQUER = 3
ETAT_CONTOURNER = 4
ETAT_SORTIE = 5
ETAT_RECENTRER = 6


etat_robot = ETAT_AVANCER


# ============================================================
# VARIABLES
# ============================================================

direction = None

distance = DISTANCE_FAUSSE

distance_gauche = DISTANCE_FAUSSE
distance_centre = DISTANCE_FAUSSE
distance_droite = DISTANCE_FAUSSE

# ============================================================
# DEPLACEMENTS
# ============================================================

def avancer(vitesse=VITESSE_AVANCE):

    servos.set_angle(0, ANGLE_CENTRE)
    robot.set_motor(1, vitesse)


def avancer_braque():

    if direction == "gauche":
        servos.set_angle(0, ANGLE_GAUCHE)
    else:
        servos.set_angle(0, ANGLE_DROITE)

    robot.set_motor(1, VITESSE_APPROCHE)


def tourner_gauche():

    servos.set_angle(0, ANGLE_GAUCHE)
    robot.set_motor(1, VITESSE_CONTOURNEMENT)


def tourner_droite():

    servos.set_angle(0, ANGLE_DROITE)
    robot.set_motor(1, VITESSE_CONTOURNEMENT)


def recentrer():

    servos.set_angle(0, ANGLE_CENTRE)


def stopper():

    robot.set_motor(1, 0)


# ============================================================
# ULTRASON
# ============================================================

def mesurer_distance():

    try:

        d = ultrasonic.get_distance()

        if d <= 0:
            return DISTANCE_FAUSSE

        return d

    except:

        return DISTANCE_FAUSSE


# ============================================================
# SCAN
# ============================================================

def scanner_obstacle():

    global distance_gauche
    global distance_centre
    global distance_droite

    print("\n===== SCAN =====")

    # ---------- Gauche ----------

    servos.set_angle(1, ANGLE_SCAN_GAUCHE)
    time.sleep(0.35)

    distance_gauche = mesurer_distance()

    # ---------- Centre ----------

    servos.set_angle(1, ANGLE_SCAN_CENTRE)
    time.sleep(0.35)

    distance_centre = mesurer_distance()

    # ---------- Droite ----------

    servos.set_angle(1, ANGLE_SCAN_DROITE)
    time.sleep(0.35)

    distance_droite = mesurer_distance()

    # Retour au centre

    servos.set_angle(1, ANGLE_SCAN_CENTRE)

    print(
        f"G={distance_gauche:.0f} mm | "
        f"C={distance_centre:.0f} mm | "
        f"D={distance_droite:.0f} mm"
    )


# ============================================================
# CHOIX DE LA DIRECTION
# ============================================================

def choisir_direction():

    if distance_gauche >= distance_droite:
        return "gauche"

    return "droite"


# ============================================================
# CAPTEURS IR
# 1 = NOIR
# 0 = BLANC
# ============================================================

def lire_ir():

    s = tracker.get_status()

    return (
        s["left"],
        s["middle"],
        s["right"]
    )


def bordure_detectee():

    etat = lire_ir()

    print("[IR]", etat)

    # Si au moins un capteur voit le bord noir
    return 1 in etat


def arena_retrouvee():

    etat = lire_ir()

    print("[IR]", etat)

    # Tous les capteurs sont revenus sur le blanc
    return etat == (0, 0, 0)
# ============================================================
# INITIALISATION
# ============================================================

print("\n==================================================")
print("MISSION C - EVITEMENT D'OBSTACLES")
print("==================================================")

# Direction des roues au centre
servos.set_angle(0, ANGLE_CENTRE)

# Caméra / Ultrason au centre
servos.set_angle(1, ANGLE_SCAN_CENTRE)

# Arrêt des moteurs
stopper()

time.sleep(1)

print("\nRobot prêt.\n")
# ============================================================
# BOUCLE PRINCIPALE
# ============================================================

try:

    while True:

        distance = mesurer_distance()

        print(f"Etat={etat_robot} | Distance={distance:.0f} mm")

        # =====================================================
        # AVANCER
        # =====================================================

        if etat_robot == ETAT_AVANCER:

            avancer()

            if distance <= DISTANCE_SCAN:

                stopper()
                etat_robot = ETAT_SCAN


        # =====================================================
        # SCAN
        # =====================================================

        elif etat_robot == ETAT_SCAN:

            scanner_obstacle()

            direction = choisir_direction()

            print("Direction :", direction)

            etat_robot = ETAT_APPROCHE


        # =====================================================
        # APPROCHE
        # =====================================================

        elif etat_robot == ETAT_APPROCHE:

            avancer_braque()

            # ralentissement progressif

            if distance > 400:

                robot.set_motor(1,18)

            elif distance > 350:

                robot.set_motor(1,15)

            else:

                robot.set_motor(1,10)

            if distance <= DISTANCE_BRAQUAGE:

                stopper()
                time.sleep(0.15)

                etat_robot = ETAT_BRAQUER


        # =====================================================
        # BRAQUAGE
        # =====================================================

        elif etat_robot == ETAT_BRAQUER:

            if direction == "gauche":

                while not bordure_detectee():

                    tourner_gauche()

                    time.sleep(0.02)

            else:

                while not bordure_detectee():

                    tourner_droite()

                    time.sleep(0.02)

            stopper()

            etat_robot = ETAT_CONTOURNER


        # =====================================================
        # CONTOURNEMENT
        # =====================================================

        elif etat_robot == ETAT_CONTOURNER:

            recentrer()

            robot.set_motor(1,VITESSE_SORTIE)

            while bordure_detectee():

                recentrer()

                robot.set_motor(1,VITESSE_SORTIE)

                time.sleep(0.02)

            stopper()

            etat_robot = ETAT_RECENTRER


        # =====================================================
        # RECENTRAGE
        # =====================================================

        elif etat_robot == ETAT_RECENTRER:

            recentrer()

            robot.set_motor(1,VITESSE_SORTIE)

            time.sleep(0.6)

            stopper()

            etat_robot = ETAT_AVANCER


        time.sleep(0.03)


except KeyboardInterrupt:

    print("\nInterruption utilisateur.")


finally:

    print("\nArrêt du robot...")

    stopper()

    servos.set_angle(0,ANGLE_CENTRE)
    servos.set_angle(1,ANGLE_SCAN_CENTRE)
