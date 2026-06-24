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

ANGLE_GAUCHE_LEGER = 125
ANGLE_GAUCHE_FORT = 155

ANGLE_DROITE_LEGER = 75
ANGLE_DROITE_FORT = 35


VITESSE_DROITE = 30
VITESSE_CORRECTION = 20
VITESSE_VIRAGE = 12
VITESSE_RECHERCHE = 10

DISTANCE_STOP = 200


SEUIL_VIRAGE_SERRE = 8


# ==========================
# VARIABLES
# ==========================

actif = False
angle_actuel = None

derniere_direction = "centre"

compteur_virage = 0


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

    braquer(angle)

    robot.set_motor(1, vitesse)



def reculer(angle):

    print("RECUL")

    braquer(angle)

    robot.set_motor(1, -12)

    time.sleep(0.25)

    robot.set_motor(1, 10)





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
# PROGRAMME
# ==========================

try:

    while True:


        if not actif:

            time.sleep(0.02)

            continue



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
        # DROIT
        # =====================

        if cap == (1,1,1):

            compteur_virage = 0

            avance(
                ANGLE_CENTRE,
                VITESSE_DROITE
            )



        # =====================
        # GAUCHE
        # =====================

        elif cap == (0,1,1):

            derniere_direction = "gauche"

            compteur_virage += 1


            if compteur_virage > SEUIL_VIRAGE_SERRE:

                avance(
                    ANGLE_GAUCHE_FORT,
                    VITESSE_VIRAGE
                )

            else:

                avance(
                    ANGLE_GAUCHE_LEGER,
                    VITESSE_CORRECTION
                )



        elif cap == (0,0,1):

            derniere_direction = "gauche"

            avance(
                ANGLE_GAUCHE_FORT,
                VITESSE_VIRAGE
            )




        # =====================
        # DROITE
        # =====================

        elif cap == (1,1,0):

            derniere_direction = "droite"

            compteur_virage += 1


            if compteur_virage > SEUIL_VIRAGE_SERRE:

                avance(
                    ANGLE_DROITE_FORT,
                    VITESSE_VIRAGE
                )

            else:

                avance(
                    ANGLE_DROITE_LEGER,
                    VITESSE_CORRECTION
                )



        elif cap == (1,0,0):

            derniere_direction = "droite"


            avance(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )





        # =====================
        # PERTE LIGNE
        # =====================

        elif cap == (0,0,0):


            if derniere_direction == "droite":

                reculer(
                    ANGLE_DROITE_FORT
                )


            elif derniere_direction == "gauche":

                reculer(
                    ANGLE_GAUCHE_FORT
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
