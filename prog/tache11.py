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


# corrections progressives
GAUCHE_LEGER = 112
DROITE_LEGER = 82


# virages serrés
GAUCHE_FORT = 123
DROITE_FORT = 70


VITESSE_LIGNE = 34
VITESSE_VIRAGE = 20
VITESSE_PERDU = 17


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


    # filtre progressif
    angle_actuel = angle_actuel*0.55 + cible*0.45


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



        # =====================
        # LIGNE CENTREE
        # =====================

        if etat == (1,1,1):

            compteur_virage = 0
            compteur_perdu = 0


            cible = CENTRE
            vitesse = VITESSE_LIGNE




        # =====================
        # GAUCHE
        # =====================

        elif etat == (1,1,0):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = 1


            cible = GAUCHE_LEGER
            vitesse = 27




        elif etat == (1,0,0):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = 1


            if compteur_virage > 3:

                cible = GAUCHE_FORT

            else:

                cible = 118


            vitesse = VITESSE_VIRAGE





        # =====================
        # DROITE
        # =====================

        elif etat == (0,1,1):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = -1


            cible = DROITE_LEGER
            vitesse = 27




        elif etat == (0,0,1):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = -1


            if compteur_virage > 3:

                cible = DROITE_FORT

            else:

                cible = 76


            vitesse = VITESSE_VIRAGE




        # =====================
        # POINTILLES / PERTE
        # =====================

        elif etat == (0,0,0):


            compteur_perdu += 1



            # -----------------
            # POINTILLES
            # -----------------

            if dernier_etat == (1,1,1) and compteur_perdu < 20:


                cible = CENTRE
                vitesse = VITESSE_LIGNE




            # -----------------
            # VIRAGE SERRÉ
            # continuer !!!
            # -----------------

            elif compteur_perdu < 45:



                if dernier_sens == 1:


                    cible = GAUCHE_FORT



                elif dernier_sens == -1:


                    cible = DROITE_FORT



                else:


                    cible = CENTRE



                vitesse = VITESSE_VIRAGE




            # -----------------
            # vraiment perdu
            # balayage doux
            # -----------------

            else:


                if dernier_sens == 1:


                    cible = 115


                elif dernier_sens == -1:


                    cible = 80


                else:


                    cible = CENTRE



                vitesse = VITESSE_PERDU





        # appliquer servo

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
