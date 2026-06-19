#!/usr/bin/env python3
# PiCar-B suivi ligne 2-3 cm
# 1 = noir, 0 = blanc

import time
import threading

from motor import RobotMotor
from ultra import Ultrasonic
from lineTracking import LineTracker
from servo import RobotServos


# =============================
# INITIALISATION
# =============================

robot = RobotMotor()
ultra = Ultrasonic()
tracker = LineTracker()
servos = RobotServos()


# =============================
# REGLAGES
# =============================

ANGLE_CENTRE = 97

# correction progressive
ANGLE_GAUCHE_LEGER = 90
ANGLE_GAUCHE_FORT = 82

ANGLE_DROITE_LEGER = 104
ANGLE_DROITE_FORT = 112


# marche arrière seulement si vraie perte
ANGLE_RECH_GAUCHE = 70
ANGLE_RECH_DROITE = 125


# vitesses adaptées ligne fine
VITESSE_LIGNE = 40
VITESSE_CORRECTION = 30
VITESSE_VIRAGE = 23

VITESSE_TROU = 20
VITESSE_RECHERCHE = 18


# tolérance interruption de ligne
TEMPS_PERTE_MAX = 0.08


DISTANCE_STOP = 200


# =============================
# VARIABLES
# =============================

actif = False

etat = "SUIVI"

angle_actuel = None

dernier_angle = ANGLE_CENTRE

derniere_direction = "centre"

debut_perte = None


# =============================
# MOUVEMENTS
# =============================

def braquer(angle):

    global angle_actuel

    if angle != angle_actuel:
        servos.set_angle(0, angle)
        angle_actuel = angle



def avancer(angle, vitesse):

    global dernier_angle

    dernier_angle = angle

    braquer(angle)

    robot.set_motor(1, vitesse)



def reculer(angle, vitesse):

    braquer(angle)

    robot.set_motor(-1, vitesse)



# =============================
# CLAVIER
# =============================

def clavier():

    global actif

    while True:

        c = input().strip().upper()


        if c == "M":

            actif = True

            robot.stop_feux()

            print("DEPART")


        elif c == "A":

            actif = False

            robot.stopper()

            print("ARRET")



threading.Thread(
    target=clavier,
    daemon=True
).start()



# =============================
# PROGRAMME PRINCIPAL
# =============================

try:

    while True:


        if not actif:

            time.sleep(0.02)
            continue



        # obstacle

        if ultra.get_distance() < DISTANCE_STOP:

            robot.stop()

            actif = False

            continue



        # lecture capteurs

        capteurs = tracker.get_status()

        lecture = (
            capteurs["left"],
            capteurs["middle"],
            capteurs["right"]
        )


        print(
            lecture,
            etat
        )



        # =============================
        # RECHERCHE
        # =============================

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


            # ligne retrouvée

            if lecture != (0,0,0):

                debut_perte = None

                etat = "SUIVI"


            continue



        # =============================
        # SUIVI DE LIGNE
        # =============================


        # parfaitement centré

        if lecture == (1,1,1):

            debut_perte = None

            derniere_direction = "centre"

            avancer(
                ANGLE_CENTRE,
                VITESSE_LIGNE
            )



        # dérive droite ou début virage gauche

        elif lecture == (1,1,0):

            debut_perte = None

            derniere_direction = "gauche"

            avancer(
                ANGLE_GAUCHE_LEGER,
                VITESSE_CORRECTION
            )



        # virage gauche confirmé

        elif lecture == (1,0,0):

            debut_perte = None

            derniere_direction = "gauche"

            avancer(
                ANGLE_GAUCHE_FORT,
                VITESSE_VIRAGE
            )



        # dérive gauche ou début virage droite

        elif lecture == (0,1,1):

            debut_perte = None

            derniere_direction = "droite"

            avancer(
                ANGLE_DROITE_LEGER,
                VITESSE_CORRECTION
            )



        # virage droite confirmé

        elif lecture == (0,0,1):

            debut_perte = None

            derniere_direction = "droite"

            avancer(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )



        # =============================
        # INTERRUPTION / PERTE
        # =============================

        elif lecture == (0,0,0):


            if debut_perte is None:

                debut_perte = time.time()



            temps = time.time() - debut_perte



            if temps < TEMPS_PERTE_MAX:


                # on garde le dernier mouvement

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

    print("Nettoyage termine")
