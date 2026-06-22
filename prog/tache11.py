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

# 110 -> tourner gauche
ANGLE_GAUCHE_LEGER=110
ANGLE_GAUCHE_FORT=125

# 011 -> tourner droite
ANGLE_DROITE_LEGER=84
ANGLE_DROITE_FORT=70

VITESSE_DROITE=35
VITESSE_CORRECTION=28
VITESSE_VIRAGE=20
VITESSE_RECHERCHE=18

DISTANCE_STOP=200

actif=False
angle_actuel=None

dernier_angle=ANGLE_CENTRE
derniere_direction="centre"

temps_000=None

compteur_gauche=0
compteur_droite=0


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


        # ==================
        # LIGNE DROITE
        # ==================

        if cap==(1,1,1):

            temps_000=None

            compteur_gauche=0
            compteur_droite=0

            derniere_direction="centre"

            avance(
                ANGLE_CENTRE,
                VITESSE_DROITE
            )


        # ==================
        # VIRAGE GAUCHE
        # ==================

        elif cap==(1,1,0):

            temps_000=None

            compteur_gauche+=1
            compteur_droite=0

            derniere_direction="gauche"


            # longtemps sur 110 = virage
            if compteur_gauche>5:

                avance(
                    ANGLE_GAUCHE_FORT,
                    VITESSE_VIRAGE
                )

            else:

                avance(
                    ANGLE_GAUCHE_LEGER,
                    VITESSE_CORRECTION
                )


        elif cap==(1,0,0):

            temps_000=None

            compteur_gauche=10
            compteur_droite=0

            derniere_direction="gauche"

            avance(
                ANGLE_GAUCHE_FORT,
                VITESSE_VIRAGE
            )


        # ==================
        # VIRAGE DROITE
        # ==================

        elif cap==(0,1,1):

            temps_000=None

            compteur_droite+=1
            compteur_gauche=0

            derniere_direction="droite"


            if compteur_droite>5:

                avance(
                    ANGLE_DROITE_FORT,
                    VITESSE_VIRAGE
                )

            else:

                avance(
                    ANGLE_DROITE_LEGER,
                    VITESSE_CORRECTION
                )


        elif cap==(0,0,1):

            temps_000=None

            compteur_droite=10
            compteur_gauche=0

            derniere_direction="droite"

            avance(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )


        # ==================
        # TROU / POINTILLES
        # ==================

        elif cap==(0,0,0):

            if temps_000 is None:

                temps_000=time.time()


            # petite interruption
            if time.time()-temps_000<0.15:

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
