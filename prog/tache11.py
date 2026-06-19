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

ANGLE_GAUCHE_LEGER=88
ANGLE_GAUCHE_FORT=78

ANGLE_DROITE_LEGER=106
ANGLE_DROITE_FORT=118

ANGLE_RECH_GAUCHE=70
ANGLE_RECH_DROITE=125

VITESSE_LIGNE=38
VITESSE_CORRECTION=30
VITESSE_VIRAGE=22
VITESSE_TROU=20
VITESSE_RECHERCHE=18

TEMPS_TROU=0.15
TEMPS_SORTIE=0.12

DISTANCE_STOP=200


# ===== VARIABLES =====

actif=False
etat="SUIVI"

angle_actuel=None

dernier_angle=ANGLE_CENTRE
dernier_virage="centre"

debut_000=None
debut_sortie=None


# ===== MOTEUR / SERVO =====

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


def reculer(angle,vitesse):
    braquer(angle)
    robot.set_motor(-1,vitesse)


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


threading.Thread(
    target=clavier,
    daemon=True
).start()


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

        print(lecture,etat)


        # =========================
        # RECHERCHE
        # =========================

        if etat=="RECHERCHE":

            if dernier_virage=="gauche":
                reculer(
                    ANGLE_RECH_GAUCHE,
                    VITESSE_RECHERCHE
                )

            elif dernier_virage=="droite":
                reculer(
                    ANGLE_RECH_DROITE,
                    VITESSE_RECHERCHE
                )

            else:
                reculer(
                    ANGLE_CENTRE,
                    VITESSE_RECHERCHE
                )


            if lecture!=(0,0,0):
                etat="SUIVI"
                debut_000=None

            continue



        # =========================
        # SORTIE VIRAGE
        # =========================

        if etat=="SORTIE":

            avancer(
                dernier_angle,
                VITESSE_CORRECTION
            )

            if time.time()-debut_sortie>TEMPS_SORTIE:

                etat="SUIVI"

            continue



        # =========================
        # SUIVI
        # =========================


        if lecture==(1,1,1):

            debut_000=None

            if dernier_virage!="centre":

                debut_sortie=time.time()
                etat="SORTIE"

            else:

                avancer(
                    ANGLE_CENTRE,
                    VITESSE_LIGNE
                )


        elif lecture==(1,1,0):

            debut_000=None
            dernier_virage="gauche"

            avancer(
                ANGLE_GAUCHE_LEGER,
                VITESSE_CORRECTION
            )


        elif lecture==(1,0,0):

            debut_000=None
            dernier_virage="gauche"

            avancer(
                ANGLE_GAUCHE_FORT,
                VITESSE_VIRAGE
            )


        elif lecture==(0,1,1):

            debut_000=None
            dernier_virage="droite"

            avancer(
                ANGLE_DROITE_LEGER,
                VITESSE_CORRECTION
            )


        elif lecture==(0,0,1):

            debut_000=None
            dernier_virage="droite"

            avancer(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )


        elif lecture==(0,0,0):

            if debut_000 is None:
                debut_000=time.time()

            if time.time()-debut_000<TEMPS_TROU:

                avancer(
                    dernier_angle,
                    VITESSE_TROU
                )

            else:

                etat="RECHERCHE"


        time.sleep(0.02)


except KeyboardInterrupt:
    pass

finally:
    robot.stopper()
    braquer(ANGLE_CENTRE)
    print("FIN")
