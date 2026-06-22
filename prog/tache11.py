#!/usr/bin/env python3

import time
import threading

from motor import RobotMotor
from ultra import Ultrasonic
from lineTracking import LineTracker
from servo import RobotServos


# ======================
# INITIALISATION
# ======================

robot = RobotMotor()
ultra = Ultrasonic()
tracker = LineTracker()
servos = RobotServos()


# ======================
# REGLAGES
# ======================

ANGLE_CENTRE = 97

# SUR TON ROBOT :
# petit angle = gauche
# grand angle = droite

ANGLE_GAUCHE_LEGER = 75
ANGLE_GAUCHE_FORT = 55

ANGLE_DROITE_LEGER = 125
ANGLE_DROITE_FORT = 145


VITESSE_DROITE = 30
VITESSE_CORRECTION = 24
VITESSE_VIRAGE = 25
VITESSE_RECHERCHE = 25

DISTANCE_STOP = 200


# ======================
# VARIABLES
# ======================

actif = False

angle_actuel = None

dernier_angle = ANGLE_CENTRE
derniere_direction = "centre"



# ======================
# SERVO
# ======================

def braquer(angle):

    global angle_actuel

    if angle_actuel != angle:

        servos.set_angle(0, angle)

        print("[CH00] →", angle, "°")

        angle_actuel = angle



# ======================
# MOTEUR
# ======================

def avance(angle, vitesse):

    global dernier_angle

    dernier_angle = angle

    braquer(angle)

    robot.set_motor(1, vitesse)



# ======================
# CLAVIER
# ======================

def clavier():

    global actif

    while True:

        c = input().strip().upper()

        if c == "M":

            actif = True

            print("START")


        elif c == "A":

            actif = False

            robot.stopper()

            print("STOP")



threading.Thread(
    target=clavier,
    daemon=True
).start()



# ======================
# BOUCLE PRINCIPALE
# ======================

try:

    while True:


        if not actif:

            time.sleep(0.02)
            continue



        # obstacle

        if ultra.get_distance() < DISTANCE_STOP:

            robot.stopper()
            actif = False
            continue



        # capteurs ligne

        s = tracker.get_status()


        cap = (
            s["left"],
            s["middle"],
            s["right"]
        )


        print(cap)



        # =====================
        # TOUT DROIT
        # =====================

        if cap == (1,1,1):

            derniere_direction = "centre"

            avance(
                ANGLE_CENTRE,
                VITESSE_DROITE
            )



        # =====================
        # VIRAGE DROITE
        # =====================
        # ton 2e virage


        elif cap == (1,1,0):

            derniere_direction = "droite"

            avance(
                ANGLE_DROITE_LEGER,
                VITESSE_CORRECTION
            )



        elif cap == (1,0,0):

            derniere_direction = "droite"

            avance(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )



        # =====================
        # VIRAGE GAUCHE
        # =====================
        # ton 1er et 3e virage


        elif cap == (0,1,1):

            derniere_direction = "gauche"

            avance(
                ANGLE_GAUCHE_LEGER,
                VITESSE_CORRECTION
            )



        elif cap == (0,0,1):

            derniere_direction = "gauche"

            avance(
                ANGLE_GAUCHE_FORT,
                VITESSE_VIRAGE
            )



        # =====================
        # PERTE LIGNE
        # =====================
        # continue le dernier virage


        elif cap == (0,0,0):


            if derniere_direction == "droite":

                avance(
                    ANGLE_DROITE_FORT,
                    VITESSE_RECHERCHE
                )



            elif derniere_direction == "gauche":

                avance(
                    ANGLE_GAUCHE_FORT,
                    VITESSE_RECHERCHE
                )



            else:

                avance(
                    ANGLE_CENTRE,
                    18
                )



        time.sleep(0.02)



except KeyboardInterrupt:

    pass



finally:

    robot.stopper()

    braquer(ANGLE_CENTRE)

    print("FIN")
