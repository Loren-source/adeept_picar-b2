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


# correction douce
GAUCHE_LEGER = 110
DROITE_LEGER = 84


# virages réels
GAUCHE_FORT = 122
DROITE_FORT = 72


VITESSE_LIGNE = 34
VITESSE_VIRAGE = 24
VITESSE_PERDU = 18



angle_actuel = CENTRE


# mémoire
dernier_sens = 0
# 1 gauche
# -1 droite


compteur_virage = 0

compteur_perdu = 0

dernier_etat = (1,1,1)



# ==========================
# SERVO FLUIDE
# ==========================

def tourner(cible):

    global angle_actuel


    # plus doux que 0.6/0.4
    angle_actuel = angle_actuel*0.7 + cible*0.3


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

time.sleep(0.7)




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
        # LIGNE LARGE / CENTRE
        # =====================

        if etat == (1,1,1):


            compteur_perdu = 0


            # on ne casse plus le virage directement

            if dernier_sens == 1 and compteur_virage > 0:


                cible = 104


                compteur_virage -= 1



            elif dernier_sens == -1 and compteur_virage > 0:


                cible = 90


                compteur_virage -= 1



            else:


                cible = CENTRE



            vitesse = VITESSE_LIGNE




        # =====================
        # VIRAGE GAUCHE LEGER
        # =====================

        elif etat == (1,1,0):


            compteur_perdu = 0

            dernier_sens = 1

            compteur_virage = 5


            cible = GAUCHE_LEGER

            vitesse = 30




        # =====================
        # VIRAGE GAUCHE FORT
        # =====================

        elif etat == (1,0,0):


            compteur_perdu = 0


            dernier_sens = 1

            compteur_virage += 2



            if compteur_virage > 8:

                cible = GAUCHE_FORT

            else:

                cible = 116



            vitesse = VITESSE_VIRAGE




        # =====================
        # VIRAGE DROITE LEGER
        # =====================

        elif etat == (0,1,1):


            compteur_perdu = 0

            dernier_sens = -1

            compteur_virage = 5


            cible = DROITE_LEGER

            vitesse = 30




        # =====================
        # VIRAGE DROITE FORT
        # =====================

        elif etat == (0,0,1):


            compteur_perdu = 0


            dernier_sens = -1

            compteur_virage += 2



            if compteur_virage > 8:

                cible = DROITE_FORT

            else:

                cible = 78



            vitesse = VITESSE_VIRAGE




        # =====================
        # 000 : POINTILLE OU PERTE
        # =====================

        elif etat == (0,0,0):


            compteur_perdu += 1



            # ---- POINTILLES ----

            if dernier_etat == (1,1,1) and compteur_perdu < 20:


                cible = CENTRE

                vitesse = VITESSE_LIGNE



            # ---- RECHERCHE ----

            else:


                # au début on continue le virage

                if compteur_perdu < 25:


                    if dernier_sens == 1:

                        cible = 115


                    elif dernier_sens == -1:

                        cible = 80


                    else:

                        cible = CENTRE



                # si ça marche pas on balaie inverse

                else:


                    if dernier_sens == 1:

                        cible = 78


                    else:

                        cible = 116



                vitesse = VITESSE_PERDU




        else:


            cible = CENTRE
            vitesse = 25




        # =====================
        # ACTION
        # =====================

        tourner(cible)


        robot.set_motor(
            1,
            int(vitesse)
        )



        # mémoire état

        if etat != (0,0,0):

            dernier_etat = etat



        time.sleep(0.025)





except KeyboardInterrupt:


    print("STOP")


    robot.stopper()

    servos.set_angle(0,CENTRE)
