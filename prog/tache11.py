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

# GAUCHE physique (ne pas toucher)
ANGLE_GAUCHE_LEGER = 125
ANGLE_GAUCHE_FORT = 145

# DROITE physique (corrigé 2e virage)
ANGLE_DROITE_LEGER = 70
ANGLE_DROITE_FORT = 35


VITESSE_DROITE = 30
VITESSE_CORRECTION = 22
VITESSE_VIRAGE = 15
VITESSE_RECHERCHE = 15


DISTANCE_STOP = 200


# nombre de lectures avant virage fort
LIMITE_LEGER = 5


# ==========================
# VARIABLES
# ==========================

actif = False

angle_actuel = None

derniere_direction = "centre"

compteur_droite = 0
compteur_gauche = 0


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



        # =====================
        # LIGNE DROITE
        # =====================

        if cap == (1,1,1):

            compteur_droite = 0
            compteur_gauche = 0

            derniere_direction = "centre"

            avance(
                ANGLE_CENTRE,
                VITESSE_DROITE
            )



        # =====================
        # VIRAGE DROITE
        # =====================

        elif cap == (0,1,1):

            derniere_direction = "droite"

            compteur_droite += 1
            compteur_gauche = 0


            if compteur_droite < LIMITE_LEGER:

                avance(
                    ANGLE_DROITE_LEGER,
                    VITESSE_CORRECTION
                )


            else:

                avance(
                    ANGLE_DROITE_FORT,
                    VITESSE_VIRAGE
                )



        elif cap == (0,0,1):

            derniere_direction = "droite"


            avance(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )



        # =====================
        # VIRAGE GAUCHE
        # =====================

        elif cap == (1,1,0):

            derniere_direction = "gauche"

            compteur_gauche += 1
            compteur_droite = 0


            if compteur_gauche < LIMITE_LEGER:

                avance(
                    ANGLE_GAUCHE_LEGER,
                    VITESSE_CORRECTION
                )


            else:

                avance(
                    ANGLE_GAUCHE_FORT,
                    VITESSE_VIRAGE
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

                # continue le 2e virage
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

                # uniquement les pointillés droits

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
