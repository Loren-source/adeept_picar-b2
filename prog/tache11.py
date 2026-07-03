#!/usr/bin/env python3

import time

from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker


robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()


# ==========================
# REGLAGES
# ==========================

CENTRE = 97

# petites corrections
GAUCHE_LEGER = 115
DROITE_LEGER = 82

# vrais virages
GAUCHE_FORT = 128
DROITE_FORT = 65

VITESSE_LIGNE = 45
VITESSE_VIRAGE = 22          # réduite pour plus de sécurité
VITESSE_PERDU = 19
VITESSE_POINTILLE = 36

# Seuils
SEUIL_POINTILLE = 50          # 1.25s avant de considérer une perte (uniquement pour les états modérés)
SEUIL_PERDU_MAX = 150         # 3.75s avant arrêt total
SEUIL_ANGLE_DROIT = 12        # considéré comme "droit" si dans ±12° du centre

angle_actuel = CENTRE

dernier_sens = 0                # 1=gauche, -1=droite
compteur_virage = 0
dernier_etat = (1,1,1)
compteur_pointille = 0          # cycles en (0,0,0) pour les pointillés
compteur_perdu = 0              # cycles de perte réelle

derniere_cible = CENTRE
derniere_vitesse = VITESSE_LIGNE


# ==========================
# SERVO avec retour au centre accéléré
# ==========================

def tourner(cible):
    global angle_actuel
    if cible == CENTRE:
        # Retour au centre rapide : 30% ancien, 70% cible
        angle_actuel = angle_actuel * 0.3 + cible * 0.7
    else:
        # Mouvement fluide en virage : 60% ancien, 40% cible
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
# BOUCLE PRINCIPALE
# ==========================

try:
    while True:
        s = tracker.get_status()
        etat = (s["left"], s["middle"], s["right"])
        print(etat)

        # --- ÉTATS VISIBLES ---

        if etat == (1,1,1):
            compteur_virage = 0
            compteur_pointille = 0
            compteur_perdu = 0
            cible = CENTRE
            vitesse = VITESSE_LIGNE
            derniere_cible = cible
            derniere_vitesse = vitesse

        elif etat == (1,1,0):
            compteur_pointille = 0
            compteur_perdu = 0
            compteur_virage = min(compteur_virage + 1, 5)
            dernier_sens = 1
            cible = GAUCHE_LEGER
            vitesse = 28
            derniere_cible = cible
            derniere_vitesse = vitesse

        elif etat == (1,0,0):
            compteur_pointille = 0
            compteur_perdu = 0
            compteur_virage = min(compteur_virage + 1, 5)
            dernier_sens = 1
            if compteur_virage > 3:
                cible = GAUCHE_FORT
            else:
                cible = 120
            vitesse = VITESSE_VIRAGE
            derniere_cible = cible      # Mémorisation pour tous les états !
            derniere_vitesse = vitesse

        elif etat == (0,1,1):
            compteur_pointille = 0
            compteur_perdu = 0
            compteur_virage = min(compteur_virage + 1, 5)
            dernier_sens = -1
            cible = DROITE_LEGER
            vitesse = 28
            derniere_cible = cible
            derniere_vitesse = vitesse

        elif etat == (0,0,1):
            compteur_pointille = 0
            compteur_perdu = 0
            compteur_virage = min(compteur_virage + 1, 5)
            dernier_sens = -1
            if compteur_virage > 3:
                cible = DROITE_FORT
            else:
                cible = 75
            vitesse = VITESSE_VIRAGE
            derniere_cible = cible
            derniere_vitesse = vitesse

        # --- 000 : POINTILLÉS OU PERTE ---

        elif etat == (0,0,0):
            # Détection du type de perte
            venait_de_virage_serre = dernier_etat in ((1,0,0), (0,0,1))
            venait_de_ligne_modere = dernier_etat in ((1,1,1), (1,1,0), (0,1,1))

            if venait_de_virage_serre:
                # Perte après un virage serré → recherche immédiate
                compteur_perdu += 1
                if compteur_perdu > SEUIL_PERDU_MAX:
                    print("--- Fin de parcours ---")
                    cible = CENTRE
                    vitesse = 0
                    tourner(cible)
                    robot.set_motor(1, 0)
                    break
                # On braque dans la dernière direction (angle fort)
                cible = derniere_cible
                vitesse = VITESSE_PERDU

            elif venait_de_ligne_modere and abs(angle_actuel - CENTRE) < SEUIL_ANGLE_DROIT:
                # Pointillé probable (état modéré + angle proche du centre)
                compteur_pointille += 1
                if compteur_pointille <= SEUIL_POINTILLE:
                    # Transition douce
                    if compteur_pointille == 1:
                        cible = derniere_cible
                    elif compteur_pointille == 2:
                        cible = (derniere_cible + CENTRE) / 2
                    else:
                        cible = CENTRE
                    vitesse = VITESSE_POINTILLE
                else:
                    # Pointillé trop long → recherche
                    compteur_perdu += 1
                    if compteur_perdu > SEUIL_PERDU_MAX:
                        print("--- Fin de parcours ---")
                        cible = CENTRE
                        vitesse = 0
                        tourner(cible)
                        robot.set_motor(1, 0)
                        break
                    phase = (compteur_perdu - 1) // 30
                    cible = GAUCHE_FORT if phase % 2 == 0 else DROITE_FORT
                    vitesse = VITESSE_PERDU
            else:
                # Autre cas (par exemple angle éloigné ou état inattendu) → recherche immédiate
                compteur_perdu += 1
                if compteur_perdu > SEUIL_PERDU_MAX:
                    print("--- Fin de parcours ---")
                    cible = CENTRE
                    vitesse = 0
                    tourner(cible)
                    robot.set_motor(1, 0)
                    break
                phase = (compteur_perdu - 1) // 30
                cible = GAUCHE_FORT if phase % 2 == 0 else DROITE_FORT
                vitesse = VITESSE_PERDU

        # --- APPLICATION ---

        tourner(cible)
        robot.set_motor(1, vitesse)

        # Mise à jour de la mémoire (seulement si ligne vue)
        if etat != (0,0,0):
            dernier_etat = etat

        time.sleep(0.025)


except KeyboardInterrupt:
    print("STOP")
    robot.stopper()
    servos.set_angle(0, CENTRE)
