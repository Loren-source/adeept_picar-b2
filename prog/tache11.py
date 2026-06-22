#!/usr/bin/env python3

import time
import sys

sys.path.append('/home/loren/adeept_picar-b2/server')

import motor
import servos
import RPi.GPIO as GPIO


# ======================
# REGLAGES
# ======================

ANGLE_CENTRE = 97

GAUCHE_MAX = 125
DROITE_MAX = 70

GAUCHE = 118
DROITE = 76

RETOUR_G = 108
RETOUR_D = 86


VITESSE_DROITE = 28
VITESSE_CORRECTION = 20
VITESSE_VIRAGE = 13
VITESSE_RECHERCHE = 12


# tes capteurs
CAP_G = 20
CAP_M = 16
CAP_D = 19


GPIO.setmode(GPIO.BCM)

for pin in [CAP_G, CAP_M, CAP_D]:
    GPIO.setup(pin, GPIO.IN)


dernier_angle = None
derniere_direction = "centre"


# ======================
# FONCTIONS
# ======================

def tourner(a):

    global dernier_angle

    if dernier_angle != a:

        servos.set_angle(0,a)

        print("[CH00] →",a,"°")

        dernier_angle = a



def avance(angle,vitesse):

    tourner(angle)

    motor.motor_left(1, vitesse)
    motor.motor_right(1, vitesse)



def lire():

    return (
        GPIO.input(CAP_G),
        GPIO.input(CAP_M),
        GPIO.input(CAP_D)
    )



# ======================
# MAIN
# ======================

try:

    print("START")


    while True:


        cap = lire()

        print(cap)



        # ligne OK

        if cap == (1,1,1):


            if derniere_direction=="gauche":

                avance(RETOUR_G,VITESSE_CORRECTION)
                time.sleep(0.15)


            elif derniere_direction=="droite":

                avance(RETOUR_D,VITESSE_CORRECTION)
                time.sleep(0.15)


            derniere_direction="centre"

            avance(ANGLE_CENTRE,VITESSE_DROITE)




        # commence à partir à gauche

        elif cap == (1,1,0):

            derniere_direction="gauche"

            avance(GAUCHE,VITESSE_CORRECTION)



        # gros virage gauche

        elif cap == (1,0,0):

            derniere_direction="gauche"

            avance(GAUCHE_MAX,VITESSE_VIRAGE)

            time.sleep(0.25)




        # commence à partir droite

        elif cap == (0,1,1):

            derniere_direction="droite"

            avance(DROITE,VITESSE_CORRECTION)




        # gros virage droite

        elif cap == (0,0,1):

            derniere_direction="droite"

            avance(DROITE_MAX,VITESSE_VIRAGE)

            time.sleep(0.25)




        # perdu

        elif cap == (0,0,0):


            if derniere_direction=="gauche":

                avance(GAUCHE_MAX,VITESSE_RECHERCHE)


            elif derniere_direction=="droite":

                avance(DROITE_MAX,VITESSE_RECHERCHE)


            else:

                avance(ANGLE_CENTRE,VITESSE_RECHERCHE)



        time.sleep(0.03)




except KeyboardInterrupt:


    servos.set_angle(0,97)

    motor.motorStop()

    print("FIN")
