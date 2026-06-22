#!/usr/bin/env python3

import time
import motor
from servo import Servo
import RPi.GPIO as GPIO


# ======================
# REGLAGES
# ======================

CENTRE = 97

# valeurs testées sur ton robot
GAUCHE_LEGER = 76
GAUCHE_MAX = 70

DROITE_LEGER = 118
DROITE_MAX = 125


V_LIGNE = 35
V_VIRAGE = 45


# capteurs ligne
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


servos = Servo()

dernier_angle = None
dernier_virage = CENTRE


# ======================
# SERVO
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
# PROGRAMME PRINCIPAL
# ======================

print("START")


try:

    tourner(CENTRE)

    while True:


        gauche = GPIO.input(IR01)
        milieu = GPIO.input(IR02)
        droite = GPIO.input(IR03)


        etat = (gauche, milieu, droite)

        print(etat)



        # ==================
        # LIGNE DROITE
        # ==================

        if etat == (1,1,1):

            avance(CENTRE, V_LIGNE)

            dernier_virage = CENTRE



        # ==================
        # TOURNE DROITE
        # ==================

        elif etat == (1,1,0):

            avance(DROITE_LEGER, V_LIGNE)

            dernier_virage = DROITE_LEGER



        elif etat == (1,0,0):

            avance(DROITE_MAX, V_VIRAGE)

            dernier_virage = DROITE_MAX



        # ==================
        # TOURNE GAUCHE
        # ==================

        elif etat == (0,1,1):

            avance(GAUCHE_LEGER, V_LIGNE)

            dernier_virage = GAUCHE_LEGER



        elif etat == (0,0,1):

            avance(GAUCHE_MAX, V_VIRAGE)

            dernier_virage = GAUCHE_MAX



        # ==================
        # PERTE DE LIGNE
        # IMPORTANT POUR 2e VIRAGE
        # ==================

        elif etat == (0,0,0):

            # garde la dernière direction
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
