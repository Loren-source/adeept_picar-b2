#!/usr/bin/env python3
import time
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic
from lineTracking import LineTracker

robot=RobotMotor()
servos=RobotServos()
ultra=Ultrasonic()
tracker=LineTracker()

CENTRE=97
GAUCHE=140
DROITE=55
GAUCHE_LEGER=118
DROITE_LEGER=76
SCAN_GAUCHE=150
SCAN_CENTRE=97
SCAN_DROITE=40
DIST_STOP=220
DIST_OK=350
VITESSE=35
VITESSE_EVITEMENT=28
angle_actuel=CENTRE

def tourner(cible):
    global angle_actuel
    angle_actuel=angle_actuel*0.6+cible*0.4
    servos.set_angle(0,round(angle_actuel,1))

def scan():
    m={}
    for nom,ang in (("gauche",SCAN_GAUCHE),("centre",SCAN_CENTRE),("droite",SCAN_DROITE)):
        servos.set_angle(1,ang)
        time.sleep(0.25)
        m[nom]=ultra.get_distance()
    servos.set_angle(1,SCAN_CENTRE)
    return m

def choisir_direction(m):
    if m["centre"]>DIST_OK:
        return "centre"
    return "gauche" if m["gauche"]>=m["droite"] else "droite"

def corriger_bord():
    s=tracker.get_status()
    if s["left"]==0:
        tourner(DROITE_LEGER)
    elif s["right"]==0:
        tourner(GAUCHE_LEGER)

print("START")
tourner(CENTRE)
servos.set_angle(1,SCAN_CENTRE)
robot.set_motor(1,30)
time.sleep(1)

try:
    while True:
        corriger_bord()
        d=ultra.get_distance()
        print(f"Distance: {d:.0f} mm")
        if d<DIST_STOP:
            robot.stopper()
            mesures=scan()
            print(mesures)
            direction=choisir_direction(mesures)
            if direction=="gauche":
                tourner(GAUCHE)
            elif direction=="droite":
                tourner(DROITE)
            else:
                tourner(CENTRE)
            robot.set_motor(1,VITESSE_EVITEMENT)
            time.sleep(0.9)
            tourner(CENTRE)
        else:
            robot.set_motor(1,VITESSE)
        time.sleep(0.05)
except KeyboardInterrupt:
    robot.stopper()
    tourner(CENTRE)
    servos.set_angle(1,SCAN_CENTRE)
