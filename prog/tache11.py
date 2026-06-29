#!/usr/bin/env python3

import time

from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker


robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()


# ==========================
# REGLAGES VALIDES (inchangés)
# ==========================

CENTRE = 97

GAUCHE_LEGER = 112
DROITE_LEGER = 82

GAUCHE_FORT = 128
DROITE_FORT = 65

VITESSE_LIGNE = 34
VITESSE_APPROCHE = 27
VITESSE_VIRAGE = 18
VITESSE_PERDU = 14

angle_actuel = CENTRE

dernier_sens = 0
# 1 = gauche, -1 = droite

compteur_virage = 0
dernier_etat = (1, 1, 1)
compteur_perdu = 0

# ==========================
# NOUVEAU : mémoire de "ligne droite confirmée"
# ==========================
# Nombre de cycles consécutifs centrés nécessaires avant de considérer
# qu'on est VRAIMENT en ligne droite (et donc d'oublier le dernier virage).
CENTRE_CONFIRME = 8
compteur_centre = 0

# NOUVEAU : seuil dédié aux pointillés, distinct du seuil "vraiment perdu"
# Mesurez vos pointillés réels (longueur du segment noir + longueur du blanc)
# et ajustez ce chiffre : à VITESSE_LIGNE, le robot avance pendant
# SEUIL_POINTILLE * 0.025s. Si vos gaps blancs durent plus que ça, augmentez.
SEUIL_POINTILLE = 45      # ancien : 25 → souvent trop court, cause la perte
SEUIL_VRAIMENT_PERDU = 70  # au-delà, on admet qu'on a vraiment quitté la piste


def tourner(cible):
    global angle_actuel
    angle_actuel = angle_actuel * 0.6 + cible * 0.4
    servos.set_angle(0, round(angle_actuel, 1))


print("START")
tourner(CENTRE)
robot.set_motor(1, 30)
time.sleep(1)

try:
    while True:

        s = tracker.get_status()
        etat = (s["left"], s["middle"], s["right"])
        print(etat)

        # =====================
        # LIGNE CENTREE
        # =====================
        if etat == (1, 1, 1):
            compteur_virage = 0
            compteur_perdu = 0
            compteur_centre += 1

            # NOUVEAU : on efface la mémoire du dernier virage une fois
            # qu'on a confirmé plusieurs cycles de ligne droite stable.
            # C'est ce qui empêche un virage déjà passé de "ressurgir"
            # plus tard sur une zone de pointillés.
            if compteur_centre > CENTRE_CONFIRME:
                dernier_sens = 0

            cible = CENTRE
            vitesse = VITESSE_LIGNE

        # =====================
        # VIRAGE GAUCHE
        # =====================
        elif etat == (1, 1, 0):
            compteur_perdu = 0
            compteur_centre = 0
            compteur_virage += 1
            dernier_sens = 1

            if compteur_virage > 2:
                cible = GAUCHE_FORT
                vitesse = VITESSE_VIRAGE
            else:
                cible = GAUCHE_LEGER
                vitesse = VITESSE_APPROCHE

        elif etat == (1, 0, 0):
            compteur_perdu = 0
            compteur_centre = 0
            compteur_virage += 2
            dernier_sens = 1
            cible = GAUCHE_FORT
            vitesse = VITESSE_VIRAGE

        # =====================
        # VIRAGE DROITE
        # =====================
        elif etat == (0, 1, 1):
            compteur_perdu = 0
            compteur_centre = 0
            compteur_virage += 1
            dernier_sens = -1

            if compteur_virage > 2:
                cible = DROITE_FORT
                vitesse = VITESSE_VIRAGE
            else:
                cible = DROITE_LEGER
                vitesse = VITESSE_APPROCHE

        elif etat == (0, 0, 1):
            compteur_perdu = 0
            compteur_centre = 0
            compteur_virage += 2
            dernier_sens = -1
            cible = DROITE_FORT
            vitesse = VITESSE_VIRAGE

        # =====================
        # POINTILLES OU PERTE
        # =====================
        elif etat == (0, 0, 0):
            compteur_perdu += 1
            compteur_centre = 0

            # PHASE 1 : on vient de quitter une ligne centrée → très
            # probablement un pointillé. On garde tout droit, sans
            # appliquer aucun "dernier_sens" (qui ne doit JAMAIS
            # intervenir tant qu'on pense être sur un pointillé).
            if dernier_etat == (1, 1, 1) and compteur_perdu < SEUIL_POINTILLE:
                cible = CENTRE
                vitesse = VITESSE_LIGNE

            # PHASE 2 : zone intermédiaire — on n'est plus sûr d'être
            # sur un pointillé, mais pas encore "vraiment perdu".
            # On continue tout droit en ralentissant légèrement,
            # plutôt que de braquer franchement (ce qui causait le bug).
            elif compteur_perdu < SEUIL_VRAIMENT_PERDU:
                cible = CENTRE
                vitesse = VITESSE_PERDU

            # PHASE 3 : vraiment perdu (sortie de virage par ex.) →
            # on utilise dernier_sens, mais seulement ici, et seulement
            # si on n'est pas dans le cas pointillé ci-dessus.
            else:
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

        if etat != (0, 0, 0):
            dernier_etat = etat

        time.sleep(0.025)

except KeyboardInterrupt:
    print("STOP")
    robot.stopper()
    servos.set_angle(0, CENTRE)
