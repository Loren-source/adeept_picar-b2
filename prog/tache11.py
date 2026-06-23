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
ANGLE_DROITE_LEGER = 75
ANGLE_DROITE_FORT = 55


VITESSE_DROITE = 30
VITESSE_CORRECTION = 22
VITESSE_VIRAGE = 15
VITESSE_RECHERCHE = 12


DISTANCE_STOP = 200


# après combien de lectures en léger on force le virage
LIMITE_LEGER = 6


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
        # TOUT DROIT
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
        # capteurs inversés
        # =====================

        elif cap == (0,1,1):

            derniere_direction = "droite"

            compteur_droite += 1
            compteur_gauche = 0


            # début virage
            if compteur_droite < LIMITE_LEGER:

                avance(
                    ANGLE_DROITE_LEGER,
                    VITESSE_CORRECTION
                )


            # si le virage continue => tourner plus
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
        # capteurs inversés
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
        # PERTE LIGNE
        # =====================

        elif cap == (0,0,0):


            # IMPORTANT :
            # on continue le virage
            # on ne remet PAS à 97°

            if derniere_direction == "droite":


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
