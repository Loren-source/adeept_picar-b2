#!/usr/bin/env python3

import time

from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker


robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()


CENTRE = 97


# correction normale
GAUCHE_LEGER = 112
DROITE_LEGER = 82


# virages
GAUCHE_FORT = 128
DROITE_FORT = 65


VITESSE_LIGNE = 34
VITESSE_VIRAGE = 22
VITESSE_PERDU = 18


angle_actuel = CENTRE

dernier_sens = 0
compteur_virage = 0


def tourner(cible):

    global angle_actuel

    # on remet comme la version qui passait le 1er virage
    angle_actuel = angle_actuel*0.6 + cible*0.4

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
        # AU CENTRE
        # =====================

        if etat == (1,1,1):

            compteur_virage = 0

            cible = CENTRE
            vitesse = VITESSE_LIGNE


        # =====================
        # GAUCHE
        # =====================

        elif etat == (1,1,0):

            compteur_virage += 1
            dernier_sens = 1

            # on anticipe davantage
            cible = GAUCHE_LEGER

            vitesse = 28



        elif etat == (1,0,0):

            compteur_virage += 1
            dernier_sens = 1


            if compteur_virage > 3:
                cible = GAUCHE_FORT

            else:
                cible = 120


            vitesse = VITESSE_VIRAGE



        # =====================
        # DROITE
        # =====================

        elif etat == (0,1,1):

            compteur_virage += 1
            dernier_sens = -1

            cible = DROITE_LEGER

            vitesse = 28



        elif etat == (0,0,1):

            compteur_virage += 1
            dernier_sens = -1


            if compteur_virage > 3:
                cible = DROITE_FORT

            else:
                cible = 75


            vitesse = VITESSE_VIRAGE



        # =====================
        # PERDU
        # =====================

        elif etat == (0,0,0):


            # IMPORTANT :
            # continuer le virage
            # ne pas redresser

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


        time.sleep(0.025)



except KeyboardInterrupt:

    print("STOP")

    robot.stopper()

    servos.set_angle(0,CENTRE)
