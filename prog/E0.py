#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic
from lineTracking import LineTracker

# ============================================================
# INITIALISATION
# ============================================================
robot = RobotMotor()
servos = RobotServos()
ultrasonic = Ultrasonic()
tracker = LineTracker()

# ============================================================
# RÉGLAGES
# ============================================================
ANGLE_CENTRE = 97
ANGLE_GAUCHE = 125
ANGLE_DROITE = 65

ANGLE_SCAN_GAUCHE = 150
ANGLE_SCAN_CENTRE = 97
ANGLE_SCAN_DROITE = 40

VITESSE_AVANCE = 35
VITESSE_APPROCHE = 15
VITESSE_CONTOURNEMENT = 18
VITESSE_SORTIE = 22
VITESSE_RECUL = 15

DISTANCE_SCAN = 450
DISTANCE_BRAQUAGE = 300
DISTANCE_CRITIQUE = 200      # seuil pour reculer
DISTANCE_FAUSSE = 3000

# États
ETAT_AVANCER = 0
ETAT_SCAN = 1
ETAT_APPROCHE = 2
ETAT_BRAQUER = 3
ETAT_CONTOURNER = 4
ETAT_RECENTRER = 5

etat_robot = ETAT_AVANCER
direction = None
distance = DISTANCE_FAUSSE
distance_gauche = DISTANCE_FAUSSE
distance_centre = DISTANCE_FAUSSE
distance_droite = DISTANCE_FAUSSE


# ============================================================
# FONCTIONS DE DÉPLACEMENT
# ============================================================
def avancer(vitesse=VITESSE_AVANCE):
    servos.set_angle(0, ANGLE_CENTRE)
    robot.set_motor(1, vitesse)

def avancer_braque():
    if direction == "gauche":
        servos.set_angle(0, ANGLE_GAUCHE)
    else:
        servos.set_angle(0, ANGLE_DROITE)
    robot.set_motor(1, VITESSE_APPROCHE)

def tourner_gauche():
    servos.set_angle(0, ANGLE_GAUCHE)
    robot.set_motor(1, VITESSE_CONTOURNEMENT)

def tourner_droite():
    servos.set_angle(0, ANGLE_DROITE)
    robot.set_motor(1, VITESSE_CONTOURNEMENT)

def recentrer():
    servos.set_angle(0, ANGLE_CENTRE)

def stopper():
    robot.set_motor(1, 0)

def reculer(vitesse=VITESSE_RECUL):
    robot.set_motor(-1, vitesse)


# ============================================================
# ULTRASON
# ============================================================
def mesurer_distance():
    try:
        d = ultrasonic.get_distance()
        if d <= 0:
            return DISTANCE_FAUSSE
        return d
    except:
        return DISTANCE_FAUSSE


# ============================================================
# SCAN
# ============================================================
def scanner_obstacle():
    global distance_gauche, distance_centre, distance_droite
    print("\n===== SCAN =====")
    servos.set_angle(1, ANGLE_SCAN_GAUCHE)
    time.sleep(0.35)
    distance_gauche = mesurer_distance()
    servos.set_angle(1, ANGLE_SCAN_CENTRE)
    time.sleep(0.35)
    distance_centre = mesurer_distance()
    servos.set_angle(1, ANGLE_SCAN_DROITE)
    time.sleep(0.35)
    distance_droite = mesurer_distance()
    servos.set_angle(1, ANGLE_SCAN_CENTRE)
    print(f"G={distance_gauche:.0f} mm | C={distance_centre:.0f} mm | D={distance_droite:.0f} mm")


# ============================================================
# CHOIX DE LA DIRECTION
# ============================================================
def choisir_direction():
    if distance_gauche >= distance_droite:
        return "gauche"
    return "droite"


# ============================================================
# CAPTEURS IR
# ============================================================
def lire_ir():
    s = tracker.get_status()
    return (s["left"], s["middle"], s["right"])

def bordure_detectee():
    etat = lire_ir()
    return etat[0] == 1 or etat[2] == 1

def arena_retrouvee():
    etat = lire_ir()
    return etat == (0, 0, 0)


