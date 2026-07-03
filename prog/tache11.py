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
VITESSE_VIRAGE = 26
VITESSE_PERDU = 19
VITESSE_POINTILLE = 34          # plus rapide pour réduire le temps sans capteurs

# Seuils
SEUIL_POINTILLE = 50            # 50 cycles = 1.25s (à ajuster selon la longueur des pointillés)
SEUIL_PERDU_MAX = 150           # 150 cycles = 3.75s avant arrêt total

angle_actuel = CENTRE

dernier_sens = 0                # 1=gauche, -1=droite
compteur_virage = 0
dernier_etat = (1,1,1)
compteur_perdu = 0

# Mémorisation de la dernière trajectoire "modérée" (uniquement pour 111, 110, 011)
derniere_cible = CENTRE
derniere_vitesse = VITESSE_LIGNE


# ==========================
# SERVO
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
# BOUCLE PRINCIPALE
# ==========================

try:
    while True:
        s = tracker.get_status()
        etat = (s["left"], s["middle"], s["right"])

        # Debug
        print(f"etat={etat} angle={round(angle_actuel,1)} cible={cible if 'cible' in locals() else '-'} perdu={compteur_perdu}")

        # =====================
        # CENTRE (1,1,1)
        # =====================
        if etat == (1,1,1):
            compteur_virage = 0
            compteur_perdu = 0
            cible = CENTRE
            vitesse = VITESSE_LIGNE
            # Mémorisation car état modéré
            derniere_cible = cible
            derniere_vitesse = vitesse

        # =====================
        # VIRAGE GAUCHE MODÉRÉ (1,1,0)
        # =====================
        elif etat == (1,1,0):
            compteur_perdu = 0
            compteur_virage = min(compteur_virage + 1, 5)
            dernier_sens = 1
            cible = GAUCHE_LEGER
            vitesse = 28
            # Mémorisation
            derniere_cible = cible
            derniere_vitesse = vitesse

        # =====================
        # VIRAGE GAUCHE SERRÉ (1,0,0) – on NE mémorise PAS
        # =====================
        elif etat == (1,0,0):
            compteur_perdu = 0
            compteur_virage = min(compteur_virage + 1, 5)
            dernier_sens = 1
            if compteur_virage > 3:
                cible = GAUCHE_FORT
            else:
                cible = 120
            vitesse = VITESSE_VIRAGE
            # PAS de mémorisation ici

        # =====================
        # VIRAGE DROITE MODÉRÉ (0,1,1)
        # =====================
        elif etat == (0,1,1):
            compteur_perdu = 0
            compteur_virage = min(compteur_virage + 1, 5)
            dernier_sens = -1
            cible = DROITE_LEGER
            vitesse = 28
            # Mémorisation
            derniere_cible = cible
            derniere_vitesse = vitesse

        # =====================
        # VIRAGE DROITE SERRÉ (0,0,1) – on NE mémorise PAS
        # =====================
        elif etat == (0,0,1):
            compteur_perdu = 0
            compteur_virage = min(compteur_virage + 1, 5)
            dernier_sens = -1
            if compteur_virage > 3:
                cible = DROITE_FORT
            else:
                cible = 75
            vitesse = VITESSE_VIRAGE
            # PAS de mémorisation

        # =====================
        # 000 : POINTILLÉS OU PERDU
        # =====================
        elif etat == (0,0,0):
            compteur_perdu += 1

            # ======================
            # CAS POINTILLÉS (on garde la dernière trajectoire modérée, avec retour progressif vers CENTRE)
            # ======================
            if compteur_perdu <= SEUIL_POINTILLE:
                # Retour progressif vers le centre (pas de -2/+2 pour une douceur optimale)
                if derniere_cible > CENTRE:
                    cible = max(CENTRE, derniere_cible - 2)
                elif derniere_cible < CENTRE:
                    cible = min(CENTRE, derniere_cible + 2)
                else:
                    cible = CENTRE
                # On met à jour pour la prochaine itération
                derniere_cible = cible
                vitesse = VITESSE_POINTILLE

            # ======================
            # VRAIE PERTE (on cherche)
            # ======================
            else:
                if compteur_perdu > SEUIL_PERDU_MAX:
                    print("--- Fin de parcours ou perte définitive ---")
                    cible = CENTRE
                    vitesse = 0
                    tourner(cible)
                    robot.set_motor(1, 0)
                    break
                # Alternance gauche/droite toutes les 30 cycles
                phase = (compteur_perdu - SEUIL_POINTILLE) // 30
                if phase % 2 == 0:
                    cible = GAUCHE_FORT
                else:
                    cible = DROITE_FORT
                vitesse = VITESSE_PERDU

        # =====================
        # APPLICATION
        # =====================
        tourner(cible)
        robot.set_motor(1, vitesse)

        # Mise à jour de dernier_etat uniquement si ligne vue
        if etat != (0,0,0):
            dernier_etat = etat

        time.sleep(0.025)


except KeyboardInterrupt:
    print("STOP")
    robot.stopper()
    servos.set_angle(0, CENTRE)
