#!/usr/bin/env python3

import time

from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker


# ==========================
# INITIALISATION
# ==========================

robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()


# ==========================
# REGLAGES ADEEPT PICAR-B
# ==========================

CENTRE = 97

# ton montage :
# angle > 97 = gauche
# angle < 97 = droite

MAX_CORRECTION = 25


VITESSE_DROITE = 42
VITESSE_VIRAGE = 28
VITESSE_PERDU = 20


angle_actuel = CENTRE
correction = 0


# ==========================
# OUTILS
# ==========================

def limite(x, mini, maxi):
    return max(mini, min(maxi, x))


def tourner(cible):

    global angle_actuel

    # plus réactif que l'ancien
    angle_actuel = angle_actuel * 0.65 + cible * 0.35

    servos.set_angle(
        0,
        round(angle_actuel, 1)
    )



# ==========================
# START
# ==========================

print("START")

tourner(CENTRE)

robot.set_motor(1, 30)

time.sleep(1)



# ==========================
# BOUCLE PRINCIPALE
# ==========================

try:

    while True:


        data = tracker.get_status()


        L = data["left"]
        M = data["middle"]
        R = data["right"]


        etat = (L, M, R)

        print(etat)


        # ==================================
        # PARFAITEMENT SUR LA LIGNE NOIRE
        # ==================================

        if etat == (1,1,1):

            # sortie de virage :
            # revenir rapidement au centre

            if abs(correction) > 15:

                correction *= 0.45

            else:

                correction *= 0.8


            vitesse = VITESSE_DROITE



        # ==================================
        # ROBOT TROP A GAUCHE
        # il faut tourner DROITE
        # donc angle diminue
        # ==================================

        elif etat == (0,1,1):

            correction -= 3

            vitesse = VITESSE_DROITE



        elif etat == (0,0,1):

            correction -= 7

            vitesse = VITESSE_VIRAGE



        # ==================================
        # ROBOT TROP A DROITE
        # il faut tourner GAUCHE
        # donc angle augmente
        # ==================================

        elif etat == (1,1,0):

            correction += 3

            vitesse = VITESSE_DROITE



        elif etat == (1,0,0):

            correction += 7

            vitesse = VITESSE_VIRAGE



        # ==================================
        # PERTE COMPLETE DE LA LIGNE
        # ==================================

        elif etat == (0,0,0):

            # continuer la dernière recherche
            # mais doucement

            if correction > 0:

                correction += 3

            else:

                correction -= 3


            vitesse = VITESSE_PERDU



        # sécurité servo

        correction = limite(
            correction,
            -MAX_CORRECTION,
            MAX_CORRECTION
        )


        angle_final = CENTRE + correction


        tourner(angle_final)


        robot.set_motor(
            1,
            vitesse
        )


        time.sleep(0.03)



except KeyboardInterrupt:

    print("STOP")

    robot.stopper()

    servos.set_angle(0, CENTRE)
