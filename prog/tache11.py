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


# ==========================
# ETATS
# ==========================

etat_robot = "NORMAL"
angle_pointille = CENTRE
compteur_111 = 0

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
        # ==========================================================
        # MODE POINTILLES
        # ==========================================================

        if etat_robot == "POINTILLE":

            # On ne réenvoie l'angle au servo qu'au tout début
            # de la traversée (le servo reste mécaniquement en place ensuite)
            if compteur_111 == 0 and compteur_perdu == 0:
                tourner(angle_pointille)

            robot.set_motor(1, 38)

            # Seule une vraie ligne pleine compte comme "retour"
            if etat == (1, 1, 1):

                compteur_111 += 1

            else:

                compteur_111 = 0

            # Après quelques lectures stables (segments courts),
            # on revient au suivi normal.
            if compteur_111 >= 2:
                etat_robot = "NORMAL"

                compteur_111 = 0

                dernier_etat = etat

            # Sécurité : si on reste trop longtemps à 000,
            # ce n'est plus un pointillé mais une vraie perte.
            if etat == (0, 0, 0):

                compteur_perdu += 1

                if compteur_perdu > 20:

                    etat_robot = "NORMAL"

                    compteur_perdu = 0

                    if dernier_sens == 1:
                        cible = GAUCHE_FORT
                    elif dernier_sens == -1:
                        cible = DROITE_FORT
                    else:
                        cible = CENTRE

                    tourner(cible)
                    robot.set_motor(1, VITESSE_PERDU)

            else:

                compteur_perdu = 0

            time.sleep(0.025)

            continue



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

            # CORRECTION : on ne saute plus directement à FORT.
            # Une lecture isolée de (1,0,0) peut venir du bruit
            # d'une ligne large / d'un pointillé, pas forcément
            # d'un vrai virage serré.
            if compteur_virage > 2:

                cible = GAUCHE_FORT
                vitesse = VITESSE_VIRAGE

            else:

                cible = GAUCHE_LEGER
                vitesse = VITESSE_APPROCHE





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

            # CORRECTION : même logique progressive que (0,1,1),
            # au lieu d'un saut direct à DROITE_FORT.
            if compteur_virage > 2:

                cible = DROITE_FORT
                vitesse = VITESSE_VIRAGE

            else:

                cible = DROITE_LEGER
                vitesse = VITESSE_APPROCHE





        # =====================
        # POINTILLES OU PERTE
        # =====================

        elif etat == (0, 0, 0):

            # CORRECTION : on accepte maintenant aussi (1,1,0) et (0,1,1)
            # comme "venant de la ligne", à condition que l'angle soit
            # encore raisonnablement centré (le robot n'était pas
            # vraiment en train de tourner fort).
            venait_de_ligne = dernier_etat in ((1, 1, 1), (1, 1, 0), (0, 1, 1))
            proche_centre = abs(angle_actuel - CENTRE) < 8

            if venait_de_ligne and proche_centre:

                # On ne mémorise l'angle qu'à la première entrée
                if etat_robot != "POINTILLE":
                    angle_pointille = angle_actuel

                etat_robot = "POINTILLE"

                compteur_111 = 0

                compteur_perdu = 0

                continue

            # Sinon, vraie perte

            compteur_perdu += 1

            if dernier_sens == 1:

                base_cible = GAUCHE_FORT

            elif dernier_sens == -1:

                base_cible = DROITE_FORT

            else:

                base_cible = CENTRE

            # CORRECTION : balayage de récupération.
            # Si on reste bloqué trop longtemps à fond dans une direction
            # sans rien retrouver, on relâche progressivement vers le
            # centre au lieu de rester braqué à 65°/128° pour toujours.
            # Cela permet de "rebalayer" et de retrouver la ligne.
            if compteur_perdu > 15:

                progression = min((compteur_perdu - 15) / 15, 1)

                cible = base_cible + (CENTRE - base_cible) * progression

            else:

                cible = base_cible

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
