#!/usr/bin/env python3

import time

from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker


robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()


# ==========================
# REGLAGES
# ==========================

CENTRE = 97


# corrections légères
GAUCHE_LEGER = 112
DROITE_LEGER = 78


# virages serrés
GAUCHE_FORT = 128
DROITE_FORT = 55


# vitesses optimisées
VITESSE_LIGNE = 32
VITESSE_VIRAGE = 18
VITESSE_PERDU = 15


angle_actuel = CENTRE

dernier_sens = 0
compteur_virage = 0
perdu_count = 0



# ==========================
# SERVO PROGRESSIF
# ==========================

def tourner(cible):

    global angle_actuel

    # virage serré = réaction immédiate
    if cible == GAUCHE_FORT or cible == DROITE_FORT:
        angle_actuel = cible

    else:
        angle_actuel = angle_actuel*0.55 + cible*0.45


    servos.set_angle(
        0,
        round(angle_actuel,1)
    )



# ==========================
# START
# ==========================

print("START")

tourner(CENTRE)

robot.set_motor(1,30)

time.sleep(1)



try:

    while True:


        s = tracker.get_status()

        etat = (
            s["left"],
            s["middle"],
            s["right"]
        )


        print(etat)



        # =====================
        # LIGNE DROITE
        # =====================

        if etat == (1,1,1):

            compteur_virage = 0
            perdu_count = 0

            cible = CENTRE
            vitesse = VITESSE_LIGNE




        # =====================
        # VIRAGE GAUCHE
        # =====================

        elif etat == (1,1,0):

            compteur_virage += 1
            perdu_count = 0

            dernier_sens = 1


            cible = GAUCHE_LEGER

            # ralentir dès l'entrée
            vitesse = VITESSE_VIRAGE




        elif etat == (1,0,0):

            compteur_virage += 1
            perdu_count = 0

            dernier_sens = 1


            if compteur_virage > 3:
                cible = GAUCHE_FORT

            else:
                cible = 118


            vitesse = VITESSE_VIRAGE




        # =====================
        # VIRAGE DROITE
        # =====================

        elif etat == (0,1,1):

            compteur_virage += 1
            perdu_count = 0

            dernier_sens = -1


            cible = DROITE_LEGER

            # ralentir AVANT virage serré
            vitesse = VITESSE_VIRAGE




        elif etat == (0,0,1):

            compteur_virage += 1
            perdu_count = 0

            dernier_sens = -1


            if compteur_virage > 3:
                cible = DROITE_FORT

            else:
                cible = 70


            vitesse = VITESSE_VIRAGE





        # =====================
        # POINTILLES / PERTE LIGNE
        # =====================

        elif etat == (0,0,0):

            perdu_count += 1


            # petit trou = pointillés
            if perdu_count < 12:

                cible = CENTRE
                vitesse = VITESSE_LIGNE



            # vraie perte de ligne
            else:

                if dernier_sens == 1:

                    cible = GAUCHE_FORT


                elif dernier_sens == -1:

                    cible = DROITE_FORT


                else:

                    cible = CENTRE


                vitesse = VITESSE_PERDU





        tourner(cible)


        robot.set_motor(
            1,
            vitesse
        )


        time.sleep(0.025)





except KeyboardInterrupt:

    print("STOP")

    robot.stopper()

    servos.set_angle(0,CENTRE)
