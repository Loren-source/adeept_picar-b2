#!/usr/bin/env python3
import time
import threading

from motor import RobotMotor
from ultra import Ultrasonic
from lineTracking import LineTracker
from servo import RobotServos

robot=RobotMotor()
ultra=Ultrasonic()
tracker=LineTracker()
servos=RobotServos()

# ===== REGLAGES =====

ANGLE_CENTRE=97

# corrections progressives
ANGLE_GAUCHE=86
ANGLE_GAUCHE_FORT=78

ANGLE_DROITE=108
ANGLE_DROITE_FORT=116

VITESSE_LIGNE=32
VITESSE_CORRECTION=27
VITESSE_VIRAGE=24
VITESSE_TROU=20
VITESSE_RECHERCHE=18

TEMPS_TROU=0.08

DISTANCE_STOP=200


# ===== VARIABLES =====

actif=False

angle_actuel=None

dernier_angle=ANGLE_CENTRE
derniere_direction="centre"

temps_000=None


# ===== COMMANDES =====

def braquer(angle):
    global angle_actuel

    if angle!=angle_actuel:
        servos.set_angle(0,angle)
        angle_actuel=angle


def avancer(angle,vitesse):
    global dernier_angle

    dernier_angle=angle

    braquer(angle)
    robot.set_motor(1,vitesse)


# ===== CLAVIER =====

def clavier():

    global actif

    while True:

        c=input().strip().upper()

        if c=="M":

            actif=True
            robot.stop_feux()
            print("START")


        elif c=="A":

            actif=False
            robot.stopper()
            print("STOP")


threading.Thread(target=clavier,daemon=True).start()


# ===== MAIN =====

try:

    while True:

        if not actif:
            time.sleep(0.02)
            continue


        if ultra.get_distance()<DISTANCE_STOP:

            robot.stop()
            actif=False
            continue


        cap=tracker.get_status()

        lecture=(
            cap["left"],
            cap["middle"],
            cap["right"]
        )


        print(lecture)


        # ==================
        # CENTRE
        # ==================

        if lecture==(1,1,1):

            temps_000=None

            # amortissement
            # on revient doucement au centre

            if dernier_angle<ANGLE_CENTRE:

                avancer(
                    92,
                    VITESSE_LIGNE
                )


            elif dernier_angle>ANGLE_CENTRE:

                avancer(
                    102,
                    VITESSE_LIGNE
                )


            else:

                avancer(
                    ANGLE_CENTRE,
                    VITESSE_LIGNE
                )


            derniere_direction="centre"



        # ==================
        # PART A DROITE
        # donc corrige gauche
        # ==================

        elif lecture==(1,1,0):

            temps_000=None
            derniere_direction="gauche"

            avancer(
                ANGLE_GAUCHE,
                VITESSE_CORRECTION
            )


        elif lecture==(1,0,0):

            temps_000=None
            derniere_direction="gauche"

            avancer(
                ANGLE_GAUCHE_FORT,
                VITESSE_VIRAGE
            )


        # ==================
        # PART A GAUCHE
        # donc corrige droite
        # ==================

        elif lecture==(0,1,1):

            temps_000=None
            derniere_direction="droite"

            avancer(
                ANGLE_DROITE,
                VITESSE_CORRECTION
            )


        elif lecture==(0,0,1):

            temps_000=None
            derniere_direction="droite"

            avancer(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )


        # ==================
        # TROU / PERTE
        # ==================

        elif lecture==(0,0,0):

            if temps_000 is None:

                temps_000=time.time()


            if time.time()-temps_000<TEMPS_TROU:

                avancer(
                    dernier_angle,
                    VITESSE_TROU
                )


            else:

                if derniere_direction=="gauche":

                    avancer(
                        ANGLE_GAUCHE_FORT,
                        VITESSE_TROU
                    )

                elif derniere_direction=="droite":

                    avancer(
                        ANGLE_DROITE_FORT,
                        VITESSE_TROU
                    )


        time.sleep(0.02)



except KeyboardInterrupt:

    pass


finally:

    robot.stopper()
    braquer(ANGLE_CENTRE)
    print("FIN")
