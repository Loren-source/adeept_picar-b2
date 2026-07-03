#!/usr/bin/env python3
"""
EvitementObstacle_v3.py

Architecture à états :
- AVANCER
- SCAN
- TOURNER
- LONGER
- REPRISE

Compatible avec les modules Adeept :
motor.py, servo.py, Ultra.py, line.py
"""

import time
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic

robot = RobotMotor()
servos = RobotServos()
ultra = Ultrasonic()

CENTRE = 97
GAUCHE = 125
DROITE = 70

VITESSE = 30
VITESSE_CONTOUR = 22
STOP = 220

etat = "AVANCER"
direction = CENTRE
t0 = 0

def dir_angle(a):
    servos.set_angle(0, a)

def tete(a):
    servos.set_angle(1, a)

def dist():
    try:
        return ultra.get_distance()
    except Exception:
        return 9999

dir_angle(CENTRE)
tete(97)
robot.set_motor(1, VITESSE)

try:
    while True:
        d = dist()
        print(etat, d)

        if etat == "AVANCER":
            dir_angle(CENTRE)
            robot.set_motor(1, VITESSE)
            if d < STOP:
                robot.set_motor(1, 0)
                etat = "SCAN"

        elif etat == "SCAN":
            mesures = {}
            for nom, ang in [("gauche",150),("centre",97),("droite",40)]:
                tete(ang)
                time.sleep(0.25)
                mesures[nom] = dist()
            tete(97)

            meilleur = max(mesures, key=mesures.get)
            direction = GAUCHE if meilleur=="gauche" else DROITE if meilleur=="droite" else CENTRE

            dir_angle(direction)
            robot.set_motor(1, VITESSE_CONTOUR)
            t0 = time.time()
            etat = "TOURNER"

        elif etat == "TOURNER":
            dir_angle(direction)
            robot.set_motor(1, VITESSE_CONTOUR)

            # garde le braquage pendant 0.8 s
            if time.time()-t0 > 0.8:
                t0 = time.time()
                etat = "LONGER"

        elif etat == "LONGER":
            dir_angle(direction)
            robot.set_motor(1, VITESSE_CONTOUR)

            # obstacle dépassé
            if dist() > 450 and time.time()-t0 > 0.6:
                t0 = time.time()
                etat = "REPRISE"

        elif etat == "REPRISE":
            dir_angle(CENTRE)
            robot.set_motor(1, VITESSE)

            if time.time()-t0 > 0.6:
                etat = "AVANCER"

        time.sleep(0.05)

except KeyboardInterrupt:
    robot.stopper()
    dir_angle(CENTRE)
    tete(97)
