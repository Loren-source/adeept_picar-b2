#!/usr/bin/env python3

import time
import sys

sys.path.append('/home/loren/adeept_picar-b2/prog')

import motor
from servo import RobotServos
import lineTracking


# ==========================
# INITIALISATION
# ==========================

servos = RobotServos()


# ==========================
# REGLAGES
# ==========================

CENTRE = 97

# tes valeurs mesurées
GAUCHE_MAX = 125
DROITE_MAX = 70

GAUCHE = 118
DROITE = 76


V_LIGNE = 35
V_VIRAGE = 45

dernier_angle = CENTRE


# ==========================
# SERVO
# ==========================

def tourner(angle):
    global dernier_angle

    if angle != dernier_angle:
        servos.set_angle(0, angle)
        dernier_angle = angle


# ==========================
# MOTEURS
# ==========================

def avancer(vitesse):
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
    motor.motorStop()


# ==========================
# PROGRAMME
# ==========================

print("START")

try:

    tourner(CENTRE)
    time.sleep(1)


    while True:

        L, M, R = lineTracking.readLine()

        print((L, M, R))


        # ====================
        # MILIEU
        # ====================

        if (L, M, R) == (1,1,1):

            tourner(CENTRE)
            avancer(V_LIGNE)


        # ====================
        # PART A DROITE
        # ligne vue à gauche
        # ====================

        elif (L, M, R) == (0,1,1):

            tourner(DROITE)
            avancer(V_VIRAGE)


        elif (L, M, R) == (0,0,1):

            tourner(DROITE_MAX)
            avancer(V_VIRAGE)


        # ====================
        # PART A GAUCHE
        # ligne vue à droite
        # ====================

        elif (L, M, R) == (1,1,0):

            tourner(GAUCHE)
            avancer(V_VIRAGE)


        elif (L, M, R) == (1,0,0):

            tourner(GAUCHE_MAX)
            avancer(V_VIRAGE)


        # ====================
        # PERDU
        # garde dernier angle
        # ====================

        elif (L, M, R) == (0,0,0):

            avancer(30)


        time.sleep(0.03)



except KeyboardInterrupt:

    tourner(CENTRE)
    stop()
    print("FIN")
