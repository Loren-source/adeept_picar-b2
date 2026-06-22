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
angle_actuel=97

V_MAX=38
V_CORR=30
V_VIRAGE=24
V_PERTE=20

actif=False
dernier_angle=97
derniere_direction="centre"
temps_perte=None

def braquer(cible):
    global angle_actuel

    if abs(cible-angle_actuel)>3:
        if cible>angle_actuel:
            angle_actuel+=3
        else:
            angle_actuel-=3
    else:
        angle_actuel=cible

    servos.set_angle(0,angle_actuel)


def avance(angle,vitesse):
    global dernier_angle

    dernier_angle=angle
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


threading.Thread(target=clavier,daemon=True).start()


try:

    while True:

        if not actif:
            time.sleep(0.02)
            continue


        if ultra.get_distance()<200:
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


        # =====================
        # LIGNE DROITE
        # =====================

        if cap==(1,1,1):

            temps_perte=None
            derniere_direction="centre"

            avance(
                ANGLE_CENTRE,
                V_MAX
            )


        # =====================
        # GAUCHE
        # =====================

        elif cap==(1,1,0):

            temps_perte=None
            derniere_direction="gauche"

            avance(
                88,
                V_CORR
            )


        elif cap==(1,0,0):

            temps_perte=None
            derniere_direction="gauche"

            avance(
                78,
                V_VIRAGE
            )


        # =====================
        # DROITE
        # =====================

        elif cap==(0,1,1):

            temps_perte=None
            derniere_direction="droite"

            avance(
                106,
                V_CORR
            )


        elif cap==(0,0,1):

            temps_perte=None
            derniere_direction="droite"

            avance(
                116,
                V_VIRAGE
            )


        # =====================
        # TROU / VIRAGE FORT
        # =====================

        elif cap==(0,0,0):

            if temps_perte is None:
                temps_perte=time.time()


            # pendant 150 ms on garde la trajectoire

            if time.time()-temps_perte<0.15:

                avance(
                    dernier_angle,
                    V_PERTE
                )


            else:

                # seulement après vraie perte

                if derniere_direction=="gauche":
                    avance(75,18)

                elif derniere_direction=="droite":
                    avance(120,18)

                else:
                    avance(97,18)


        time.sleep(0.02)


except KeyboardInterrupt:
    pass

finally:
    robot.stopper()
    servos.set_angle(0,97)
