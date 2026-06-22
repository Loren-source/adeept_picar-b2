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


# création objet depuis la classe servo
servos = servo.servo()


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
# MOTEUR
# ======================

def avance(angle, vitesse):

    tourner(angle)

    motor.motor_left(1,0,vitesse)
    motor.motor_right(1,0,vitesse)



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


        etat = (G,M,D)

        print(etat)



        # DROIT
        if etat == (1,1,1):

            avance(CENTRE,V_LIGNE)



        # DROITE
        elif etat == (1,1,0):

            dernier_virage = DROITE_LEGER

            avance(DROITE_LEGER,V_LIGNE)



        elif etat == (1,0,0):

            dernier_virage = DROITE_MAX

            avance(DROITE_MAX,V_VIRAGE)



        # GAUCHE
        elif etat == (0,1,1):

            dernier_virage = GAUCHE_LEGER

            avance(GAUCHE_LEGER,V_LIGNE)



        elif etat == (0,0,1):

            dernier_virage = GAUCHE_MAX

            avance(GAUCHE_MAX,V_VIRAGE)



        # PERDU
        elif etat == (0,0,0):

            # garde la direction du virage
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
