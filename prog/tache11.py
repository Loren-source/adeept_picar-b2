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
ANGLE_DROITE_LEGER = 60
ANGLE_DROITE_FORT = 35


VITESSE_DROITE = 30
VITESSE_CORRECTION = 15
VITESSE_VIRAGE = 6
VITESSE_RECHERCHE = 8

DISTANCE_STOP = 200


# ==========================
# VARIABLES
# ==========================

actif = False

angle_actuel = None
dernier_angle = ANGLE_CENTRE
derniere_direction = "centre"


# ==========================
# MOTEUR + SERVO
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

    robot.set_motor(
        1,
        vitesse
    )


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
        # PART TROP A GAUCHE
        # → corriger DROITE
        # =====================

        elif cap == (0,1,1):

            derniere_direction = "droite"

            avance(
                ANGLE_DROITE_LEGER,
                VITESSE_CORRECTION
            )



        elif cap == (0,0,1):

            derniere_direction = "droite"

            avance(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )



        # =====================
        # PART TROP A DROITE
        # → corriger GAUCHE
        # =====================

        elif cap == (1,1,0):

            derniere_direction = "gauche"

            avance(
                ANGLE_GAUCHE_LEGER,
                VITESSE_CORRECTION
            )



        elif cap == (1,0,0):

            derniere_direction = "gauche"

            avance(
                ANGLE_GAUCHE_FORT,
                VITESSE_VIRAGE
            )



        # =====================
        # PERTE DE LIGNE
        # =====================

        elif cap == (0,0,0):


            if derniere_direction == "droite":

                # garde le braquage fort
                # mais avance doucement
                avance(
                    ANGLE_DROITE_FORT,
                    VITESSE_RECHERCHE
                )


            elif derniere_direction == "gauche":

                avance(
                    ANGLE_GAUCHE_FORT,
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
