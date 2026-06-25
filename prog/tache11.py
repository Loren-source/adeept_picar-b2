#!/usr/bin/env python3

import time

from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker


robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()


# ==========================
# REGLAGES VALIDES
# ==========================

CENTRE = 97


# petites corrections
GAUCHE_LEGER = 112
DROITE_LEGER = 82


# vrais virages
GAUCHE_FORT = 128
DROITE_FORT = 65


# vitesses
VITESSE_LIGNE = 34
VITESSE_APPROCHE = 27
VITESSE_VIRAGE = 18
VITESSE_PERDU = 14


angle_actuel = CENTRE


dernier_sens = 0
# 1 = gauche
# -1 = droite


compteur_virage = 0

dernier_etat = (1,1,1)
compteur_perdu = 0



# ==========================
# SERVO FLUIDE
# ==========================

def tourner(cible):

    global angle_actuel


    # garde la fluidité qui marchait
    angle_actuel = angle_actuel*0.6 + cible*0.4


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



# ==========================
# BOUCLE
# ==========================

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
            compteur_perdu = 0


            cible = CENTRE
            vitesse = VITESSE_LIGNE




        # =====================
        # VIRAGE GAUCHE
        # =====================

        elif etat == (1,1,0):

            compteur_perdu = 0
            compteur_virage += 1

            dernier_sens = 1



            # anticipation virage
            if compteur_virage > 2:

                cible = GAUCHE_FORT
                vitesse = VITESSE_VIRAGE


            else:

                cible = GAUCHE_LEGER
                vitesse = VITESSE_APPROCHE




        elif etat == (1,0,0):

            compteur_perdu = 0

            compteur_virage += 2

            dernier_sens = 1



            cible = GAUCHE_FORT

            vitesse = VITESSE_VIRAGE





        # =====================
        # VIRAGE DROITE
        # =====================

        elif etat == (0,1,1):

            compteur_perdu = 0

            compteur_virage += 1

            dernier_sens = -1



            if compteur_virage > 2:

                cible = DROITE_FORT
                vitesse = VITESSE_VIRAGE


            else:

                cible = DROITE_LEGER
                vitesse = VITESSE_APPROCHE




        elif etat == (0,0,1):

            compteur_perdu = 0

            compteur_virage += 2

            dernier_sens = -1



            cible = DROITE_FORT

            vitesse = VITESSE_VIRAGE





        # =====================
        # POINTILLES OU PERTE
        # =====================

        elif etat == (0,0,0):


            compteur_perdu += 1



            # POINTILLES
            # il garde droit

            if dernier_etat == (1,1,1) and compteur_perdu < 25:


                cible = CENTRE

                vitesse = VITESSE_LIGNE




            # VRAIMENT PERDU
            else:


                if dernier_sens == 1:


                    cible = GAUCHE_FORT



                elif dernier_sens == -1:


                    cible = DROITE_FORT



                else:


                    cible = CENTRE



                vitesse = VITESSE_PERDU





        # =====================
        # ACTION
        # =====================

        tourner(cible)


        robot.set_motor(
            1,
            vitesse
        )




        # mémoire dernière ligne vue

        if etat != (0,0,0):

            dernier_etat = etat




        time.sleep(0.025)





except KeyboardInterrupt:


    print("STOP")


    robot.stopper()


    servos.set_angle(0,CENTRE)

