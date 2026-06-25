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


# corrections légères
GAUCHE_LEGER = 112
DROITE_LEGER = 82


# virages forts (réduit pour éviter de couper)
GAUCHE_FORT = 123
DROITE_FORT = 70


VITESSE_LIGNE = 34
VITESSE_VIRAGE = 22
VITESSE_PERDU = 15


angle_actuel = CENTRE


# mémoire direction
dernier_sens = 0
# 1 gauche
# -1 droite


compteur_virage = 0
compteur_perdu = 0

dernier_etat = (1,1,1)



# ==========================
# SERVO DIRECTION
# ==========================

def tourner(cible):

    global angle_actuel


    # plus réactif qu'avant
    angle_actuel = angle_actuel*0.5 + cible*0.5


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
        # CENTRÉ
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

            vitesse = 28





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

            vitesse = 28





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
        # 000 : POINTILLÉ / PERDU
        # =====================

        elif etat == (0,0,0):


            compteur_perdu += 1



            # ------------------
            # POINTILLÉS
            # ------------------

            if dernier_etat == (1,1,1) and compteur_perdu < 18:


                # garde la trajectoire

                cible = angle_actuel

                vitesse = VITESSE_LIGNE




            # ------------------
            # VRAIE PERTE
            # ------------------

            else:


                # on ne bloque plus à fond
                # on cherche la ligne


                if dernier_sens == 1:


                    cible = 110



                elif dernier_sens == -1:


                    cible = 85



                else:


                    cible = CENTRE



                vitesse = VITESSE_PERDU






        # appliquer direction

        tourner(cible)



        robot.set_motor(
            1,
            vitesse
        )



        # mémoire dernier vrai état

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
