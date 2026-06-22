#!/usr/bin/env python3

import time

from servo import RobotServos
from motor import RobotMotor
from lineTracking import LineTracker


# ==========================
# REGLAGES
# ==========================

CENTRE = 97

# angles calibrés avec tes tests
GAUCHE_MAX = 125
DROITE_MAX = 70

GAUCHE = 118
DROITE = 76


# vitesses
V_LIGNE = 32
V_VIRAGE = 18
V_RECHERCHE = 10


# ==========================
# INITIALISATION
# ==========================

servos = RobotServos()
moteur = RobotMotor()
tracker = LineTracker()


dernier_angle = None
dernier_virage = CENTRE


# ==========================
# FONCTIONS
# ==========================

def tourner(angle):
    global dernier_angle

    if angle != dernier_angle:
        servos.set_angle(0, angle)
        dernier_angle = angle


def avancer(angle, vitesse):
    global dernier_virage

    tourner(angle)

    # mémorise uniquement les vrais virages
    if angle == GAUCHE_MAX or angle == DROITE_MAX:
        dernier_virage = angle

    moteur.set_motor(1, vitesse)



def stop():
    moteur.stopper()
    tourner(CENTRE)



# ==========================
# PROGRAMME PRINCIPAL
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

        print((L, M, R))


        # ==================
        # TOUT DROIT
        # ==================

        if (L,M,R) == (1,1,1):

            avancer(CENTRE, V_LIGNE)



        # ==================
        # VIRAGE DROITE
        # ==================

        elif (L,M,R) == (0,1,1):

            # commence à droite
            avancer(DROITE, V_LIGNE)


        elif (L,M,R) == (0,0,1):

            # gros virage droite
            avancer(DROITE_MAX, V_VIRAGE)



        # ==================
        # VIRAGE GAUCHE
        # ==================

        elif (L,M,R) == (1,1,0):

            avancer(GAUCHE, V_LIGNE)


        elif (L,M,R) == (1,0,0):

            avancer(GAUCHE_MAX, V_VIRAGE)



        # ==================
        # LIGNE PERDUE
        # ==================

        elif (L,M,R) == (0,0,0):

            print("Recherche ligne")

            # continue le dernier virage connu
            tourner(dernier_virage)

            # avance doucement pour retrouver
            moteur.set_motor(1, V_RECHERCHE)



        else:

            avancer(CENTRE,20)



        time.sleep(0.04)



except KeyboardInterrupt:

    print("FIN")

    stop()
