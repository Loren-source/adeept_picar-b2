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

ANGLE_CENTRE=97

# 125 = gauche
ANGLE_GAUCHE=118
ANGLE_GAUCHE_FORT=125

# 70 = droite
ANGLE_DROITE=76
ANGLE_DROITE_FORT=70

VITESSE_DROITE=35
VITESSE_CORRECTION=28
VITESSE_VIRAGE=20
VITESSE_RECHERCHE=20

DISTANCE_STOP=200

actif=False
angle_actuel=None
derniere_direction="centre"


def braquer(angle):
    global angle_actuel

    if angle_actuel!=angle:
        servos.set_angle(0,angle)
        angle_actuel=angle


def avance(angle,vitesse):

    braquer(angle)
    robot.set_motor(1,vitesse)


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


try:

    while True:

        if not actif:

            time.sleep(0.02)
            continue


        if ultra.get_distance()<DISTANCE_STOP:

            robot.stop()
            actif=False
            continue


        s=tracker.get_status()

        cap=(
            s["left"],
            s["middle"],
            s["right"]
        )


        print(cap)


        # ===================
        # LIGNE CENTREE
        # ===================

        if cap==(1,1,1):

            derniere_direction="centre"

            avance(
                ANGLE_CENTRE,
                VITESSE_DROITE
            )


        # ===================
        # GAUCHE
        # ===================

        elif cap==(1,1,0):

            derniere_direction="gauche"

            avance(
                ANGLE_GAUCHE,
                VITESSE_CORRECTION
            )


        elif cap==(1,0,0):

            derniere_direction="gauche"

            avance(
                ANGLE_GAUCHE_FORT,
                VITESSE_VIRAGE
            )


        # ===================
        # DROITE
        # ===================

        elif cap==(0,1,1):

            derniere_direction="droite"

            avance(
                ANGLE_DROITE,
                VITESSE_CORRECTION
            )


        elif cap==(0,0,1):

            derniere_direction="droite"

            avance(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )


        # ===================
        # PERTE LIGNE
        # ===================

        elif cap==(0,0,0):

            if derniere_direction=="gauche":

                avance(
                    ANGLE_GAUCHE_FORT,
                    VITESSE_RECHERCHE
                )


            elif derniere_direction=="droite":

                avance(
                    ANGLE_DROITE_FORT,
                    VITESSE_RECHERCHE
                )


            else:

                avance(
                    ANGLE_CENTRE,
                    15
                )


        time.sleep(0.02)


except KeyboardInterrupt:

    pass


finally:

    robot.stopper()
    braquer(ANGLE_CENTRE)
    print("FIN")
