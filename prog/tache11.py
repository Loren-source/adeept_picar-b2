#!/usr/bin/env python3

import time

from servo import RobotServos
from motor import RobotMotor
from line import LineTracker


# ==========================
# REGLAGES
# ==========================

CENTRE = 97

GAUCHE_LEGER = 112
GAUCHE_FORT = 125

DROITE_LEGER = 82
DROITE_FORT = 70


V_DROIT = 35
V_CORRECTION = 25
V_VIRAGE = 18
V_RECHERCHE = 12


# ==========================
# INIT
# ==========================

servos = RobotServos()
moteur = RobotMotor()
tracker = LineTracker()

dernier_angle = None
dernier_cote = CENTRE


# ==========================
# FONCTIONS
# ==========================

def tourner(angle):
    global dernier_angle

    if angle != dernier_angle:
        servos.set_angle(0, angle)
        dernier_angle = angle


def avancer(angle, vitesse):
    global dernier_cote

    tourner(angle)
    moteur.set_motor(1, vitesse)

    # on mémorise même les petits virages
    if angle < CENTRE:
        dernier_cote = DROITE_FORT

    elif angle > CENTRE:
        dernier_cote = GAUCHE_FORT



def stop():
    moteur.stopper()
    tourner(CENTRE)



# ==========================
# MAIN
# ==========================

print("START")

try:

    tourner(CENTRE)
    time.sleep(1)


    while True:

        etat = tracker.get_status()

        L = int(etat["left"])
        M = int(etat["middle"])
        R = int(etat["right"])

        print((L,M,R))


        # =====================
        # Ligne centrée
        # =====================

        if (L,M,R) == (1,1,1) or (L,M,R)==(0,1,0):

            avancer(CENTRE, V_DROIT)



        # =====================
        # La ligne part à droite
        # =====================

        elif (L,M,R) == (0,1,1):

            avancer(DROITE_LEGER, V_CORRECTION)


        elif (L,M,R) == (0,0,1):

            avancer(DROITE_FORT, V_VIRAGE)



        # =====================
        # La ligne part à gauche
        # =====================

        elif (L,M,R) == (1,1,0):

            avancer(GAUCHE_LEGER, V_CORRECTION)


        elif (L,M,R) == (1,0,0):

            avancer(GAUCHE_FORT, V_VIRAGE)



        # =====================
        # Ligne perdue
        # =====================

        elif (L,M,R) == (0,0,0):

            print("Recherche :", dernier_cote)

            tourner(dernier_cote)
            moteur.set_motor(1, V_RECHERCHE)



        # sécurité
        else:

            avancer(CENTRE,20)



        time.sleep(0.03)



except KeyboardInterrupt:

    print("STOP")
    stop()
