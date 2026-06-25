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
GAUCHE_LEGER = 112
DROITE_LEGER = 82


# vrais virages (corrigés)
GAUCHE_FORT = 124
DROITE_FORT = 68


# vitesses
VITESSE_LIGNE = 34
VITESSE_APPROCHE = 30
VITESSE_VIRAGE = 22
VITESSE_PERDU = 16


angle_actuel = CENTRE


dernier_sens = 0
#  1 = gauche
# -1 = droite


compteur_virage = 0
compteur_perdu = 0

dernier_etat = (1,1,1)



# ==========================
# SERVO FLUIDE
# ==========================

def tourner(cible):

    global angle_actuel


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
        # LIGNE DROITE
        # =====================

        if etat == (1,1,1):

            compteur_virage = 0
            compteur_perdu = 0

            cible = CENTRE
            vitesse = VITESSE_LIGNE





        # =====================
        # VIRAGE GAUCHE
        # =====================

        elif etat == (1,1,0):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = 1


            if compteur_virage > 4:

                cible = 118

            else:

                cible = GAUCHE_LEGER


            vitesse = 28





        elif etat == (1,0,0):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = 1


            if compteur_virage > 3:

                cible = GAUCHE_FORT

            else:

                cible = 120


            vitesse = VITESSE_VIRAGE






        # =====================
        # VIRAGE DROITE
        # =====================

        elif etat == (0,1,1):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = -1


            if compteur_virage > 4:

                cible = 76

            else:

                cible = DROITE_LEGER


            vitesse = 28





        elif etat == (0,0,1):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = -1


            if compteur_virage > 3:

                cible = DROITE_FORT

            else:

                cible = 74


            vitesse = VITESSE_VIRAGE






        # =====================
        # 000 : POINTILLE / PERDU
        # =====================

        elif etat == (0,0,0):

            compteur_perdu += 1



            # ==================
            # POINTILLES
            # ==================

            if compteur_perdu < 20:


                if dernier_etat == (1,1,1):

                    # trou dans ligne droite
                    cible = CENTRE
                    vitesse = VITESSE_LIGNE


                else:

                    # garder trajectoire actuelle
                    cible = angle_actuel
                    vitesse = VITESSE_APPROCHE





            # ==================
            # VRAIE PERTE
            # ==================

            else:


                if dernier_sens == 1:

                    # récupération gauche douce
                    cible = 118


                elif dernier_sens == -1:

                    # récupération droite douce
                    cible = 76


                else:

                    cible = CENTRE


                vitesse = VITESSE_PERDU





        # =====================
        # APPLICATION
        # =====================

        tourner(cible)


        robot.set_motor(
            1,
            vitesse
        )



        # mémoire

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
