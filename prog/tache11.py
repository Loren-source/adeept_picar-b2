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


# corrections
GAUCHE_LEGER = 112
DROITE_LEGER = 82


# vrais virages
GAUCHE_FORT = 128
DROITE_FORT = 65


# vitesses
VITESSE_LIGNE = 34
VITESSE_APPROCHE = 30
VITESSE_VIRAGE = 22      # MODIFIÉ
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
        # GAUCHE LEGER
        # =====================

        elif etat == (1,1,0):

            compteur_perdu = 0
            compteur_virage += 1


            dernier_sens = 1


            if compteur_virage > 4:

                cible = 120

            else:

                cible = GAUCHE_LEGER



            vitesse = VITESSE_APPROCHE





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

                cible = 122



            vitesse = VITESSE_VIRAGE






        # =====================
        # DROITE LEGER
        # =====================

        elif etat == (0,1,1):

            compteur_perdu = 0
            compteur_virage += 1


            dernier_sens = -1



            if compteur_virage > 4:

                cible = 75

            else:

                cible = DROITE_LEGER



            vitesse = VITESSE_APPROCHE






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

                cible = 72



            vitesse = VITESSE_VIRAGE








        # =====================
        # 000 : POINTILLÉS / PERDU
        # =====================

        elif etat == (0,0,0):


            compteur_perdu += 1



            # ---------------------
            # POINTILLÉS
            # ---------------------

            if compteur_perdu < 20:



                # il venait droit
                if dernier_etat == (1,1,1):


                    cible = CENTRE
                    vitesse = VITESSE_LIGNE



                # coupure pendant virage
                else:


                    cible = angle_actuel
                    vitesse = VITESSE_APPROCHE






            # ---------------------
            # VRAIE PERTE
            # ---------------------

            else:


                if dernier_sens == 1:


                    cible = GAUCHE_FORT



                elif dernier_sens == -1:


                    cible = DROITE_FORT



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
