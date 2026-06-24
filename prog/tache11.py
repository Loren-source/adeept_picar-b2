#!/usr/bin/env python3

import time

from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker


robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()


CENTRE = 97


# direction normale
GAUCHE_LEGER = 104
DROITE_LEGER = 90


# virages
GAUCHE_FORT = 125
DROITE_FORT = 68


VITESSE_LIGNE = 36
VITESSE_VIRAGE = 24
VITESSE_PERDU = 15


angle_actuel = CENTRE

dernier_sens = 0
# 1 gauche
# -1 droite

compteur_virage = 0
compteur_perdu = 0


def tourner(angle):

    global angle_actuel

    angle_actuel = angle_actuel*0.55 + angle*0.45

    servos.set_angle(
        0,
        round(angle_actuel,1)
    )



print("START")

tourner(CENTRE)
robot.set_motor(1,30)

time.sleep(1)



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

            compteur_perdu = 0
            compteur_virage = 0

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
            vitesse = VITESSE_LIGNE



        elif etat == (1,0,0):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = 1


            if compteur_virage > 4:
                cible = GAUCHE_FORT
            else:
                cible = 115


            vitesse = VITESSE_VIRAGE



        # =====================
        # DROITE
        # =====================

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


            if compteur_virage > 4:
                cible = DROITE_FORT
            else:
                cible = 80


            vitesse = VITESSE_VIRAGE




        # =====================
        # LIGNE PERDUE
        # =====================

        elif etat == (0,0,0):

            compteur_perdu += 1


            # au début continuer
            if compteur_perdu < 15:

                if dernier_sens == 1:
                    cible = GAUCHE_FORT

                else:
                    cible = DROITE_FORT


            # ensuite chercher inverse
            elif compteur_perdu < 35:


                if dernier_sens == 1:
                    cible = DROITE_FORT

                else:
                    cible = GAUCHE_FORT


            # balayage

            else:

                if (compteur_perdu // 20) % 2 == 0:
                    cible = GAUCHE_FORT
                else:
                    cible = DROITE_FORT


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
