#!/usr/bin/env python3

import time

from motor import RobotMotor
from servo import RobotServos
from line import LineTracker


robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()


CENTRE = 97

# TON ROBOT :
# grand angle = gauche
# petit angle = droite

MAX_CORRECTION = 35


VITESSE_DROITE = 40
VITESSE_VIRAGE = 30


angle_actuel = CENTRE
correction = 0


def limite(x,a,b):
    return max(a,min(b,x))


def tourner(cible):
    global angle_actuel

    # plus doux
    angle_actuel = angle_actuel*0.8 + cible*0.2

    servos.set_angle(0, round(angle_actuel,1))



print("START")

tourner(CENTRE)
robot.set_motor(1,30)

time.sleep(1)



try:

    while True:

        s = tracker.get_status()

        L = s["left"]
        M = s["middle"]
        R = s["right"]


        etat = (L,M,R)

        print(etat)


        # =========================
        # parfaitement sur la ligne
        # =========================

        if etat == (1,1,1):

            correction *= 0.7
            vitesse = VITESSE_DROITE



        # =========================
        # trop à gauche
        # revenir à droite
        # angle plus petit
        # =========================

        elif etat == (0,1,1):

            correction -= 5
            vitesse = VITESSE_DROITE


        elif etat == (0,0,1):

            correction -= 12
            vitesse = VITESSE_VIRAGE



        # =========================
        # trop à droite
        # revenir à gauche
        # angle plus grand
        # =========================

        elif etat == (1,1,0):

            correction += 5
            vitesse = VITESSE_DROITE


        elif etat == (1,0,0):

            correction += 12
            vitesse = VITESSE_VIRAGE



        # =========================
        # perdu
        # =========================

        elif etat == (0,0,0):

            # continue dans le dernier sens
            if correction > 0:
                correction += 5
            else:
                correction -= 5

            vitesse = 20



        correction = limite(
            correction,
            -MAX_CORRECTION,
            MAX_CORRECTION
        )


        angle = CENTRE + correction


        tourner(angle)


        robot.set_motor(1,vitesse)


        time.sleep(0.03)



except KeyboardInterrupt:

    print("STOP")

    robot.stopper()
    servos.set_angle(0,CENTRE)
