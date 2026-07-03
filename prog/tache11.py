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


VITESSE_LIGNE = 43
VITESSE_VIRAGE = 24
VITESSE_PERDU = 19
VITESSE_POINTILLE = 30          # vitesse réduite pour les pointillés

# Seuils
SEUIL_POINTILLE = 60            # 50 cycles = 1.25s (augmenté)
SEUIL_PERDU_MAX = 150           # 150 cycles = 3.75s avant arrêt total

angle_actuel = CENTRE


dernier_sens = 0
# 1 = gauche
# -1 = droite


compteur_virage = 0

dernier_etat = (1,1,1)
compteur_perdu = 0

# Mémorisation de la dernière trajectoire
derniere_cible = CENTRE
derniere_vitesse = VITESSE_LIGNE


# ==========================
# SERVO
# ==========================

def tourner(cible):

    global angle_actuel

    # réglage validé sur ton parcours
    angle_actuel = angle_actuel*0.6 + cible*0.4


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


        print(etat)



        # =====================
        # CENTRE
        # =====================

        if etat == (1,1,1):

            compteur_virage = 0
            compteur_perdu = 0


            cible = CENTRE
            vitesse = VITESSE_LIGNE
            derniere_cible = cible
            derniere_vitesse = vitesse



        # =====================
        # VIRAGE GAUCHE
        # =====================

        elif etat == (1,1,0):

            compteur_perdu = 0

            compteur_virage += 1

            dernier_sens = 1


            cible = GAUCHE_LEGER

            vitesse = 28

            derniere_cible = cible
            derniere_vitesse = vitesse



        elif etat == (1,0,0):

            compteur_perdu = 0

            compteur_virage += 1

            dernier_sens = 1


            if compteur_virage > 3:

                cible = GAUCHE_FORT

            else:

                cible = 120



            vitesse = VITESSE_VIRAGE

            derniere_cible = cible
            derniere_vitesse = vitesse




        # =====================
        # VIRAGE DROITE
        # =====================

        elif etat == (0,1,1):

            compteur_perdu = 0

            compteur_virage += 1

            dernier_sens = -1


            cible = DROITE_LEGER

            vitesse = 28

            derniere_cible = cible
            derniere_vitesse = vitesse



        elif etat == (0,0,1):

            compteur_perdu = 0

            compteur_virage += 1

            dernier_sens = -1



            if compteur_virage > 3:

                cible = DROITE_FORT


            else:

                cible = 75



            vitesse = VITESSE_VIRAGE

            derniere_cible = cible
            derniere_vitesse = vitesse




        # =====================
        # 000 : POINTILLÉS OU PERDU
        # =====================

        elif etat == (0,0,0):


            compteur_perdu += 1



            # ======================
            # CAS POINTILLÉS (on garde la trajectoire)
            # ======================

            if compteur_perdu <= SEUIL_POINTILLE:


                # on continue sur la dernière trajectoire connue
                cible = derniere_cible
                vitesse = VITESSE_POINTILLE



            # ======================
            # VRAIE PERTE (on cherche)
            # ======================

            else:

                # Si la perte dure très longtemps, on arrête
                if compteur_perdu > SEUIL_PERDU_MAX:
                    print("--- Fin de parcours ou perte définitive ---")
                    cible = CENTRE
                    vitesse = 0
                    tourner(cible)
                    robot.set_motor(1, 0)
                    break   # sortie de la boucle

                # Sinon, on alterne les directions pour chercher la ligne
                # Phase alternée toutes les 30 cycles (0.75s)
                phase = (compteur_perdu - SEUIL_POINTILLE) // 30
                if phase % 2 == 0:
                    cible = GAUCHE_FORT
                else:
                    cible = DROITE_FORT

                vitesse = VITESSE_PERDU




        tourner(cible)



        robot.set_motor(
            1,
            vitesse
        )



        # =====================
        # MEMOIRE
        # =====================

        # On met à jour dernier_etat UNIQUEMENT si on voit la ligne
        if etat != (0,0,0):
            dernier_etat = etat



        time.sleep(0.025)





except KeyboardInterrupt:


    print("STOP")


    robot.stopper()


    servos.set_angle(0,CENTRE)
