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


# corrections douces
GAUCHE_LEGER = 112
DROITE_LEGER = 82


# virages serrés
GAUCHE_FORT = 128
DROITE_FORT = 65


# vitesses
VITESSE_LIGNE = 34
VITESSE_APPROCHE = 25
VITESSE_VIRAGE = 18
VITESSE_PERDU = 15


angle_actuel = CENTRE

dernier_sens = 0
compteur_virage = 0

dernier_etat = (1,1,1)
compteur_perdu = 0



# ==========================
# SERVO
# ==========================

def tourner(cible):

    global angle_actuel


    # plus réactif qu'avant
    angle_actuel = angle_actuel*0.45 + cible*0.55


    servos.set_angle(
        0,
        round(angle_actuel,1)
    )



# ==========================
# START
# ==========================

print("START")

tourner(CENTRE)

robot.set_motor(1,25)

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



        # =====================
        # TOUT DROIT
        # =====================

        if etat == (1,1,1):

            compteur_virage = 0
            compteur_perdu = 0


            cible = CENTRE
            vitesse = VITESSE_LIGNE




        # =====================
        # PREPARATION GAUCHE
        # =====================

        elif etat == (1,1,0):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = 1


            cible = GAUCHE_LEGER

            # ralentir AVANT le virage
            vitesse = VITESSE_APPROCHE




        # =====================
        # VIRAGE GAUCHE
        # =====================

        elif etat == (1,0,0):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = 1


            if compteur_virage > 2:

                cible = GAUCHE_FORT

            else:

                cible = 120


            vitesse = VITESSE_VIRAGE





        # =====================
        # PREPARATION DROITE
        # =====================

        elif etat == (0,1,1):

            compteur_perdu = 0
            compteur_virage += 1


            dernier_sens = -1


            cible = DROITE_LEGER


            vitesse = VITESSE_APPROCHE





        # =====================
        # VIRAGE DROITE
        # =====================

        elif etat == (0,0,1):

            compteur_perdu = 0
            compteur_virage += 1


            dernier_sens = -1



            if compteur_virage > 2:

                cible = DROITE_FORT

            else:

                cible = 75



            vitesse = VITESSE_VIRAGE






        # =====================
        # 000
        # =====================

        elif etat == (0,0,0):


            compteur_perdu += 1



            # -------- POINTILLES --------

            if dernier_etat == (1,1,1) and compteur_perdu < 30:


                cible = CENTRE

                vitesse = VITESSE_LIGNE




            # -------- PERTE APRES VIRAGE --------

            else:


                if dernier_sens == 1:

                    cible = GAUCHE_FORT



                elif dernier_sens == -1:

                    cible = DROITE_FORT



                else:

                    cible = CENTRE



                vitesse = VITESSE_PERDU





        tourner(cible)



        robot.set_motor(
            1,
            vitesse
        )



        # mémoire dernière vraie lecture

        if etat != (0,0,0):

            dernier_etat = etat



        time.sleep(0.025)




except KeyboardInterrupt:


    print("STOP")


    robot.stopper()

    servos.set_angle(0,CENTRE)
