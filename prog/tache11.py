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

ANGLE_GAUCHE_LEGER=88
ANGLE_GAUCHE_FORT=78

ANGLE_DROITE_LEGER=106
ANGLE_DROITE_FORT=116

V_LIGNE=38
V_CORRECTION=32
V_VIRAGE=25
V_PERTE=20

actif=False
angle_actuel=None

dernier_angle=97
derniere_direction="centre"
temps_000=None


def braquer(a):
    global angle_actuel

    if angle_actuel!=a:
        servos.set_angle(0,a)
        angle_actuel=a


def avance(a,v):
    global dernier_angle

    dernier_angle=a

    braquer(a)
    robot.set_motor(1,v)


def clavier():
    global actif

    while True:
        c=input().upper()

        if c=="M":
            actif=True
            robot.stop_feux()
            print("START")

        elif c=="A":
            actif=False
            robot.stopper()
            print("STOP")


threading.Thread(target=clavier,daemon=True).start()


try:

    while True:

        if not actif:
            time.sleep(0.02)
            continue


        s=tracker.get_status()

        cap=(
            s["left"],
            s["middle"],
            s["right"]
        )


        print(cap)


        # ligne parfaite

        if cap==(1,1,1):

            temps_000=None
            derniere_direction="centre"

            avance(
                ANGLE_CENTRE,
                V_LIGNE
            )


        # commence à partir à droite
        # donc on ramène gauche

        elif cap==(1,1,0):

            temps_000=None
            derniere_direction="gauche"

            avance(
                ANGLE_GAUCHE_LEGER,
                V_CORRECTION
            )


        elif cap==(1,0,0):

            temps_000=None
            derniere_direction="gauche"

            avance(
                ANGLE_GAUCHE_FORT,
                V_VIRAGE
            )


        # commence à partir gauche
        # donc ramène droite

        elif cap==(0,1,1):

            temps_000=None
            derniere_direction="droite"

            avance(
                ANGLE_DROITE_LEGER,
                V_CORRECTION
            )


        elif cap==(0,0,1):

            temps_000=None
            derniere_direction="droite"

            avance(
                ANGLE_DROITE_FORT,
                V_VIRAGE
            )


        # blanc

        elif cap==(0,0,0):

            if temps_000 is None:
                temps_000=time.time()


            if time.time()-temps_000<0.12:

                avance(
                    dernier_angle,
                    V_PERTE
                )


            else:

                # chercher sans reculer

                if derniere_direction=="gauche":

                    avance(
                        ANGLE_GAUCHE_FORT,
                        18
                    )

                elif derniere_direction=="droite":

                    avance(
                        ANGLE_DROITE_FORT,
                        18
                    )


        time.sleep(0.02)


except KeyboardInterrupt:
    pass


finally:
    robot.stopper()
    servos.set_angle(0,97)
