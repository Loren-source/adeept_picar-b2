#!/usr/bin/env python3

import time
import sys

sys.path.append('/home/loren/adeept_picar-b2/server')

import motor
import servo
import RPi.GPIO as GPIO


# ======================
# REGLAGES
# ======================

CENTRE = 97

GAUCHE_MAX = 125
DROITE_MAX = 70

GAUCHE = 118
DROITE = 76

RETOUR_G = 108
RETOUR_D = 86


V_DROITE = 28
V_CORRECTION = 20
V_VIRAGE = 13
V_RECHERCHE = 12


CAP_G = 20
CAP_M = 16
CAP_D = 19


GPIO.setmode(GPIO.BCM)

for p in [CAP_G,CAP_M,CAP_D]:
    GPIO.setup(p, GPIO.IN)



dernier_angle = None
derniere_direction = "centre"



def tourner(a):

    global dernier_angle

    if dernier_angle != a:

        servo.setServoAngle(0,a)

        print("[CH00] →",a,"°")

        dernier_angle=a



def avance(angle,vitesse):

    tourner(angle)

    motor.motor_left(1,vitesse)
    motor.motor_right(1,vitesse)



def lire():

    return (
        GPIO.input(CAP_G),
        GPIO.input(CAP_M),
        GPIO.input(CAP_D)
    )




try:

    print("START")


    while True:


        cap=lire()

        print(cap)



        # ligne droite

        if cap==(1,1,1):


            if derniere_direction=="gauche":

                avance(RETOUR_G,V_CORRECTION)
                time.sleep(0.15)


            elif derniere_direction=="droite":

                avance(RETOUR_D,V_CORRECTION)
                time.sleep(0.15)



            derniere_direction="centre"

            avance(CENTRE,V_DROITE)



        # gauche léger

        elif cap==(1,1,0):

            derniere_direction="gauche"

            avance(GAUCHE,V_CORRECTION)



        # gros gauche

        elif cap==(1,0,0):

            derniere_direction="gauche"

            avance(GAUCHE_MAX,V_VIRAGE)

            time.sleep(0.3)




        # droite léger

        elif cap==(0,1,1):

            derniere_direction="droite"

            avance(DROITE,V_CORRECTION)




        # gros droite

        elif cap==(0,0,1):

            derniere_direction="droite"

            avance(DROITE_MAX,V_VIRAGE)

            time.sleep(0.3)




        # ligne perdue

        elif cap==(0,0,0):


            if derniere_direction=="gauche":

                avance(GAUCHE_MAX,V_RECHERCHE)


            elif derniere_direction=="droite":

                avance(DROITE_MAX,V_RECHERCHE)


            else:

                avance(CENTRE,V_RECHERCHE)



        time.sleep(0.03)




except KeyboardInterrupt:


    tourner(97)

    motor.motorStop()

    print("FIN")
