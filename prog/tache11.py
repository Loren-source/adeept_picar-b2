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

# gauche
ANGLE_GAUCHE_LEGER = 120
ANGLE_GAUCHE_FORT = 155

# droite
ANGLE_DROITE_LEGER = 75
ANGLE_DROITE_FORT = 40


VITESSE_LIGNE = 32
VITESSE_CORRECTION = 22
VITESSE_VIRAGE = 13
VITESSE_RECHERCHE = 10


DISTANCE_STOP = 200


# ==========================
# VARIABLES
# ==========================

actif = False
angle_actuel = None

derniere_direction = "centre"

# compteur de maintien virage
memoire_virage = 0


# ==========================
# COMMANDES
# ==========================

def braquer(angle):
    global angle_actuel

    if angle != angle_actuel:
        servos.set_angle(0, angle)
        angle_actuel = angle



def avance(angle, vitesse):

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
# BOUCLE PRINCIPALE
# ==========================


try:

    while True:


        if not actif:
            time.sleep(0.02)
            continue



        # obstacle
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



        # ======================
        # CENTRE SEUL
        # ======================

        if cap == (0,1,0):

            derniere_direction = "centre"
            memoire_virage = 0

            avance(
                ANGLE_CENTRE,
                VITESSE_LIGNE
            )



        # ======================
        # TOUT NOIR
        # ligne large
        # ======================

        elif cap == (1,1,1):

            if memoire_virage > 0:


                if derniere_direction == "gauche":

                    avance(
                        ANGLE_GAUCHE_LEGER,
                        VITESSE_CORRECTION
                    )


                elif derniere_direction == "droite":

                    avance(
                        ANGLE_DROITE_LEGER,
                        VITESSE_CORRECTION
                    )


                memoire_virage -= 1


            else:

                avance(
                    ANGLE_CENTRE,
                    VITESSE_LIGNE
                )



        # ======================
        # GAUCHE
        # ======================

        elif cap in [
            (1,1,0),
            (1,0,0)
        ]:

            derniere_direction = "gauche"
            memoire_virage = 15


            avance(
                ANGLE_GAUCHE_FORT,
                VITESSE_VIRAGE
            )



        # ======================
        # DROITE
        # ======================

        elif cap in [
            (0,1,1),
            (0,0,1)
        ]:


            derniere_direction = "droite"
            memoire_virage = 15


            avance(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )




        # ======================
        # PERTE LIGNE
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
                    ANGLE_CENTRE,
                    VITESSE_RECHERCHE
                )



        time.sleep(0.015)



except KeyboardInterrupt:
    pass


finally:

    robot.stopper()
    braquer(ANGLE_CENTRE)
    print("FIN")
