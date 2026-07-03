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
VITESSE_VIRAGE = 24
VITESSE_PERDU = 19
VITESSE_POINTILLE = 36          # vitesse de traversée des pointillés

# Seuils
SEUIL_POINTILLE = 50            # 50 cycles = 1.25s (pour les pointillés)
SEUIL_PERDU_MAX = 150           # 150 cycles = 3.75s avant arrêt total

angle_actuel = CENTRE


dernier_sens = 0
# 1 = gauche
# -1 = droite


compteur_virage = 0

dernier_etat = (1,1,1)
compteur_pointille = 0          # compte les cycles de (0,0,0) pour les pointillés
compteur_perdu = 0              # compte les cycles de perte réelle

# Mémorisation de la dernière trajectoire modérée
derniere_cible = CENTRE
derniere_vitesse = VITESSE_LIGNE


# ==========================
# SERVO (avec retour au centre plus rapide)
# ==========================

def tourner(cible):

    global angle_actuel

    # Si on va vers le centre, on accélère le mouvement
    if cible == CENTRE:
        angle_actuel = angle_actuel * 0.45 + cible * 0.55
    else:
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
# BOUCLE PRINCIPALE
# ==========================

try:

    while True:


        s = tracker.get_status()


        etat = (
            s["left"],
            s["middle"],
            s["right"]
        )


        # =====================
        # CENTRE
        # =====================

        if etat == (1,1,1):

            compteur_virage = 0
            compteur_pointille = 0
            compteur_perdu = 0


            cible = CENTRE
            vitesse = VITESSE_LIGNE
            # Mémorisation pour les états modérés
            derniere_cible = cible
            derniere_vitesse = vitesse



        # =====================
        # VIRAGE GAUCHE (modéré)
        # =====================

        elif etat == (1,1,0):

            compteur_pointille = 0
            compteur_perdu = 0

            compteur_virage = min(compteur_virage + 1, 5)

            dernier_sens = 1


            cible = GAUCHE_LEGER

            vitesse = 28

            derniere_cible = cible
            derniere_vitesse = vitesse



        # =====================
        # VIRAGE GAUCHE (serré) – on NE mémorise PAS
        # =====================

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

            # PAS de mémorisation ici



        # =====================
        # VIRAGE DROITE (modéré)
        # =====================

        elif etat == (0,1,1):

            compteur_pointille = 0
            compteur_perdu = 0

            compteur_virage = min(compteur_virage + 1, 5)

            dernier_sens = -1


            cible = DROITE_LEGER

            vitesse = 28

            derniere_cible = cible
            derniere_vitesse = vitesse



        # =====================
        # VIRAGE DROITE (serré) – on NE mémorise PAS
        # =====================

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

            # PAS de mémorisation




        # =====================
        # 000 : POINTILLÉS OU PERDU
        # =====================

        elif etat == (0,0,0):

            # Déterminer si l'état précédent était un virage modéré ou une ligne droite
            venait_de_ligne = dernier_etat in ((1,1,1), (1,1,0), (0,1,1))

            # ======================
            # CAS POINTILLÉS (si on venait d'un état modéré)
            # ======================

            if venait_de_ligne:

                # On incrémente le compteur de pointillés
                compteur_pointille += 1

                # Transition douce vers le centre
                if compteur_pointille <= SEUIL_POINTILLE:

                    if compteur_pointille == 1:
                        cible = derniere_cible
                    elif compteur_pointille == 2:
                        cible = (derniere_cible + CENTRE) / 2
                    else:
                        cible = CENTRE

                    vitesse = VITESSE_POINTILLE

                    # On garde compteur_perdu à 0
                else:
                    # Si les pointillés durent trop longtemps, on passe en recherche
                    compteur_perdu += 1
                    if compteur_perdu > SEUIL_PERDU_MAX:
                        print("--- Fin de parcours ou perte définitive ---")
                        cible = CENTRE
                        vitesse = 0
                        tourner(cible)
                        robot.set_motor(1, 0)
                        break
                    # Alternance pour chercher
                    phase = (compteur_perdu - 1) // 30
                    if phase % 2 == 0:
                        cible = GAUCHE_FORT
                    else:
                        cible = DROITE_FORT
                    vitesse = VITESSE_PERDU

            # ======================
            # PERTE RÉELLE (si on venait d'un virage serré)
            # ======================

            else:
                # On incrémente directement le compteur de perte
                compteur_perdu += 1

                if compteur_perdu > SEUIL_PERDU_MAX:
                    print("--- Fin de parcours ou perte définitive ---")
                    cible = CENTRE
                    vitesse = 0
                    tourner(cible)
                    robot.set_motor(1, 0)
                    break

                # On commence immédiatement la recherche
                phase = (compteur_perdu - 1) // 30
                if phase % 2 == 0:
                    cible = GAUCHE_FORT
                else:
                    cible = DROITE_FORT
                vitesse = VITESSE_PERDU


        # =====================
        # DEBUG
        # =====================
        print(f"etat={etat} angle={round(angle_actuel,1)} cible={cible if 'cible' in locals() else '-'} pointille={compteur_pointille} perdu={compteur_perdu}")


        # =====================
        # APPLICATION
        # =====================

        tourner(cible)



        robot.set_motor(
            1,
            vitesse
        )



        # =====================
        # MEMOIRE
        # =====================

        if etat != (0,0,0):
            dernier_etat = etat



        time.sleep(0.025)





except KeyboardInterrupt:


    print("STOP")


    robot.stopper()


    servos.set_angle(0,CENTRE)
