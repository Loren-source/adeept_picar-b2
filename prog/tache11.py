import time

from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker


robot = RobotMotor()
servo = RobotServos()
tracker = LineTracker()


# =========================
# REGLAGES PICAR-B
# =========================

CENTRE = 97

GAUCHE_LEGER = 80
GAUCHE_FORT = 55

DROITE_LEGER = 115
DROITE_FORT = 140


VITESSE_RAPIDE = 45
VITESSE_VIRAGE = 32
VITESSE_RECUP = 25


angle_actuel = CENTRE
dernier_cote = 0
# -1 gauche
#  1 droite


# =========================
# SERVO FLUIDE
# =========================

def tourner(cible):

    global angle_actuel

    # filtre pour éviter les coups secs
    angle_actuel = angle_actuel*0.65 + cible*0.35

    servo.set_angle(0, angle_actuel)



# =========================
# BOUCLE PRINCIPALE
# =========================

print("START")

servo.set_angle(0, CENTRE)
robot.set_motor(1, 30)

time.sleep(1)


try:

    while True:


        data = tracker.get_status()

        L = data["left"]
        M = data["middle"]
        R = data["right"]

        etat = (L,M,R)

        print(etat)



        # ========================
        # Pleine ligne noire
        # ========================

        if etat == (1,1,1):

            tourner(CENTRE)
            robot.set_motor(1,VITESSE_RAPIDE)



        # ========================
        # Ligne part à gauche
        # ========================

        elif etat == (1,1,0):

            dernier_cote = -1

            tourner(GAUCHE_LEGER)
            robot.set_motor(1,VITESSE_VIRAGE)



        elif etat == (1,0,0):

            dernier_cote = -1

            tourner(GAUCHE_FORT)
            robot.set_motor(1,VITESSE_RECUP)




        # ========================
        # Ligne part à droite
        # ========================

        elif etat == (0,1,1):

            dernier_cote = 1

            tourner(DROITE_LEGER)
            robot.set_motor(1,VITESSE_VIRAGE)



        elif etat == (0,0,1):

            dernier_cote = 1

            tourner(DROITE_FORT)
            robot.set_motor(1,VITESSE_RECUP)



        # ========================
        # Ligne perdue
        # ========================

        elif etat == (0,0,0):

            robot.set_motor(1,22)


            if dernier_cote == -1:

                tourner(GAUCHE_FORT)


            elif dernier_cote == 1:

                tourner(DROITE_FORT)


            else:

                tourner(CENTRE)



        time.sleep(0.02)



except KeyboardInterrupt:

    robot.stopper()

    servo.set_angle(0,CENTRE)
