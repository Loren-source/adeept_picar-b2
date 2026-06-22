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

ANGLE_GAUCHE_LEGER=82
ANGLE_GAUCHE_FORT=70

ANGLE_DROITE_LEGER=115
ANGLE_DROITE_FORT=125

ANGLE_RECH_GAUCHE=70
ANGLE_RECH_DROITE=125

VITESSE_DROITE=30
VITESSE_CORRECTION=28
VITESSE_VIRAGE=25
VITESSE_RECHERCHE=18

DISTANCE_STOP=200

actif=False
etat="SUIVI"

angle_actuel=None
dernier_angle=ANGLE_CENTRE

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


def recule(a,v):

    braquer(a)
    robot.set_motor(-1,v)



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

        etat_cap=(
            s["left"],
            s["middle"],
            s["right"]
        )


        print(etat_cap)



        # ==================
        # LIGNE CENTREE
        # ==================

        if etat_cap==(1,1,1):

            temps_000=None
            derniere_direction="centre"

            avance(
                ANGLE_CENTRE,
                VITESSE_DROITE
            )



        # ==================
        # PART VERS DROITE
        # DONC CORRECTION GAUCHE
        # ==================

        elif etat_cap==(1,1,0):

            temps_000=None
            derniere_direction="gauche"

            avance(
                ANGLE_GAUCHE_LEGER,
                VITESSE_CORRECTION
            )



        elif etat_cap==(1,0,0):

            temps_000=None
            derniere_direction="gauche"

            avance(
                ANGLE_GAUCHE_FORT,
                VITESSE_VIRAGE
            )



        # ==================
        # PART VERS GAUCHE
        # DONC CORRECTION DROITE
        # ==================

        elif etat_cap==(0,1,1):

            temps_000=None
            derniere_direction="droite"

            avance(
                ANGLE_DROITE_LEGER,
                VITESSE_CORRECTION
            )



        elif etat_cap==(0,0,1):

            temps_000=None
            derniere_direction="droite"

            avance(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )



        # ==================
        # BLANC COMPLET
        # ==================

        elif etat_cap==(0,0,0):


            if temps_000 is None:

                temps_000=time.time()



            # petit trou ou début de perte
            if time.time()-temps_000<0.05:

                avance(
                    dernier_angle,
                    20
                )


            # vraie perte
            else:


                if derniere_direction=="gauche":

                    recule(
                        ANGLE_RECH_GAUCHE,
                        VITESSE_RECHERCHE
                    )


                elif derniere_direction=="droite":

                    recule(
                        ANGLE_RECH_DROITE,
                        VITESSE_RECHERCHE
                    )


                else:

                    recule(
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
