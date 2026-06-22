#!/usr/bin/env python3

import time
import sys
import RPi.GPIO as GPIO

# Fichiers Adeept
import motor
import lineTracking

# Ton fichier servo.py avec RobotServos
from servo import RobotServos


# ======================
# REGLAGES
# ======================

CENTRE = 97

# ATTENTION : corrigé avec tes logs
DROITE = 76
DROITE_MAX = 70

GAUCHE = 118
GAUCHE_MAX = 125


V_LIGNE = 35
V_VIRAGE = 28
V_RECHERCHE = 25

DELAI = 0.02


# ======================
# INIT
# ======================

servos = RobotServos()

dernier_cote = "DROITE"


# ======================
# FONCTIONS
# ======================

def tourner(angle):
    servos.set_angle(0, angle)
    print("[CH00] →", str(angle)+"°")


def avancer(angle, vitesse):

    tourner(angle)

    motor.motor_left(
        status=1,
        direction=1,
        speed=vitesse
    )

    motor.motor_right(
        status=1,
        direction=1,
        speed=vitesse
    )


def stop():

    motor.motor_left(
        status=0,
        direction=1,
        speed=0
    )

    motor.motor_right(
        status=0,
        direction=1,
        speed=0
    )


def lire_ligne():

    L = GPIO.input(lineTracking.line_pin_left)
    M = GPIO.input(lineTracking.line_pin_middle)
    R = GPIO.input(lineTracking.line_pin_right)

    return (L, M, R)



# ======================
# START
# ======================

try:

    print("START")

    tourner(CENTRE)

    while True:

        L, M, R = lire_ligne()

        print((L,M,R))


        # ====================
        # TOUT DROIT
        # ====================

        if (L,M,R) == (1,1,1):

            avancer(CENTRE, V_LIGNE)



        # ====================
        # VIRAGE DROITE
        # ====================

        elif (L,M,R) == (1,1,0):

            dernier_cote = "DROITE"
            avancer(DROITE, V_LIGNE)


        elif (L,M,R) == (1,0,0):

            dernier_cote = "DROITE"
            avancer(DROITE_MAX, V_VIRAGE)



        # ====================
        # VIRAGE GAUCHE
        # ====================

        elif (L,M,R) == (0,1,1):

            dernier_cote = "GAUCHE"
            avancer(GAUCHE, V_LIGNE)


        elif (L,M,R) == (0,0,1):

            dernier_cote = "GAUCHE"
            avancer(GAUCHE_MAX, V_VIRAGE)



        # ====================
        # LIGNE PERDUE
        # ====================

        elif (L,M,R) == (0,0,0):

            print("Recherche ligne")


            # au lieu de continuer tout droit,
            # il revient vers le dernier virage

            if dernier_cote == "DROITE":

                avancer(DROITE_MAX, V_RECHERCHE)


            else:

                avancer(GAUCHE_MAX, V_RECHERCHE)



        # autres cas
        else:

            avancer(CENTRE,25)


        time.sleep(DELAI)



except KeyboardInterrupt:

    print("FIN")

    stop()

    tourner(CENTRE)

    GPIO.cleanup()
