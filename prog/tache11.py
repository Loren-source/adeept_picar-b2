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

# GAUCHE
ANGLE_GAUCHE_LEGER = 125
ANGLE_GAUCHE_FORT = 145

# DROITE
ANGLE_DROITE_LEGER = 75
ANGLE_DROITE_FORT = 55


VITESSE_DROITE = 30
VITESSE_CORRECTION = 22
VITESSE_VIRAGE = 15
VITESSE_RECHERCHE = 10


DISTANCE_STOP = 200


# réglages intelligence virage
LIMITE_LEGER = 12
LIMITE_FORT = 8
LIMITE_PERTE = 10



# ==========================
# VARIABLES
# ==========================

actif = False

angle_actuel = None

derniere_direction = "centre"

compteur_leger = 0
compteur_fort = 0
compteur_perte = 0



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
        # TOUT DROIT
        # =====================

        if cap == (1,1,1):

            compteur_leger = 0
            compteur_fort = 0
            compteur_perte = 0


            avance(
                ANGLE_CENTRE,
                VITESSE_DROITE
            )





        # =====================
        # DROITE LEGER 011
        # =====================

        elif cap == (0,1,1):

            compteur_leger += 1
            compteur_fort = 0
            compteur_perte = 0


            derniere_direction = "droite"



            if compteur_leger < LIMITE_LEGER:

                avance(
                    ANGLE_DROITE_LEGER,
                    VITESSE_CORRECTION
                )

            else:

                # virage droite qui dure :
                # on anticipe

                avance(
                    ANGLE_DROITE_FORT,
                    VITESSE_VIRAGE
                )






        # =====================
        # DROITE FORT 001
        # =====================

        elif cap == (0,0,1):

            compteur_fort += 1
            compteur_perte = 0


            derniere_direction = "droite"



            if compteur_fort < LIMITE_FORT:

                avance(
                    ANGLE_DROITE_FORT,
                    VITESSE_VIRAGE
                )


            else:

                avance(
                    ANGLE_DROITE_FORT,
                    VITESSE_RECHERCHE
                )








        # =====================
        # GAUCHE LEGER 110
        # =====================

        elif cap == (1,1,0):

            compteur_leger += 1
            compteur_fort = 0
            compteur_perte = 0


            derniere_direction = "gauche"



            if compteur_leger < LIMITE_LEGER:

                avance(
                    ANGLE_GAUCHE_LEGER,
                    VITESSE_CORRECTION
                )


            else:

                avance(
                    ANGLE_GAUCHE_FORT,
                    VITESSE_VIRAGE
                )








        # =====================
        # GAUCHE FORT 100
        # =====================

        elif cap == (1,0,0):

            compteur_fort += 1
            compteur_perte = 0


            derniere_direction = "gauche"



            if compteur_fort < LIMITE_FORT:


                avance(
                    ANGLE_GAUCHE_FORT,
                    VITESSE_VIRAGE
                )


            else:


                avance(
                    ANGLE_GAUCHE_FORT,
                    VITESSE_RECHERCHE
                )








        # =====================
        # PERTE / POINTILLES
        # =====================

        elif cap == (0,0,0):

            compteur_perte += 1



            # petit trou blanc du parcours

            if compteur_perte < LIMITE_PERTE:


                avance(
                    ANGLE_CENTRE,
                    VITESSE_RECHERCHE
                )



            # vraie perte de ligne

            else:


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
