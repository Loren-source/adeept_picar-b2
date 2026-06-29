#!/usr/bin/env python3
"""
Suivi de ligne PiCar-B - Automate expérimental

Etats:
0 = SUIVI
1 = ABSENCE_COURTE (pointillés probables)
2 = RECHERCHE_PROGRESSIVE
3 = RECHERCHE_LARGE

Réglages à ajuster sur le robot.
"""

import time
from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker

robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()

CENTRE = 97
GAIN = 15

ANGLE_G = 128
ANGLE_D = 65

VMAX = 34
VMIN = 18
VSEARCH = 14

SERVO_ALPHA = 0.40
ERR_ALPHA = 0.30

ABSENCE_COURTE = 12      # ~300 ms
RECHERCHE = 24           # ~600 ms
RECHERCHE_LARGE = 40     # ~1 s

SUIVI = 0
ABSENT = 1
PROGRESSIF = 2
LARGE = 3

etat_ctrl = SUIVI
blancs = 0

angle = CENTRE
erreur = 0.0

def clamp(x,a,b):
    return max(a,min(b,x))

def tourner(cible):
    global angle
    angle = angle*(1-SERVO_ALPHA)+cible*SERVO_ALPHA
    servos.set_angle(0,round(angle,1))

tourner(CENTRE)
robot.set_motor(1,30)
time.sleep(1)

try:
    while True:

        s = tracker.get_status()
        etat=(s["left"],s["middle"],s["right"])

        mesure=None

        if etat==(1,1,1):
            mesure=0
        elif etat==(1,1,0):
            mesure=1
        elif etat==(1,0,0):
            mesure=2
        elif etat==(0,1,1):
            mesure=-1
        elif etat==(0,0,1):
            mesure=-2

        if mesure is not None:
            blancs=0
            etat_ctrl=SUIVI
            erreur=(1-ERR_ALPHA)*erreur+ERR_ALPHA*mesure

        else:
            blancs+=1

            if blancs<=ABSENCE_COURTE:
                etat_ctrl=ABSENT

            elif blancs<=RECHERCHE:
                etat_ctrl=PROGRESSIF

                if erreur>=0:
                    erreur=min(erreur+0.08,2.0)
                else:
                    erreur=max(erreur-0.08,-2.0)

            else:
                etat_ctrl=LARGE
                erreur=0

        cible=CENTRE+GAIN*erreur
        cible=clamp(cible,ANGLE_D,ANGLE_G)

        if etat_ctrl==SUIVI:
            vitesse=max(VMIN,int(VMAX-abs(erreur)*5))

        elif etat_ctrl==ABSENT:
            vitesse=max(VMIN,int(VMAX-2))

        elif etat_ctrl==PROGRESSIF:
            vitesse=VSEARCH

        else:
            vitesse=VSEARCH
            cible=CENTRE

        tourner(cible)
        robot.set_motor(1,vitesse)

        print(etat,
              "mode=",etat_ctrl,
              "blancs=",blancs,
              "err=",round(erreur,2),
              "ang=",round(angle,1))

        time.sleep(0.025)

except KeyboardInterrupt:
    robot.stopper()
    servos.set_angle(0,CENTRE)
