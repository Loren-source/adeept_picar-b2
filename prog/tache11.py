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


GPIO.setmode(GPIO.BCM)

GPIO.setup(IR01, GPIO.IN)
GPIO.setup(IR02, GPIO.IN)
GPIO.setup(IR03, GPIO.IN)


dernier_angle = None


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
# MOTEUR
# ======================

def avance(angle, vitesse):

    tourner(angle)

    motor.motor_left(1, 0, vitesse)
    motor.motor_right(1, 0, vitesse)



def stop():

    motor.motorStop()



# ======================
# PROGRAMME
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


        # =====================
        # LIGNE DROITE
        # =====================

        if etat == (1,1,1):

            avance(CENTRE, V_LIGNE)



        # =====================
        # PART TROP A GAUCHE
        # correction droite
        # =====================

        elif etat == (1,1,0):

            avance(DROITE_LEGER, V_LIGNE)


        elif etat == (1,0,0):

            # gros virage droite
            avance(DROITE_MAX, V_VIRAGE)



        # =====================
        # PART TROP A DROITE
        # correction gauche
        # =====================

        elif etat == (0,1,1):

            avance(GAUCHE_LEGER, V_LIGNE)


        elif etat == (0,0,1):

            # gros virage gauche
            avance(GAUCHE_MAX, V_VIRAGE)



        # =====================
        # PERTE LIGNE
        # garde le dernier angle
        # =====================

        elif etat == (0,0,0):

            # avance doucement au lieu de partir tout droit
            motor.motor_left(1,0,25)
            motor.motor_right(1,0,25)


        else:

            avance(CENTRE,30)


        time.sleep(0.03)



except KeyboardInterrupt:

    tourner(CENTRE)

    stop()

    GPIO.cleanup()

    print("FIN")
