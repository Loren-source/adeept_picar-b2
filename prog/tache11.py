#!/usr/bin/env python3

import time
import motor
from servo import servo
import RPi.GPIO as GPIO


# ======================
# REGLAGES ROBOT
# ======================

CENTRE = 97

# angles mesurés sur ton robot
GAUCHE_LEGER = 76
GAUCHE_MAX = 70

DROITE_LEGER = 118
DROITE_MAX = 125


# vitesses
V_LIGNE = 35
V_VIRAGE = 45


# capteurs infrarouges
IR01 = 14   # gauche
IR02 = 15   # milieu
IR03 = 23   # droite


# ======================
# INITIALISATION
# ======================

GPIO.setmode(GPIO.BCM)

GPIO.setup(IR01, GPIO.IN)
GPIO.setup(IR02, GPIO.IN)
GPIO.setup(IR03, GPIO.IN)


# création objet servo
servos = servo()


dernier_angle = None
dernier_virage = CENTRE



# ======================
# DIRECTION
# ======================

def tourner(angle):

    global dernier_angle

    if dernier_angle != angle:

        servos.set_angle(0, angle)

        print("[CH00] →", angle, "°")

        dernier_angle = angle



# ======================
# MOTEURS
# ======================

def avance(angle, vitesse):

    tourner(angle)

    motor.motor_left(1, 0, vitesse)
    motor.motor_right(1, 0, vitesse)



def stop():

    motor.motorStop()



# ======================
# MAIN
# ======================

print("START")


try:

    tourner(CENTRE)


    while True:


        G = GPIO.input(IR01)
        M = GPIO.input(IR02)
        D = GPIO.input(IR03)


        etat = (G, M, D)

        print(etat)



        # =========================
        # TOUT VA BIEN
        # =========================

        if etat == (1,1,1):

            avance(CENTRE, V_LIGNE)



        # =========================
        # CORRECTION DROITE
        # =========================

        elif etat == (1,1,0):

            avance(DROITE_LEGER, V_LIGNE)

            dernier_virage = DROITE_LEGER



        elif etat == (1,0,0):

            avance(DROITE_MAX, V_VIRAGE)

            dernier_virage = DROITE_MAX



        # =========================
        # CORRECTION GAUCHE
        # =========================

        elif etat == (0,1,1):

            avance(GAUCHE_LEGER, V_LIGNE)

            dernier_virage = GAUCHE_LEGER



        elif etat == (0,0,1):

            avance(GAUCHE_MAX, V_VIRAGE)

            dernier_virage = GAUCHE_MAX



        # =========================
        # PERTE DE LIGNE
        # cas du 2e virage
        # =========================

        elif etat == (0,0,0):

            # NE PAS remettre droit
            # continuer le dernier virage

            tourner(dernier_virage)

            motor.motor_left(1,0,35)
            motor.motor_right(1,0,35)



        time.sleep(0.03)




except KeyboardInterrupt:


    tourner(CENTRE)

    stop()

    GPIO.cleanup()

    servos.fermer()

    print("FIN")
