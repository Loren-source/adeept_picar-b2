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


# vrais virages (adoucis)
GAUCHE_FORT = 125
DROITE_FORT = 68


VITESSE_LIGNE = 34
VITESSE_VIRAGE = 22
VITESSE_PERDU = 16


angle_actuel = CENTRE


dernier_sens = 0
# 1 = gauche
# -1 = droite


compteur_virage = 0
compteur_perdu = 0

dernier_etat = (1,1,1)



# ==========================
# SERVO FLUIDE
# ==========================

def tourner(cible):

    global angle_actuel


    # filtre pour éviter les coups secs
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
        # LIGNE DROITE
        # =====================

        if etat == (1,1,1):


            compteur_virage = 0
            compteur_perdu = 0


            cible = CENTRE

            vitesse = VITESSE_LIGNE




        # =====================
        # GAUCHE LEGER
        # =====================

        elif etat == (1,1,0):


            compteur_perdu = 0

            compteur_virage += 1

            dernier_sens = 1


            cible = GAUCHE_LEGER

            vitesse = 28




        # =====================
        # GAUCHE FORT
        # =====================

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
        # DROITE LEGER
        # =====================

        elif etat == (0,1,1):


            compteur_perdu = 0

            compteur_virage += 1

            dernier_sens = -1


            cible = DROITE_LEGER

            vitesse = 28




        # =====================
        # DROITE FORT
        # =====================

        elif etat == (0,0,1):


            compteur_perdu = 0

            compteur_virage += 1

            dernier_sens = -1



            if compteur_virage > 3:

                cible = DROITE_FORT

            else:

                cible = 75



            vitesse = VITESSE_VIRAGE





        # =====================
        # PERTE OU POINTILLES
        # =====================

        elif etat == (0,0,0):


            compteur_perdu += 1



            # --------------------
            # POINTILLES
            # --------------------

            if dernier_etat == (1,1,1) and compteur_perdu < 20:


                cible = CENTRE

                vitesse = VITESSE_LIGNE




            # --------------------
            # SORTIE VIRAGE
            # on garde le virage
            # --------------------

            elif compteur_perdu < 15:



                if dernier_sens == 1:


                    cible = GAUCHE_FORT



                elif dernier_sens == -1:


                    cible = DROITE_FORT



                else:


                    cible = CENTRE



                vitesse = VITESSE_PERDU





            # --------------------
            # RECHERCHE LIGNE
            # on ouvre le volant
            # --------------------

            else:



                if dernier_sens == 1:


                    cible = GAUCHE_LEGER



                elif dernier_sens == -1:


                    cible = DROITE_LEGER



                else:


                    cible = CENTRE



                vitesse = 16




        # appliquer direction

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


    servos.set_angle(0,CENTRE)
