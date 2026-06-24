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
# REGLAGES PICAR-B
# ==========================

CENTRE = 97

# Sur ton robot :
# >97 = gauche
# <97 = droite

GAUCHE_LEGER = 104
GAUCHE_FORT = 112

DROITE_LEGER = 90
DROITE_FORT = 82


VITESSE_LIGNE = 35
VITESSE_VIRAGE = 25
VITESSE_PERDU = 18


angle_actuel = CENTRE
dernier_angle = CENTRE


# ==========================
# DIRECTION FLUIDE
# ==========================

def tourner(cible):

    global angle_actuel

    # filtre anti zig-zag
    angle_actuel = angle_actuel * 0.65 + cible * 0.35

    servos.set_angle(
        0,
        round(angle_actuel, 1)
    )


# ==========================
# DEMARRAGE
# ==========================

print("START")

tourner(CENTRE)

robot.set_motor(1, 30)

time.sleep(1)



# ==========================
# SUIVI DE LIGNE
# ==========================

try:

    while True:

        data = tracker.get_status()

        L = data["left"]
        M = data["middle"]
        R = data["right"]


        etat = (L, M, R)

        print(etat)


        # ======================
        # BIEN SUR LA LIGNE
        # ======================

        if etat == (1,1,1):

            cible = CENTRE
            vitesse = VITESSE_LIGNE



        # ======================
        # ROBOT TROP A GAUCHE
        # corriger vers DROITE
        # ======================

        elif etat == (0,1,1):

            cible = DROITE_LEGER
            vitesse = VITESSE_LIGNE



        elif etat == (0,0,1):

            cible = DROITE_FORT
            vitesse = VITESSE_VIRAGE



        # ======================
        # ROBOT TROP A DROITE
        # corriger vers GAUCHE
        # ======================

        elif etat == (1,1,0):

            cible = GAUCHE_LEGER
            vitesse = VITESSE_LIGNE



        elif etat == (1,0,0):

            cible = GAUCHE_FORT
            vitesse = VITESSE_VIRAGE



        # ======================
        # PERDU
        # ======================

        elif etat == (0,0,0):

            # seulement ici on utilise la mémoire

            cible = dernier_angle
            vitesse = VITESSE_PERDU



        tourner(cible)


        robot.set_motor(
            1,
            vitesse
        )


        # sauvegarde uniquement une vraie direction

        if etat != (0,0,0):

            dernier_angle = cible



        time.sleep(0.025)




except KeyboardInterrupt:

    print("STOP")

    robot.stopper()

    servos.set_angle(0, CENTRE)
