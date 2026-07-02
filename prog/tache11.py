#!/usr/bin/env python3

import time

from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker


robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()


# ==========================
# REGLAGES VALIDES
# ==========================

CENTRE = 97

# petites corrections
GAUCHE_LEGER = 112
DROITE_LEGER = 82

# vrais virages
GAUCHE_FORT = 128
DROITE_FORT = 55

# vitesses
VITESSE_LIGNE = 40
VITESSE_APPROCHE = 27
VITESSE_VIRAGE = 19
VITESSE_PERDU = 14
VITESSE_POINTILLE = 28          # <-- NOUVEAU : vitesse pour traverser les pointillés

# seuil pour pointillés (cycles)
SEUIL_POINTILLE = 15            # <-- NOUVEAU : 15 * 25 ms = 375 ms

angle_actuel = CENTRE
dernier_sens = 0                # 1 = gauche, -1 = droite
compteur_virage = 0
dernier_etat = (1,1,1)
compteur_perdu = 0
derniere_cible = CENTRE         # <-- NOUVEAU : mémorise la dernière cible calculée


# ==========================
# SERVO FLUIDE
# ==========================

def tourner(cible):
    global angle_actuel
    angle_actuel = angle_actuel * 0.6 + cible * 0.4
    servos.set_angle(0, round(angle_actuel, 1))


# ==========================
# START
# ==========================

print("START")
tourner(CENTRE)
robot.set_motor(1, 30)
time.sleep(1)


# ==========================
# BOUCLE
# ==========================

try:
    while True:
        s = tracker.get_status()
        etat = (s["left"], s["middle"], s["right"])
        print(etat)

        # =====================
        # LIGNE CENTREE
        # =====================
        if etat == (1,1,1):
            compteur_virage = 0
            compteur_perdu = 0
            cible = CENTRE
            vitesse = VITESSE_LIGNE
            derniere_cible = cible   # <-- mémorisation

        # =====================
        # VIRAGE GAUCHE
        # =====================
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
            derniere_cible = cible

        elif etat == (1,0,0):
            compteur_perdu = 0
            compteur_virage += 2
            dernier_sens = 1
            cible = GAUCHE_FORT
            vitesse = VITESSE_VIRAGE
            derniere_cible = cible

        # =====================
        # VIRAGE DROITE
        # =====================
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
            derniere_cible = cible

        elif etat == (0,0,1):
            compteur_perdu = 0
            compteur_virage += 2
            dernier_sens = -1
            cible = DROITE_FORT
            vitesse = VITESSE_VIRAGE
            derniere_cible = cible

        # =====================
        # POINTILLES OU PERTE
        # =====================
        elif etat == (0,0,0):
            compteur_perdu += 1

            # --- NOUVEAU : pointillé ---
            if compteur_perdu < SEUIL_POINTILLE:
                # on garde la dernière cible (même si on était en virage)
                cible = derniere_cible
                vitesse = VITESSE_POINTILLE
            else:
                # perte réelle : on cherche
                if dernier_sens == 1:
                    cible = GAUCHE_FORT
                elif dernier_sens == -1:
                    cible = DROITE_FORT
                else:
                    cible = CENTRE
                vitesse = VITESSE_PERDU

        # =====================
        # ACTION
        # =====================
        tourner(cible)
        robot.set_motor(1, vitesse)

        # mémoire dernière ligne vue (ne pas oublier)
        if etat != (0,0,0):
            dernier_etat = etat

        time.sleep(0.025)


except KeyboardInterrupt:
    print("STOP")
    robot.stopper()
    servos.set_angle(0, CENTRE)
