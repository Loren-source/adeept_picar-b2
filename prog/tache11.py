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
GAUCHE_LEGER = 105
DROITE_LEGER = 89


# virages S
GAUCHE_FORT = 125
DROITE_FORT = 68


VITESSE_LIGNE = 36
VITESSE_VIRAGE = 22
VITESSE_PERDU = 17


angle_actuel = CENTRE

dernier_sens = 0
# 1 = gauche
# -1 = droite

compteur_virage = 0
compteur_perdu = 0



# ==========================
# SERVO
# ==========================

def tourner(cible):

    global angle_actuel

    # plus rapide pour le virage en S
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



        # ==========================
        # CENTRE
        # ==========================

        if etat == (1,1,1):

            compteur_virage = 0
            compteur_perdu = 0

            cible = CENTRE
            vitesse = VITESSE_LIGNE



        # ==========================
        # TOURNE GAUCHE
        # ==========================

        elif etat == (1,1,0):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = 1

            cible = GAUCHE_LEGER
            vitesse = VITESSE_LIGNE



        elif etat == (1,0,0):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = 1


            # réaction rapide pour le S

            if compteur_virage > 2:

                cible = GAUCHE_FORT

            else:

                cible = 115


            vitesse = VITESSE_VIRAGE



        # ==========================
        # TOURNE DROITE
        # ==========================

        elif etat == (0,1,1):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = -1

            cible = DROITE_LEGER
            vitesse = VITESSE_LIGNE



        elif etat == (0,0,1):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = -1


            if compteur_virage > 2:

                cible = DROITE_FORT

            else:

                cible = 80


            vitesse = VITESSE_VIRAGE




        # ==========================
        # PERTE DE LIGNE
        # ==========================

        elif etat == (0,0,0):

            compteur_perdu += 1


            # continuer un peu le virage

            if compteur_perdu < 20:


                if dernier_sens == 1:

                    cible = GAUCHE_FORT


                elif dernier_sens == -1:

                    cible = DROITE_FORT


                else:

                    cible = CENTRE



            # si toujours perdu :
            # remettre un peu droit

            else:

                if dernier_sens == 1:

                    cible = 110


                elif dernier_sens == -1:

                    cible = 84


                else:

                    cible = CENTRE



            vitesse = VITESSE_PERDU




        tourner(cible)


        robot.set_motor(
            1,
            vitesse
        )


        time.sleep(0.025)



except KeyboardInterrupt:

    print("STOP")

    robot.stopper()

    servos.set_angle(0,CENTRE)
