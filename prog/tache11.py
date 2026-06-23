#!/usr/bin/env python3

import time
import threading

from motor import RobotMotor
from ultra import Ultrasonic
from lineTracking import LineTracker
from servo import RobotServos


robot = RobotMotor()
ultra = Ultrasonic()
tracker = LineTracker()
servos = RobotServos()


# ==========================
# REGLAGES
# ==========================

ANGLE_CENTRE = 97

# GAUCHE physique
ANGLE_GAUCHE_LEGER = 125
ANGLE_GAUCHE_FORT = 145

# DROITE physique
ANGLE_DROITE_LEGER = 75
ANGLE_DROITE_FORT = 55


VITESSE_DROITE = 30
VITESSE_CORRECTION = 22
VITESSE_VIRAGE = 15
VITESSE_RECHERCHE = 12

DISTANCE_STOP = 200


# ==========================
# VARIABLES
# ==========================

actif = False

angle_actuel = None

dernier_angle = ANGLE_CENTRE
derniere_direction = "centre"

# compteur parcours :
# 1 = gauche
# 2 = droite
# 3 = gauche

nombre_virages = 0
dernier_gros_virage = 0



# ==========================
# MOTEURS
# ==========================

def braquer(angle):

    global angle_actuel

    if angle_actuel != angle:

        servos.set_angle(0, angle)

        print("[CH00] →", angle, "°")

        angle_actuel = angle



def avance(angle, vitesse):

    global dernier_angle

    dernier_angle = angle

    braquer(angle)

    robot.set_motor(1, vitesse)



# ==========================
# CLAVIER
# ==========================

def clavier():

    global actif

    while True:

        c = input().strip().upper()


        if c == "M":

            actif = True

            print("START")


        elif c == "A":

            actif = False

            robot.stopper()

            print("STOP")



threading.Thread(
    target=clavier,
    daemon=True
).start()



# ==========================
# PROGRAMME PRINCIPAL
# ==========================

try:

    while True:


        if not actif:

            time.sleep(0.02)

            continue



        # obstacle

        if ultra.get_distance() < DISTANCE_STOP:

            robot.stopper()

            actif = False

            continue



        s = tracker.get_status()


        cap = (
            s["left"],
            s["middle"],
            s["right"]
        )


        print(cap)



        # =====================
        # TOUT DROIT
        # =====================

        if cap == (1,1,1):

            avance(
                ANGLE_CENTRE,
                VITESSE_DROITE
            )




        # =====================
        # PETITE CORRECTION GAUCHE
        # =====================


        elif cap == (0,1,1):

            derniere_direction = "gauche"

            avance(
                ANGLE_GAUCHE_LEGER,
                VITESSE_CORRECTION
            )




        # =====================
        # PETITE CORRECTION DROITE
        # =====================


        elif cap == (1,1,0):

            derniere_direction = "droite"

            avance(
                ANGLE_DROITE_LEGER,
                VITESSE_CORRECTION
            )





        # =====================
        # GROS VIRAGES DU PARCOURS
        # =====================

        elif cap == (0,0,1) or cap == (1,0,0):


            # éviter de compter 50 fois le même virage

            if time.time() - dernier_gros_virage > 1.5:


                nombre_virages += 1

                dernier_gros_virage = time.time()


                print(
                    "===== VIRAGE",
                    nombre_virages,
                    "====="
                )



            # =====================
            # VIRAGE 1 : GAUCHE
            # =====================

            if nombre_virages == 1:


                derniere_direction = "gauche"


                avance(
                    ANGLE_GAUCHE_FORT,
                    VITESSE_VIRAGE
                )



            # =====================
            # VIRAGE 2 : DROITE
            # =====================

            elif nombre_virages == 2:


                derniere_direction = "droite"


                avance(
                    ANGLE_DROITE_FORT,
                    VITESSE_VIRAGE
                )



            # =====================
            # VIRAGE 3 : GAUCHE
            # =====================

            elif nombre_virages == 3:


                derniere_direction = "gauche"


                avance(
                    ANGLE_GAUCHE_FORT,
                    VITESSE_VIRAGE
                )


            else:


                avance(
                    dernier_angle,
                    VITESSE_VIRAGE
                )





        # =====================
        # PERTE DE LIGNE
        # =====================


        elif cap == (0,0,0):


            if derniere_direction == "gauche":


                avance(
                    ANGLE_GAUCHE_FORT,
                    VITESSE_RECHERCHE
                )



            elif derniere_direction == "droite":


                avance(
                    ANGLE_DROITE_FORT,
                    VITESSE_RECHERCHE
                )



            else:


                avance(
                    ANGLE_CENTRE,
                    VITESSE_RECHERCHE
                )



        time.sleep(0.02)




except KeyboardInterrupt:

    pass



finally:

    robot.stopper()

    braquer(ANGLE_CENTRE)

    print("FIN")
