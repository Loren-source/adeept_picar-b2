#!/usr/bin/env python3

import time

from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker


robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()


CENTRE = 97


# petites corrections
GAUCHE_LEGER = 104
DROITE_LEGER = 90


# vrais virages
GAUCHE_FORT = 128
DROITE_FORT = 65


VITESSE_LIGNE = 36
VITESSE_VIRAGE = 24
VITESSE_PERDU = 18


angle_actuel = CENTRE
dernier_sens = 0
compteur_virage = 0


def tourner(cible):

    global angle_actuel

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
        # CENTRE
        # =====================

        if etat == (1,1,1):

            compteur_virage = 0

            cible = CENTRE
            vitesse = VITESSE_LIGNE



        # =====================
        # partir à gauche
        # =====================

        elif etat == (1,1,0):

            compteur_virage += 1

            dernier_sens = 1

            cible = GAUCHE_LEGER
            vitesse = VITESSE_LIGNE



        elif etat == (1,0,0):

            compteur_virage += 1

            dernier_sens = 1


            # si ça dure :
            # c'est un vrai virage

            if compteur_virage > 5:
                cible = GAUCHE_FORT

            else:
                cible = 115


            vitesse = VITESSE_VIRAGE



        # =====================
        # partir à droite
        # =====================

        elif etat == (0,1,1):

            compteur_virage += 1

            dernier_sens = -1

            cible = DROITE_LEGER
            vitesse = VITESSE_LIGNE



        elif etat == (0,0,1):

            compteur_virage += 1

            dernier_sens = -1


            if compteur_virage > 5:
                cible = DROITE_FORT

            else:
                cible = 80


            vitesse = VITESSE_VIRAGE



        # =====================
        # PERDU
        # =====================

        elif etat == (0,0,0):

            # cherche plus fort dans
            # le dernier sens connu

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
