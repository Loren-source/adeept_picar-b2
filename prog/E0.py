#!/usr/bin/env python3
"""
EvitementObstacle_v2.py

Structure améliorée :
- Machine à états (AVANCER, SCAN, CONTOURNER)
- Aucun long sleep pendant les manœuvres
- Lecture continue de l'ultrason
- Direction corrigée en continu
"""

import time
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic
from lineTracking import LineTracker

robot = RobotMotor()
servos = RobotServos()
ultra = Ultrasonic()
tracker = LineTracker()

CENTRE = 97
GAUCHE = 125
DROITE = 70

VITESSE = 30
DISTANCE_STOP = 250

etat = "AVANCER"
direction = CENTRE

def tourner(angle):
    servos.set_angle(0, angle)

def distance():
    try:
        return ultra.get_distance()
    except Exception:
        return 9999

try:
    tourner(CENTRE)
    robot.set_motor(1, VITESSE)

    while True:
        d = distance()
        print(f"Etat={etat} Distance={d:.0f} mm")

        if etat == "AVANCER":
            tourner(CENTRE)
            robot.set_motor(1, VITESSE)

            if d < DISTANCE_STOP:
                robot.set_motor(1, 0)
                etat = "SCAN"

        elif etat == "SCAN":
            mesures = {}

            for nom, angle in [("gauche",150),("centre",97),("droite",40)]:
                servos.set_angle(1, angle)
                time.sleep(0.25)
                mesures[nom] = distance()

            servos.set_angle(1,97)

            choix = max(mesures, key=mesures.get)

            if choix == "gauche":
                direction = GAUCHE
            elif choix == "droite":
                direction = DROITE
            else:
                direction = CENTRE

            etat = "CONTOURNER"

        elif etat == "CONTOURNER":
            tourner(direction)
            robot.set_motor(1, 24)

            # boucle continue sans sleep long
            if distance() > DISTANCE_STOP + 120:
                tourner(CENTRE)
                robot.set_motor(1, VITESSE)
                etat = "AVANCER"

        time.sleep(0.05)

except KeyboardInterrupt:
    robot.stopper()
    tourner(CENTRE)
    servos.set_angle(1,97)
