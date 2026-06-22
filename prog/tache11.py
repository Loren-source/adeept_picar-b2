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


# Ton robot :
# angle PETIT = tourne GAUCHE
ANGLE_GAUCHE_LEGER = 75
ANGLE_GAUCHE_FORT = 55


# angle GRAND = tourne DROITE
ANGLE_DROITE_LEGER = 125
ANGLE_DROITE_FORT = 145


VITESSE_LIGNE = 32

VITESSE_CORRECTION = 24
VITESSE_VIRAGE = 20

VITESSE_RECHERCHE = 18

DISTANCE_STOP = 200


# ======================
# VARIABLES
# ======================

actif = False

angle_actuel = None
dernier_angle = ANGLE_CENTRE

derniere_direction = "centre"

temps_perte = None


# ======================
# SERVO
# ======================

def braquer(angle):

    global angle_actuel

    if angle != angle_actuel:

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
# PROGRAMME PRINCIPAL
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



        s = tracker.get_status()


        cap = (
            s["left"],
            s["middle"],
            s["right"]
        )


        print(cap)



        # ======================
        # LIGNE AU CENTRE
        # ======================


        if cap == (1,1,1):

            temps_perte = None

            avance(
                ANGLE_CENTRE,
                VITESSE_LIGNE
            )



        # ======================
        # LA LIGNE PART A GAUCHE
        # donc robot tourne GAUCHE
        # ======================


        elif cap == (0,1,1):

            temps_perte = None

            derniere_direction = "gauche"


            avance(
                ANGLE_GAUCHE_LEGER,
                VITESSE_CORRECTION
            )



        elif cap == (0,0,1):

            temps_perte = None

            derniere_direction = "gauche"


            avance(
                ANGLE_GAUCHE_FORT,
                VITESSE_VIRAGE
            )




        # ======================
        # LA LIGNE PART A DROITE
        # donc robot tourne DROITE
        # ======================


        elif cap == (1,1,0):

            temps_perte = None

            derniere_direction = "droite"


            avance(
                ANGLE_DROITE_LEGER,
                VITESSE_CORRECTION
            )



        elif cap == (1,0,0):

            temps_perte = None

            derniere_direction = "droite"


            avance(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )



        # ======================
        # PERTE DE LIGNE
        # ======================


        elif cap == (0,0,0):


            if temps_perte is None:

                temps_perte = time.time()



            # petite coupure
            if time.time() - temps_perte < 0.15:


                avance(
                    dernier_angle,
                    VITESSE_RECHERCHE
                )



            else:


                # cherche dans la dernière direction connue

                if derniere_direction == "gauche":


                    avance(
                        ANGLE_GAUCHE_FORT,
                        VITESSE_RECHERCHE
                    )



                elif derniere_direction == "droite":


                    avance(
                        ANGLE_DROITE_FORT,
                        VITESSE_RECHERCHE
                    )



                else:


                    avance(
                        ANGLE_CENTRE,
                        VITESSE_RECHERCHE
                    )



        time.sleep(0.02)



except KeyboardInterrupt:

    pass



finally:

    robot.stopper()

    braquer(ANGLE_CENTRE)

    print("FIN")
