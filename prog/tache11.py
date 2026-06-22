#!/usr/bin/env python3

import time
import motor
import servo
import RPi.GPIO as GPIO


# ======================
# REGLAGES
# ======================

CENTRE = 97

GAUCHE_LEGER = 76
GAUCHE_MAX = 70

DROITE_LEGER = 118
DROITE_MAX = 125

V_LIGNE = 35
V_VIRAGE = 45


# capteurs ligne
IR01 = 14
IR02 = 15
IR03 = 23


# ======================
# INIT
# ======================

GPIO.setmode(GPIO.BCM)

GPIO.setup(IR01, GPIO.IN)
GPIO.setup(IR02, GPIO.IN)
GPIO.setup(IR03, GPIO.IN)


dernier_angle = None
dernier_virage = CENTRE


# ======================
# SERVO
# ======================

def tourner(angle):

    global dernier_angle

    if dernier_angle != angle:

        servo.set_angle(0, angle)

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


        # ligne droite
        if etat == (1,1,1):

            avance(CENTRE, V_LIGNE)



        # droite légère
        elif etat == (1,1,0):

            dernier_virage = DROITE_LEGER

            avance(DROITE_LEGER, V_LIGNE)



        # gros virage droite
        elif etat == (1,0,0):

            dernier_virage = DROITE_MAX

            avance(DROITE_MAX, V_VIRAGE)



        # gauche légère
        elif etat == (0,1,1):

            dernier_virage = GAUCHE_LEGER

            avance(GAUCHE_LEGER, V_LIGNE)



        # gros virage gauche
        elif etat == (0,0,1):

            dernier_virage = GAUCHE_MAX

            avance(GAUCHE_MAX, V_VIRAGE)



        # perte de ligne
        elif etat == (0,0,0):

            # garde le virage précédent
            tourner(dernier_virage)

            motor.motor_left(1,0,35)
            motor.motor_right(1,0,35)



        time.sleep(0.03)



except KeyboardInterrupt:

    tourner(CENTRE)

    stop()

    GPIO.cleanup()

    print("FIN")
