#!/usr/bin/env python3

import time

from motor import RobotMotor
from servo import RobotServos
from line import LineTracker


# ==========================
# INITIALISATION
# ==========================

robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()


# ==========================
# REGLAGES
# ==========================

CENTRE = 97


# à inverser si le robot tourne à l'envers
GAUCHE_MAX = 55
DROITE_MAX = 140


# vitesse
VITESSE_LIGNE = 45
VITESSE_COURBE = 35
VITESSE_RECHERCHE = 25


angle_actuel = CENTRE


# mémoire direction
correction = 0

# - : gauche
# + : droite


# ==========================
# SERVO FLUIDE
# ==========================

def direction(angle):

    global angle_actuel

    # filtre anti-coup
    angle_actuel = angle_actuel * 0.7 + angle * 0.3

    servos.set_angle(0, angle_actuel)



# ==========================
# LIMITATION
# ==========================

def limite(valeur, mini, maxi):

    return max(mini, min(maxi, valeur))



# ==========================
# DEMARRAGE
# ==========================

print("START")

direction(CENTRE)

robot.set_motor(1,30)

time.sleep(1)



# ==========================
# BOUCLE
# ==========================

try:

    while True:


        capteur = tracker.get_status()


        L = capteur["left"]
        M = capteur["middle"]
        R = capteur["right"]


        etat = (L,M,R)


        print(etat)


        # ======================
        # ligne parfaite
        # ======================

        if etat == (1,1,1):

            # on réduit doucement la correction
            # mais pas immédiatement
            correction *= 0.85

            vitesse = VITESSE_LIGNE



        # ======================
        # robot trop à DROITE
        # capteur droit voit blanc
        # tourner GAUCHE
        # ======================


        elif etat == (1,1,0):

            correction -= 12

            vitesse = VITESSE_COURBE



        elif etat == (1,0,0):

            correction -= 25

            vitesse = VITESSE_RECHERCHE



        # ======================
        # robot trop à GAUCHE
        # capteur gauche voit blanc
        # tourner DROITE
        # ======================


        elif etat == (0,1,1):

            correction += 12

            vitesse = VITESSE_COURBE



        elif etat == (0,0,1):

            correction += 25

            vitesse = VITESSE_RECHERCHE



        # ======================
        # perdu
        # ======================

        elif etat == (0,0,0):

            # continuer dernière recherche

            if correction > 0:
                correction += 8

            else:
                correction -= 8


            vitesse = 22



        # sécurité angle

        correction = limite(
            correction,
            -42,
            42
        )


        nouvel_angle = CENTRE + correction


        direction(nouvel_angle)


        robot.set_motor(
            1,
            vitesse
        )


        time.sleep(0.02)




except KeyboardInterrupt:

    print("STOP")

    robot.stopper()

    servos.set_angle(0,CENTRE)
