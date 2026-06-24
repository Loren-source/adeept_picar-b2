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


# corrections normales
GAUCHE_LEGER = 111
DROITE_LEGER = 78


# virages serrés
GAUCHE_FORT = 128
DROITE_FORT = 55


VITESSE_LIGNE = 36
VITESSE_VIRAGE = 22
VITESSE_PERDU = 18


angle_actuel = CENTRE

dernier_sens = 0
compteur_virage = 0
perdu_count = 0

ligne_vue_recemment = True



# ==========================
# SERVO PROGRESSIF
# ==========================

def tourner(cible):

    global angle_actuel


    # virage fort = réaction rapide
    if cible == GAUCHE_FORT or cible == DROITE_FORT:

        angle_actuel = cible


    else:

        # conduite fluide
        angle_actuel = angle_actuel*0.45 + cible*0.55


    servos.set_angle(
        0,
        round(angle_actuel,1)
    )




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
        # LIGNE CENTREE
        # =====================

        if etat == (1,1,1):

            compteur_virage = 0
            perdu_count = 0

            ligne_vue_recemment = True


            cible = CENTRE
            vitesse = VITESSE_LIGNE





        # =====================
        # CORRECTION GAUCHE
        # =====================

        elif etat == (1,1,0):

            compteur_virage += 1
            perdu_count = 0

            dernier_sens = 1
            ligne_vue_recemment = False


            cible = GAUCHE_LEGER
            vitesse = VITESSE_LIGNE




        elif etat == (1,0,0):

            compteur_virage += 1
            perdu_count = 0

            dernier_sens = 1
            ligne_vue_recemment = False



            if compteur_virage > 5:

                cible = GAUCHE_FORT

            else:

                cible = 118


            vitesse = VITESSE_VIRAGE





        # =====================
        # CORRECTION DROITE
        # =====================

        elif etat == (0,1,1):

            compteur_virage += 1
            perdu_count = 0

            dernier_sens = -1
            ligne_vue_recemment = False


            cible = DROITE_LEGER
            vitesse = VITESSE_LIGNE





        elif etat == (0,0,1):

            compteur_virage += 1
            perdu_count = 0

            dernier_sens = -1
            ligne_vue_recemment = False



            if compteur_virage > 5:

                cible = DROITE_FORT

            else:

                cible = 70


            vitesse = VITESSE_VIRAGE






        # =====================
        # POINTILLES / PERTE
        # =====================

        elif etat == (0,0,0):

            perdu_count += 1



            # -----------------
            # POINTILLES
            # -----------------
            # on garde la direction

            if perdu_count < 25:


                cible = CENTRE

                vitesse = VITESSE_LIGNE




            # -----------------
            # VRAIE PERTE
            # -----------------

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
