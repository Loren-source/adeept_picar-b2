#!/usr/bin/env python3
"""
Patch v2 basé sur le code d'origine.

Améliorations :
- Conservation de la logique de virage d'origine.
- Mémoire adaptative des blancs.
- Réinitialisation de dernier_sens après une vraie ligne droite.
- Sauvegarde de l'angle réellement envoyé au servo.
"""

import time
from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker

robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()

CENTRE = 97

GAUCHE_LEGER = 112
DROITE_LEGER = 82
GAUCHE_FORT = 128
DROITE_FORT = 65

VITESSE_LIGNE = 40
VITESSE_APPROCHE = 18
VITESSE_VIRAGE = 18
VITESSE_RECHERCHE = 14

angle_actuel = CENTRE
dernier_angle = CENTRE
derniere_vitesse = VITESSE_LIGNE

dernier_sens = 0
compteur_blanc = 0
compteur_centre = 0

SERVO_ALPHA = 0.8


def tourner(cible):
    global angle_actuel
    angle_actuel = angle_actuel * (1 - SERVO_ALPHA) + cible * SERVO_ALPHA
    servos.set_angle(0, round(angle_actuel, 1))


tourner(CENTRE)
robot.set_motor(1, 30)
time.sleep(1)

try:
    while True:

        s = tracker.get_status()
        etat = (s["left"], s["middle"], s["right"])

        if etat == (1,1,1):
            compteur_blanc = 0
            compteur_centre += 1
        
            if compteur_centre >= 10:
                dernier_sens = 0
        
            cible = CENTRE
            vitesse = VITESSE_LIGNE

        else:
            compteur_centre = 0
            if etat == (1,1,0):
                compteur_blanc = 0
                dernier_sens = 1
            
                cible = GAUCHE_FORT
                vitesse = VITESSE_APPROCHE
        
            elif etat == (1,0,0):
                compteur_blanc = 0
                dernier_sens = 1
            
                cible = GAUCHE_FORT
                vitesse = VITESSE_VIRAGE

            elif etat == (0,1,1):
                compteur_blanc = 0
                dernier_sens = -1
            
                cible = DROITE_FORT
                vitesse = VITESSE_APPROCHE

            elif etat == (0,0,1):
                compteur_blanc = 0
                dernier_sens = -1
            
                cible = DROITE_FORT
                vitesse = VITESSE_VIRAGE
        
            else:  # 000

                compteur_blanc += 1

                memoire = 18 if dernier_sens == 0 else 8

                if compteur_blanc <= memoire:
                    cible = dernier_angle
                    vitesse = derniere_vitesse

                elif compteur_blanc <= memoire + 12:

                    if dernier_sens == 1:
                        cible = min(dernier_angle + (compteur_blanc - memoire), GAUCHE_FORT)
                    elif dernier_sens == -1:
                        cible = max(dernier_angle - (compteur_blanc - memoire), DROITE_FORT)
                    else:
                        cible = CENTRE

                    vitesse = VITESSE_RECHERCHE

                else:
                    cible = CENTRE
                    vitesse = VITESSE_RECHERCHE

        tourner(cible)
        robot.set_motor(1, vitesse)

        if etat != (0,0,0):
            dernier_angle = angle_actuel
            derniere_vitesse = vitesse

        print(etat,
              "blanc=", compteur_blanc,
              "centre=", compteur_centre,
              "sens=", dernier_sens,
              "servo=", round(angle_actuel,1))

        time.sleep(0.025)

except KeyboardInterrupt:
    robot.stopper()
    servos.set_angle(0, CENTRE)
