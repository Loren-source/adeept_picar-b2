#!/usr/bin/env python3

import time

from servo import RobotServos
from motor import RobotMotor
from lineTracking import LineTracker


# =====================
# REGLAGES
# =====================

CENTRE = 97

# tes vraies limites testées
GAUCHE_MAX = 125
DROITE_MAX = 70

GAUCHE = 118
DROITE = 76

V_LIGNE = 35
V_VIRAGE = 28


# =====================
# INITIALISATION
# =====================

servos = RobotServos()
moteur = RobotMotor()
tracker = LineTracker()

dernier_angle = CENTRE


def tourner(angle):
    global dernier_angle

    if angle != dernier_angle:
        servos.set_angle(0, angle)
        dernier_angle = angle


def avancer(angle, vitesse):
    tourner(angle)
    moteur.set_motor(1, vitesse)


def stop():
    moteur.stopper()
    tourner(CENTRE)


print("START")


try:

    tourner(CENTRE)
    time.sleep(1)

    while True:

        s = tracker.get_status()

        L = int(s["left"])
        M = int(s["middle"])
        R = int(s["right"])

        print((L, M, R))


        # ==========================
        # LIGNE AU MILIEU
        # ==========================

        if (L, M, R) == (1,1,1):

            avancer(CENTRE, V_LIGNE)


        # ==========================
        # PETITE CORRECTION GAUCHE
        # ==========================

        elif (L, M, R) == (0,1,1):

            avancer(DROITE, V_LIGNE)


        elif (L, M, R) == (0,0,1):

            # gros virage droite
            avancer(DROITE_MAX, V_VIRAGE)


        # ==========================
        # PETITE CORRECTION DROITE
        # ==========================

        elif (L, M, R) == (1,1,0):

            avancer(GAUCHE, V_LIGNE)


        elif (L, M, R) == (1,0,0):

            # gros virage gauche
            avancer(GAUCHE_MAX, V_VIRAGE)


        # ==========================
        # PERTE DE LIGNE
        # ==========================

        elif (L,M,R) == (0,0,0):

            # NE PLUS FONCER TOUT DROIT
            # il garde le dernier angle
            moteur.set_motor(1,20)


        else:

            avancer(CENTRE,25)


        time.sleep(0.04)



except KeyboardInterrupt:

    print("FIN")
    stop()
