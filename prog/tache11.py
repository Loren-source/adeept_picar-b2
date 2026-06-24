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
ANGLE_GAUCHE_MAX = 160

# DROITE physique
ANGLE_DROITE_LEGER = 75
ANGLE_DROITE_FORT = 55
ANGLE_DROITE_MAX = 35


VITESSE_DROITE = 30
VITESSE_CORRECTION = 22
VITESSE_VIRAGE = 15
VITESSE_RECHERCHE = 12


DISTANCE_STOP = 200


# nouveau
COMPTEUR_MAX = 10



# ==========================
# VARIABLES
# ==========================

actif = False
angle_actuel = None

dernier_angle = ANGLE_CENTRE
derniere_direction = "centre"

compteur_serre = 0



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

    global dernier_angle

    dernier_angle = angle

    braquer(angle)

    robot.set_motor(1, vitesse)




def sauvetage(angle):

    print("VIRAGE SERRE")

    robot.stopper()

    time.sleep(0.1)


    # petit recul
    robot.set_motor(1, -12)

    braquer(angle)

    time.sleep(0.25)


    # reprise
    robot.set_motor(1, 12)





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

            compteur_serre = 0

            avance(
                ANGLE_CENTRE,
                VITESSE_DROITE
            )






        # =====================
        # GAUCHE
        # =====================

        elif cap == (0,1,1):

            derniere_direction = "gauche"

            avance(
                ANGLE_GAUCHE_LEGER,
                VITESSE_CORRECTION
            )



        elif cap == (0,0,1):

            derniere_direction = "gauche"

            compteur_serre += 1


            if compteur_serre > COMPTEUR_MAX:

                sauvetage(
                    ANGLE_GAUCHE_MAX
                )

                compteur_serre = 0


            else:

                avance(
                    ANGLE_GAUCHE_FORT,
                    VITESSE_VIRAGE
                )







        # =====================
        # DROITE
        # =====================

        elif cap == (1,1,0):

            derniere_direction = "droite"

            avance(
                ANGLE_DROITE_LEGER,
                VITESSE_CORRECTION
            )




        elif cap == (1,0,0):

            derniere_direction = "droite"


            compteur_serre += 1


            if compteur_serre > COMPTEUR_MAX:


                sauvetage(
                    ANGLE_DROITE_MAX
                )

                compteur_serre = 0



            else:

                avance(
                    ANGLE_DROITE_FORT,
                    VITESSE_VIRAGE
                )








        # =====================
        # PERTE LIGNE
        # =====================

        elif cap == (0,0,0):


            if derniere_direction == "gauche":

                avance(
                    ANGLE_GAUCHE_MAX,
                    VITESSE_RECHERCHE
                )


            elif derniere_direction == "droite":


                avance(
                    ANGLE_DROITE_MAX,
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
