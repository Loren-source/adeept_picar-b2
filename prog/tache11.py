#!/usr/bin/env python3

import time

from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker


robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()


# =========================
# REGLAGES
# =========================

CENTRE = 97


# corrections douces
GAUCHE_LEGER = 112
DROITE_LEGER = 78


# gros virages
GAUCHE_FORT = 128
DROITE_FORT = 55


# vitesses
VITESSE_LIGNE = 32
VITESSE_VIRAGE = 16
VITESSE_PERDU = 13


angle_actuel = CENTRE

dernier_sens = 0
compteur_virage = 0
perdu_count = 0



# =========================
# SERVO INTELLIGENT
# =========================

def tourner(cible):

    global angle_actuel


    # gros virage :
    # réaction immédiate

    if cible <= 60 or cible >= 125:

        angle_actuel = cible


    else:

        # garde la fluidité normale
        angle_actuel = angle_actuel*0.6 + cible*0.4


    servos.set_angle(
        0,
        round(angle_actuel,1)
    )



print("START")


tourner(CENTRE)

robot.set_motor(1,30)

time.sleep(1)



try:

    while True:


        s = tracker.get_status()

        etat = (
            s["left"],
            s["middle"],
            s["right"]
        )


        print(etat)


        # =========================
        # LIGNE OK
        # =========================

        if etat == (1,1,1):

            compteur_virage = 0
            perdu_count = 0

            cible = CENTRE
            vitesse = VITESSE_LIGNE



        # =========================
        # GAUCHE
        # =========================

        elif etat == (1,1,0):

            perdu_count = 0

            compteur_virage += 1
            dernier_sens = 1

            cible = GAUCHE_LEGER
            vitesse = VITESSE_LIGNE



        elif etat == (1,0,0):

            perdu_count = 0

            compteur_virage += 1
            dernier_sens = 1


            if compteur_virage > 3:

                cible = GAUCHE_FORT
                vitesse = VITESSE_VIRAGE

            else:

                cible = 120
                vitesse = 22



        # =========================
        # DROITE
        # =========================

        elif etat == (0,1,1):

            perdu_count = 0

            compteur_virage += 1
            dernier_sens = -1

            cible = DROITE_LEGER
            vitesse = VITESSE_LIGNE



        elif etat == (0,0,1):

            perdu_count = 0

            compteur_virage += 1
            dernier_sens = -1


            # virage serré droite
            if compteur_virage > 3:

                cible = DROITE_FORT
                vitesse = VITESSE_VIRAGE

            else:

                cible = 70
                vitesse = 22



        # =========================
        # POINTILLES / PERTE LIGNE
        # =========================

        elif etat == (0,0,0):

            perdu_count += 1


            # petit trou = pointillés
            if perdu_count < 8:

                cible = CENTRE
                vitesse = VITESSE_LIGNE


            # vraie perte :
            # recherche dans dernier sens

            else:

                if dernier_sens == 1:

                    cible = GAUCHE_FORT


                elif dernier_sens == -1:

                    cible = DROITE_FORT


                else:

                    cible = CENTRE


                vitesse = VITESSE_PERDU



        tourner(cible)


        robot.set_motor(
            1,
            vitesse
        )


        time.sleep(0.025)



except KeyboardInterrupt:

    print("STOP")

    robot.stopper()

    servos.set_angle(0,CENTRE)
