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

# 110 : robot part à droite -> tourner gauche
ANGLE_GAUCHE_LEGER=110
ANGLE_GAUCHE_FORT=125

# 011 : robot part à gauche -> tourner droite
ANGLE_DROITE_LEGER=84
ANGLE_DROITE_FORT=70

VITESSE_DROITE=35
VITESSE_CORRECTION=28
VITESSE_VIRAGE=22
VITESSE_RECHERCHE=18

DISTANCE_STOP=200

# ===== VARIABLES =====

actif=False

angle_actuel=None

dernier_angle=ANGLE_CENTRE
derniere_direction="centre"

temps_000=None


# ===== MOUVEMENT =====

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


# ===== PROGRAMME =====

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


        # ======================
        # CENTRE
        # ======================

        if cap==(1,1,1):

            temps_000=None
            derniere_direction="centre"

            avance(
                ANGLE_CENTRE,
                VITESSE_DROITE
            )


        # ======================
        # GAUCHE
        # ======================

        elif cap==(1,1,0):

            temps_000=None
            derniere_direction="gauche"

            avance(
                ANGLE_GAUCHE_LEGER,
                VITESSE_CORRECTION
            )


        elif cap==(1,0,0):

            temps_000=None
            derniere_direction="gauche"

            avance(
                ANGLE_GAUCHE_FORT,
                VITESSE_VIRAGE
            )


        # ======================
        # DROITE
        # ======================

        elif cap==(0,1,1):

            temps_000=None
            derniere_direction="droite"

            avance(
                ANGLE_DROITE_LEGER,
                VITESSE_CORRECTION
            )


        elif cap==(0,0,1):

            temps_000=None
            derniere_direction="droite"

            avance(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )


        # ======================
        # PERTE / POINTILLES
        # ======================

        elif cap==(0,0,0):

            if temps_000 is None:

                temps_000=time.time()


            # petite coupure de ligne
            if time.time()-temps_000<0.12:

                avance(
                    dernier_angle,
                    18
                )


            # vraie perte
            else:

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
                        VITESSE_RECHERCHE
                    )


        time.sleep(0.02)


except KeyboardInterrupt:

    pass


finally:

    robot.stopper()
    braquer(ANGLE_CENTRE)
    print("FIN")
