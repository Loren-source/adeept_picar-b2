#!/usr/bin/env python3

import time
import sys

sys.path.append('/home/loren/adeept_picar-b2/server')

import move
import RPIservo

# =========================
# REGLAGES
# =========================

ANGLE_CENTRE = 97

# ton calibrage :
ANGLE_GAUCHE_MAX = 125
ANGLE_DROITE_MAX = 70

ANGLE_GAUCHE_LEGER = 118
ANGLE_DROITE_LEGER = 76

# retour progressif
RETOUR_GAUCHE = 108
RETOUR_DROITE = 86


VITESSE_DROITE = 28
VITESSE_CORRECTION = 20
VITESSE_VIRAGE = 13
VITESSE_RECHERCHE = 12


# capteurs IR
capteurs = [20, 16, 19]


servo = RPIservo.ServoCtrl()
servo.start()


dernier_angle = -1
derniere_direction = "centre"


# =========================
# FONCTIONS
# =========================

def angle(a):
    global dernier_angle

    if a != dernier_angle:
        servo.setServoAngle(0, a)
        print("[CH00] → " + str(a) + "°")
        dernier_angle = a


def avance(a, vitesse):

    angle(a)

    move.move(
        vitesse,
        'forward',
        'no',
        0.8
    )


def lire():

    import RPi.GPIO as GPIO

    valeurs = []

    for c in capteurs:
        valeurs.append(GPIO.input(c))

    return tuple(valeurs)



# =========================
# PROGRAMME
# =========================

try:

    print("START")

    while True:

        cap = lire()

        print(cap)


        # =====================
        # LIGNE AU CENTRE
        # =====================
        
        if cap == (1,1,1):

            # sortie de virage gauche
            if derniere_direction == "gauche":

                avance(
                    RETOUR_GAUCHE,
                    VITESSE_CORRECTION
                )

                time.sleep(0.15)


            # sortie de virage droite
            elif derniere_direction == "droite":

                avance(
                    RETOUR_DROITE,
                    VITESSE_CORRECTION
                )

                time.sleep(0.15)


            derniere_direction = "centre"


            avance(
                ANGLE_CENTRE,
                VITESSE_DROITE
            )



        # =====================
        # CORRECTION GAUCHE
        # =====================

        elif cap == (1,1,0):

            derniere_direction = "gauche"

            avance(
                ANGLE_GAUCHE_LEGER,
                VITESSE_CORRECTION
            )



        # gros virage gauche

        elif cap == (1,0,0):

            derniere_direction = "gauche"

            avance(
                ANGLE_GAUCHE_MAX,
                VITESSE_VIRAGE
            )

            time.sleep(0.2)



        # =====================
        # CORRECTION DROITE
        # =====================

        elif cap == (0,1,1):

            derniere_direction = "droite"

            avance(
                ANGLE_DROITE_LEGER,
                VITESSE_CORRECTION
            )



        # gros virage droite

        elif cap == (0,0,1):

            derniere_direction = "droite"

            avance(
                ANGLE_DROITE_MAX,
                VITESSE_VIRAGE
            )

            time.sleep(0.2)



        # =====================
        # PERTE DE LIGNE
        # =====================

        elif cap == (0,0,0):

            # cherche du côté du dernier virage

            if derniere_direction == "gauche":

                avance(
                    ANGLE_GAUCHE_MAX,
                    VITESSE_RECHERCHE
                )

            elif derniere_direction == "droite":

                avance(
                    ANGLE_DROITE_MAX,
                    VITESSE_RECHERCHE
                )

            else:

                avance(
                    ANGLE_CENTRE,
                    VITESSE_RECHERCHE
                )


        time.sleep(0.03)



except KeyboardInterrupt:

    angle(ANGLE_CENTRE)

    move.motorStop()

    print("FIN")
