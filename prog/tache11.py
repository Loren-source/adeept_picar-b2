#!/usr/bin/env python3

from gpiozero import Robot, DigitalInputDevice
from adafruit_servokit import ServoKit
import time


# ======================
# MOTEURS
# ======================

robot = Robot(
    left=(22, 27),
    right=(24, 23)
)


# ======================
# SERVO PCA9685
# ======================

kit = ServoKit(channels=16)

CH_SERVO = 0

ANGLE_CENTRE = 97
ANGLE_GAUCHE = 84
ANGLE_GAUCHE_FORT = 70

ANGLE_DROITE = 110
ANGLE_DROITE_FORT = 125


def direction(angle):
    kit.servo[CH_SERVO].angle = angle
    print(f"[CH00] → {angle}°")


# ======================
# CAPTEURS LIGNE
# ======================

capteur_gauche = DigitalInputDevice(17)
capteur_milieu = DigitalInputDevice(18)
capteur_droite = DigitalInputDevice(19)


def lire_capteurs():
    return (
        capteur_gauche.value,
        capteur_milieu.value,
        capteur_droite.value
    )


# ======================
# VITESSES
# ======================

VITESSE_DROITE = 35
VITESSE_CORRECTION = 32
VITESSE_VIRAGE = 25
VITESSE_RECHERCHE = 25


def avance(angle, vitesse):

    direction(angle)

    v = vitesse / 100

    robot.forward(v)


# ======================
# PROGRAMME
# ======================

print("START")

direction(ANGLE_CENTRE)

derniere_direction = None

compteur_gauche = 0
compteur_droite = 0


try:

    while True:

        cap = lire_capteurs()

        print(cap)


        # ======================
        # TOUT DROIT
        # ======================

        if cap == (1,1,1):

            compteur_gauche = 0
            compteur_droite = 0

            avance(
                ANGLE_CENTRE,
                VITESSE_DROITE
            )


        # ======================
        # PART À GAUCHE
        # ======================

        elif cap == (0,1,1):

            compteur_gauche += 1
            compteur_droite = 0

            derniere_direction = "gauche"


            if compteur_gauche > 1:

                avance(
                    ANGLE_GAUCHE_FORT,
                    VITESSE_VIRAGE
                )

            else:

                avance(
                    ANGLE_GAUCHE,
                    VITESSE_CORRECTION
                )


        # ======================
        # PART À DROITE
        # ======================

        elif cap == (1,1,0):

            compteur_droite += 1
            compteur_gauche = 0

            derniere_direction = "droite"


            if compteur_droite > 1:

                avance(
                    ANGLE_DROITE_FORT,
                    VITESSE_VIRAGE
                )

            else:

                avance(
                    ANGLE_DROITE,
                    VITESSE_CORRECTION
                )


        # ======================
        # GROS VIRAGE GAUCHE
        # ======================

        elif cap == (0,0,1):

            derniere_direction = "gauche"

            avance(
                ANGLE_GAUCHE_FORT,
                VITESSE_VIRAGE
            )


        # ======================
        # GROS VIRAGE DROITE
        # ======================

        elif cap == (1,0,0):

            derniere_direction = "droite"

            avance(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )


        # ======================
        # PERTE DE LIGNE
        # ======================

        elif cap == (0,0,0):

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

                robot.stop()


        time.sleep(0.03)



except KeyboardInterrupt:

    print("FIN")

    robot.stop()

    direction(ANGLE_CENTRE)
