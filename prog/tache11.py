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


# corrections
GAUCHE_LEGER = 110
DROITE_LEGER = 84


# virages
GAUCHE_FORT = 123
DROITE_FORT = 71


VITESSE_LIGNE = 34
VITESSE_VIRAGE = 24
VITESSE_RECHERCHE = 10



angle_actuel = CENTRE


# mémoire direction
dernier_sens = 0
# gauche = 1
# droite = -1


compteur_virage = 0
compteur_perdu = 0


dernier_etat = (1,1,1)



# ==========================
# SERVO
# ==========================

def tourner(cible):

    global angle_actuel


    # filtre fluide
    angle_actuel = angle_actuel*0.7 + cible*0.3


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

time.sleep(0.7)




# ==========================
# LOOP
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
        # CENTRE / LIGNE LARGE
        # =====================

        if etat == (1,1,1):


            compteur_perdu = 0


            # garde mémoire du virage

            if compteur_virage > 0:


                if dernier_sens == 1:

                    cible = 104


                elif dernier_sens == -1:

                    cible = 90


                else:

                    cible = CENTRE


                compteur_virage -= 1



            else:

                cible = CENTRE



            vitesse = VITESSE_LIGNE





        # =====================
        # GAUCHE LEGER
        # =====================

        elif etat == (1,1,0):


            compteur_perdu = 0

            dernier_sens = 1


            compteur_virage = 8


            cible = GAUCHE_LEGER


            vitesse = 30





        # =====================
        # GAUCHE FORT
        # =====================

        elif etat == (1,0,0):


            compteur_perdu = 0


            dernier_sens = 1


            compteur_virage += 2



            if compteur_virage > 10:

                cible = GAUCHE_FORT


            else:

                cible = 116



            vitesse = VITESSE_VIRAGE





        # =====================
        # DROITE LEGER
        # =====================

        elif etat == (0,1,1):


            compteur_perdu = 0


            dernier_sens = -1


            compteur_virage = 8


            cible = DROITE_LEGER


            vitesse = 30





        # =====================
        # DROITE FORT
        # =====================

        elif etat == (0,0,1):


            compteur_perdu = 0


            dernier_sens = -1


            compteur_virage += 2



            if compteur_virage > 10:

                cible = DROITE_FORT


            else:

                cible = 78



            vitesse = VITESSE_VIRAGE






        # =====================
        # PERTE LIGNE 000
        # =====================

        elif etat == (0,0,0):


            compteur_perdu += 1



            # -----------------
            # POINTILLES
            # -----------------

            if dernier_etat == (1,1,1) and compteur_perdu < 18:


                # on continue exactement pareil

                cible = angle_actuel

                vitesse = 28




            # -----------------
            # PETITE PERTE
            # -----------------

            elif compteur_perdu < 35:


                if dernier_sens == 1:


                    cible = 112



                elif dernier_sens == -1:


                    cible = 82



                else:


                    cible = CENTRE



                vitesse = 12






            # -----------------
            # RECHERCHE BALAYAGE
            # -----------------

            else:


                phase = (compteur_perdu // 20) % 2



                if phase == 0:


                    cible = 123



                else:


                    cible = 71



                vitesse = VITESSE_RECHERCHE






        # sécurité

        else:


            cible = CENTRE

            vitesse = 20






        # =====================
        # ACTION
        # =====================

        tourner(cible)


        robot.set_motor(
            1,
            int(vitesse)
        )




        # mémoire capteur

        if etat != (0,0,0):

            dernier_etat = etat



        time.sleep(0.025)






except KeyboardInterrupt:


    print("STOP")


    robot.stopper()


    servos.set_angle(0,CENTRE)
