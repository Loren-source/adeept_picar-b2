#!/usr/bin/env python3

import time
import threading
from motor import RobotMotor
from ultra import Ultrasonic
from lineTracking import LineTracker
from servo import RobotServos

robot = RobotMotor()
ultra = Ultrasonic()
tracker = LineTracker()
servos = RobotServos()

ANGLE_CENTRE = 97

ANGLE_GAUCHE_LEGER = 92
ANGLE_GAUCHE_FORT = 82

ANGLE_DROITE_LEGER = 102
ANGLE_DROITE_FORT = 112

ANGLE_RECH_GAUCHE = 70
ANGLE_RECH_DROITE = 120


VITESSE_MAX = 60
VITESSE_CORRECTION = 45
VITESSE_VIRAGE = 32
VITESSE_TROU = 28
VITESSE_RECHERCHE = 20

TEMPS_AVANT_RECHERCHE = 0.35
DISTANCE_STOP = 200

actif = False
etat = "SUIVI"

angle_actuel = None
derniere_direction = "centre"

dernier_angle = ANGLE_CENTRE
derniere_vitesse = VITESSE_MAX
debut_000 = None

def braquer(angle):
    global angle_actuel
    if angle != angle_actuel:
        servos.set_angle(0, angle)
        angle_actuel = angle

def avancer(angle, vitesse):

    global dernier_angle
    global derniere_vitesse

    dernier_angle = angle
    derniere_vitesse = vitesse

    braquer(angle)
    robot.set_motor(1, vitesse)


def reculer(angle, vitesse):

    braquer(angle)
    robot.set_motor(-1, vitesse)


# =========================
# CLAVIER
# =========================

def clavier():

    global actif

    while True:

        cmd = input().strip().upper()

        if cmd == "M":

            actif = True
            robot.stop_feux()
            print("DEPART")

        elif cmd == "A":

            actif = False
            robot.stopper()
            print("ARRET")


threading.Thread(target=clavier, daemon=True).start()


# =========================
# MAIN
# =========================

try:

    while True:

        if not actif:
            time.sleep(0.02)
            continue


        if ultra.get_distance() < DISTANCE_STOP:

            robot.stop()
            actif = False
            continue


        capteurs = tracker.get_status()

        lecture = (
            capteurs["left"],
            capteurs["middle"],
            capteurs["right"]
        )


        print(lecture, etat)


        # =========================
        # RECHERCHE
        # =========================

        if etat == "RECHERCHE":

            if derniere_direction == "gauche":

                reculer(
                    ANGLE_RECH_GAUCHE,
                    VITESSE_RECHERCHE
                )

            elif derniere_direction == "droite":

                reculer(
                    ANGLE_RECH_DROITE,
                    VITESSE_RECHERCHE
                )

            else:

                reculer(
                    ANGLE_CENTRE,
                    VITESSE_RECHERCHE
                )


            if lecture == (1,1,1):

                robot.stopper()

                braquer(ANGLE_CENTRE)

                time.sleep(0.1)

                debut_000 = None

                etat = "SUIVI"


            continue


        # =========================
        # SUIVI FLUIDE
        # =========================


        if lecture == (1,1,1):

            debut_000 = None

            derniere_direction = "centre"

            avancer(
                ANGLE_CENTRE,
                VITESSE_MAX
            )


        elif lecture == (1,1,0):

            debut_000 = None

            derniere_direction = "gauche"

            avancer(
                ANGLE_GAUCHE_LEGER,
                VITESSE_CORRECTION
            )


        elif lecture == (1,0,0):

            debut_000 = None

            derniere_direction = "gauche"

            avancer(
                ANGLE_GAUCHE_FORT,
                VITESSE_VIRAGE
            )


        elif lecture == (0,1,1):

            debut_000 = None

            derniere_direction = "droite"

            avancer(
                ANGLE_DROITE_LEGER,
                VITESSE_CORRECTION
            )


        elif lecture == (0,0,1):

            debut_000 = None

            derniere_direction = "droite"

            avancer(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )


        # =========================
        # INTERRUPTION DE LIGNE
        # =========================

        elif lecture == (0,0,0):

            if debut_000 is None:
                debut_000 = time.time()


            temps = time.time() - debut_000


            if temps < TEMPS_AVANT_RECHERCHE:

                # on continue le virage ou la ligne
                avancer(
                    dernier_angle,
                    VITESSE_TROU
                )


            else:

                etat = "RECHERCHE"


        time.sleep(0.02)


except KeyboardInterrupt:

    print("FIN")


finally:

    robot.stopper()

    braquer(ANGLE_CENTRE)

    print("Robot nettoye")