# ============================================================
# INITIALISATION
# ============================================================
print("\n==================================================")
print("MISSION C - ÉVITEMENT D'OBSTACLES (CORRIGÉ V2)")
print("==================================================")
servos.set_angle(0, ANGLE_CENTRE)
servos.set_angle(1, ANGLE_SCAN_CENTRE)
stopper()
time.sleep(1)
print("\nRobot prêt.\n")


# ============================================================
# BOUCLE PRINCIPALE
# ============================================================
try:
    while True:
        distance = mesurer_distance()
        print(f"Etat={etat_robot} | Distance={distance:.0f} mm")

        # ---- AVANCER ----
        if etat_robot == ETAT_AVANCER:
            avancer()
            if distance <= DISTANCE_SCAN:
                stopper()
                etat_robot = ETAT_SCAN

        # ---- SCAN ----
        elif etat_robot == ETAT_SCAN:
            scanner_obstacle()
            direction = choisir_direction()
            print("Direction :", direction)
            etat_robot = ETAT_APPROCHE

        # ---- APPROCHE ----
        elif etat_robot == ETAT_APPROCHE:
            avancer_braque()
            if distance > 400:
                robot.set_motor(1, 18)
            elif distance > 350:
                robot.set_motor(1, 15)
            else:
                robot.set_motor(1, 10)
            if distance <= DISTANCE_BRAQUAGE:
                stopper()
                time.sleep(0.15)
                etat_robot = ETAT_BRAQUER

        # ---- BRAQUER ----
        elif etat_robot == ETAT_BRAQUER:
            print("[BRAQUER] Direction:", direction)
            if direction == "gauche":
                servos.set_angle(0, ANGLE_GAUCHE)
            else:
                servos.set_angle(0, ANGLE_DROITE)
            robot.set_motor(1, VITESSE_CONTOURNEMENT)
            time.sleep(0.8)
            stopper()
            etat_robot = ETAT_CONTOURNER

        # ---- CONTOURNER (avec surveillance distance) ----
        elif etat_robot == ETAT_CONTOURNER:
            recentrer()
            robot.set_motor(1, VITESSE_SORTIE)
            debut = time.time()
            dist_precedente = distance
            while True:
                dist_act = mesurer_distance()
                ir = lire_ir()
                print(f"[CONTOURNER] dist={dist_act:.0f}, IR={ir}")

                # Sortie si obstacle franchi
                if dist_act > DISTANCE_SCAN:
                    print("Plus d'obstacle, sortie du contournement")
                    break

                # Si distance critique -> recul et re-scan
                if dist_act < DISTANCE_CRITIQUE or (dist_act < dist_precedente - 30):
                    print("Trop proche ou rapprochement -> recul et re-scan")
                    stopper()
                    time.sleep(0.2)
                    reculer(VITESSE_RECUL)
                    time.sleep(0.6)
                    stopper()
                    etat_robot = ETAT_SCAN
                    break

                # Correction de bordure
                if ir[0] == 1:
                    servos.set_angle(0, ANGLE_DROITE)
                elif ir[2] == 1:
                    servos.set_angle(0, ANGLE_GAUCHE)
                else:
                    servos.set_angle(0, ANGLE_CENTRE)

                # Sécurité anti-boucle
                if time.time() - debut > 8.0:
                    print("Temps max atteint, sortie")
                    break

                dist_precedente = dist_act
                time.sleep(0.05)

            if etat_robot != ETAT_SCAN:
                stopper()
                etat_robot = ETAT_RECENTRER

        # ---- RECENTRER ----
        elif etat_robot == ETAT_RECENTRER:
            recentrer()
            robot.set_motor(1, VITESSE_SORTIE)
            time.sleep(0.6)
            stopper()
            etat_robot = ETAT_AVANCER

        time.sleep(0.03)

except KeyboardInterrupt:
    print("\nInterruption utilisateur.")

finally:
    print("\nArrêt du robot...")
    stopper()
    servos.set_angle(0, ANGLE_CENTRE)
    servos.set_angle(1, ANGLE_SCAN_CENTRE)
