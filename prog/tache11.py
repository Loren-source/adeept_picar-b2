#!/usr/bin/env python3

import time

from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker


# ==========================
# INITIALISATION
# ==========================

robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()


# ==========================
# REGLAGES
# ==========================

CENTRE = 97

# petites corrections
GAUCHE_LEGER = 112
DROITE_LEGER = 82

# vrais virages
GAUCHE_FORT = 128
DROITE_FORT = 65

# vitesses
VITESSE_LIGNE = 34
VITESSE_POINTILLE = 38
VITESSE_APPROCHE = 27
VITESSE_VIRAGE = 18
VITESSE_PERDU = 14


# ==========================
# ETATS
# ==========================

MODE_NORMAL = 0
MODE_POINTILLE = 1

etat_robot = MODE_NORMAL

angle_actuel = CENTRE
angle_pointille = CENTRE

dernier_sens = 0
# 1 = gauche
# -1 = droite

compteur_virage = 0
compteur_perdu = 0
compteur_111 = 0

dernier_etat = (1,1,1)

entree_pointille = False


# ==========================
# SERVO FLUIDE
# ==========================

def tourner(cible):

    global angle_actuel

    angle_actuel = angle_actuel * 0.6 + cible * 0.4

    servos.set_angle(
        0,
        round(angle_actuel,1)
    )


# ==========================
# START
# ==========================

print("START")

tourner(CENTRE)

robot.set_motor(1,30)

time.sleep(1)

# ==========================
# BOUCLE
# ==========================

try:

    while True:

        s = tracker.get_status()

        etat = (
            s["left"],
            s["middle"],
            s["right"]
        )

        print(etat)

        # =====================================================
        # MODE POINTILLES
        # =====================================================

        if etat_robot == MODE_POINTILLE:

            # Une seule commande servo au début
            if entree_pointille:
                tourner(angle_pointille)
                entree_pointille = False

            robot.set_motor(1, VITESSE_POINTILLE)

            # Ligne retrouvée
            if etat == (1,1,1):

                compteur_111 += 1

                if compteur_111 >= 2:

                    etat_robot = MODE_NORMAL

                    compteur_111 = 0
                    compteur_perdu = 0
                    dernier_etat = etat

            else:

                compteur_111 = 0

            # Toujours dans le blanc
            if etat == (0,0,0):

                compteur_perdu += 1

                # Sécurité : si vraiment perdu
                if compteur_perdu > 20:

                    etat_robot = MODE_NORMAL

                    compteur_perdu = 0

            else:

                compteur_perdu = 0

            time.sleep(0.025)

            continue

        # =====================================================
        # MODE NORMAL
        # =====================================================

        if etat == (1,1,1):

            compteur_virage = 0
            compteur_perdu = 0

            cible = CENTRE
            vitesse = VITESSE_LIGNE

        elif etat == (1,1,0):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = 1

            if compteur_virage > 2:

                cible = GAUCHE_FORT
                vitesse = VITESSE_VIRAGE

            else:

                cible = GAUCHE_LEGER
                vitesse = VITESSE_APPROCHE

        elif etat == (1,0,0):

            # On garde la logique qui fonctionnait
            compteur_perdu = 0
            compteur_virage += 2

            dernier_sens = 1

            cible = GAUCHE_FORT
            vitesse = VITESSE_VIRAGE

        elif etat == (0,1,1):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = -1

            if compteur_virage > 2:

                cible = DROITE_FORT
                vitesse = VITESSE_VIRAGE

            else:

                cible = DROITE_LEGER
                vitesse = VITESSE_APPROCHE


        elif etat == (0,0,1):

            # On garde la logique qui fonctionnait
            compteur_perdu = 0
            compteur_virage += 2

            dernier_sens = -1

            cible = DROITE_FORT
            vitesse = VITESSE_VIRAGE


        # =====================================
        # 000 : POINTILLES OU PERTE
        # =====================================

        elif etat == (0,0,0):

            # Les pointillés ne sont détectés
            # qu'après une vraie ligne droite.

            if dernier_etat == (1,1,1):

                etat_robot = MODE_POINTILLE

                angle_pointille = angle_actuel

                compteur_111 = 0
                compteur_perdu = 0

                entree_pointille = True

                continue

            # -----------------------------
            # Vraie perte de ligne
            # -----------------------------

            compteur_perdu += 1

            if dernier_sens == 1:

                cible = GAUCHE_FORT

            elif dernier_sens == -1:

                cible = DROITE_FORT

            else:

                cible = CENTRE

            vitesse = VITESSE_PERDU

        # =====================================
        # ACTION
        # =====================================

        tourner(cible)

        robot.set_motor(
            1,
            vitesse
        )

        # On mémorise uniquement les états où la ligne est visible.
        if etat != (0,0,0):
            dernier_etat = etat

        time.sleep(0.025)


except KeyboardInterrupt:

    print("STOP")

    robot.stopper()

    servos.set_angle(
        0,
        CENTRE
    )
