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
ANGLE_GAUCHE_FORT = 150

ANGLE_DROITE_LEGER = 75
ANGLE_DROITE_FORT = 50


VITESSE_DROITE = 28
VITESSE_CORRECTION = 22
VITESSE_VIRAGE = 16
VITESSE_RECHERCHE = 14

DISTANCE_STOP = 200


# mémoire virage
dernier_angle = ANGLE_CENTRE
derniere_direction = "centre"

temps_dernier_virage = 0
MEMOIRE_VIRAGE = 0.45


actif = False
angle_actuel = None


# ==========================
# DIRECTION
# ==========================

def braquer(angle):
    global angle_actuel

    if angle != angle_actuel:
        servos.set_angle(0, angle)
        angle_actuel = angle


def avance(angle, vitesse):
    global dernier_angle

    dernier_angle = angle

    braquer(angle)
    robot.set_motor(1, vitesse)



# ==========================
# CLAVIER
# ==========================

def clavier():
    global actif

    while True:

        c = input().upper()

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
# MAIN
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


        maintenant = time.time()


        # ======================
        # LIGNE COMPLETE
        # ======================

        if cap == (1,1,1):

            # si on sort d'un virage
            # on continue encore un peu
            if maintenant - temps_dernier_virage < MEMOIRE_VIRAGE:

                avance(
                    dernier_angle,
                    VITESSE_CORRECTION
                )

            else:

                avance(
                    ANGLE_CENTRE,
                    VITESSE_DROITE
                )


        # ======================
        # GAUCHE
        # ======================

        elif cap == (0,1,1):

            derniere_direction = "gauche"
            temps_dernier_virage = maintenant

            avance(
                ANGLE_GAUCHE_LEGER,
                VITESSE_CORRECTION
            )


        elif cap == (0,0,1):

            derniere_direction = "gauche"
            temps_dernier_virage = maintenant

            avance(
                ANGLE_GAUCHE_FORT,
                VITESSE_VIRAGE
            )



        # ======================
        # DROITE
        # ======================

        elif cap == (1,1,0):

            derniere_direction = "droite"
            temps_dernier_virage = maintenant

            avance(
                ANGLE_DROITE_LEGER,
                VITESSE_CORRECTION
            )


        elif cap == (1,0,0):

            derniere_direction = "droite"
            temps_dernier_virage = maintenant

            avance(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )



        # ======================
        # PERDU
        # ======================

        elif cap == (0,0,0):

            if derniere_direction == "gauche":

                avance(
                    ANGLE_GAUCHE_FORT,
                    VITESSE_RECHERCHE
                )


            elif derniere_direction == "droite":

                avance(
                    ANGLE_DROITE_FORT,
                    VITESSE_RECHERCHE
                )


            else:

                avance(
                    dernier_angle,
                    VITESSE_RECHERCHE
                )



        time.sleep(0.015)



except KeyboardInterrupt:
    pass


finally:

    robot.stopper()
    braquer(ANGLE_CENTRE)

    print("FIN")
