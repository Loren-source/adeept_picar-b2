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

GAUCHE_LEGER = 112
DROITE_LEGER = 82

GAUCHE_FORT = 128
DROITE_FORT = 65


VITESSE_LIGNE = 34
VITESSE_BLANC = 38       # Traversée du blanc avant les pointillés
VITESSE_APPROCHE = 27
VITESSE_VIRAGE = 18
VITESSE_PERDU = 14


angle_actuel = CENTRE


dernier_sens = 0

compteur_virage = 0
compteur_perdu = 0

dernier_etat = (1,1,1)

# ==========================
# NOUVEAU
# ==========================

compteur_blanc = 0


# ==========================
# SERVO
# ==========================

def tourner(cible):

    global angle_actuel

    angle_actuel = angle_actuel * 0.6 + cible * 0.4

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
        # Si la ligne est retrouvée
        # =====================

        if etat != (0,0,0):

            compteur_blanc = 0
            compteur_perdu = 0

            dernier_etat = etat

        # =====================
        # LIGNE CENTREE
        # =====================

        if etat == (1,1,1):

            compteur_virage = 0

            cible = CENTRE
            vitesse = VITESSE_LIGNE

        # =====================
        # VIRAGE GAUCHE
        # =====================

        elif etat == (1,1,0):

            compteur_virage += 1
            dernier_sens = 1

            if compteur_virage > 2:

                cible = GAUCHE_FORT
                vitesse = VITESSE_VIRAGE

            else:

                cible = GAUCHE_LEGER
                vitesse = VITESSE_APPROCHE


        elif etat == (1,0,0):

            compteur_virage += 2

            dernier_sens = 1

            # On garde exactement la logique
            # qui passait les virages.

            cible = GAUCHE_FORT
            vitesse = VITESSE_VIRAGE

        # =====================
        # VIRAGE DROITE
        # =====================

        elif etat == (0,1,1):

            compteur_virage += 1
            dernier_sens = -1

            if compteur_virage > 2:

                cible = DROITE_FORT
                vitesse = VITESSE_VIRAGE

            else:

                cible = DROITE_LEGER
                vitesse = VITESSE_APPROCHE


        elif etat == (0,0,1):

            compteur_virage += 2

            dernier_sens = -1

            # On garde exactement la logique
            # qui passait les virages.

            cible = DROITE_FORT
            vitesse = VITESSE_VIRAGE


        # =====================
        # BLANC / POINTILLES
        # =====================
        
        elif etat == (0,0,0):
        
            compteur_perdu += 1
        
            # Pendant les premières lectures du blanc,
            # on garde le robot parfaitement droit.
            if compteur_perdu <= 8:
        
                angle_actuel = CENTRE
                servos.set_angle(0, CENTRE)
        
                cible = CENTRE
                vitesse = VITESSE_BLANC
        
            # Si le blanc dure trop longtemps,
            # on considère que la ligne est perdue.
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

        # On mémorise le dernier état utile
        if etat != (0,0,0):

            dernier_etat = etat

        time.sleep(0.025)


except KeyboardInterrupt:

    print("STOP")

    robot.stopper()

    servos.set_angle(
        0,
        CENTRE
    )
