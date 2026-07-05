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
# RÉGLAGES (conformes à vos demandes)
# ============================================================
ANGLE_CENTRE = 97
ANGLE_GAUCHE = 135
ANGLE_DROITE = 55

ANGLE_SCAN_GAUCHE = 150
ANGLE_SCAN_CENTRE = 97
ANGLE_SCAN_DROITE = 40

VITESSE_AVANCE = 20
VITESSE_APPROCHE_18 = 18
VITESSE_APPROCHE_15 = 15
VITESSE_APPROCHE_12 = 12
VITESSE_APPROCHE_8 = 8
VITESSE_SORTIE = 18
VITESSE_RECUL = 15

DISTANCE_SCAN = 450          # 45 cm
DISTANCE_APPROCHE_FIN = 300  # 30 cm
DISTANCE_SORTIE = 400        # 50 cm (obstacle derrière)
DISTANCE_CRITIQUE = 200      # sécurité (si plus bas, recul)

DISTANCE_FAUSSE = 3000

# États
ETAT_AVANCER = 0
ETAT_SCAN = 1
ETAT_APPROCHE = 2
ETAT_CONTOURNER = 3
ETAT_SCAN_SORTIE = 4
ETAT_RECENTRER = 5

etat_robot = ETAT_AVANCER
direction = None
distance = DISTANCE_FAUSSE

# ============================================================
# FONCTIONS DE DÉPLACEMENT
# ============================================================
def avancer(vitesse):
    servos.set_angle(0, ANGLE_CENTRE)
    robot.set_motor(1, vitesse)

def avancer_braque(angle, vitesse):
    servos.set_angle(0, angle)
    robot.set_motor(1, vitesse)

def reculer(vitesse):
    robot.set_motor(-1, vitesse)

def stopper():
    robot.set_motor(1, 0)

def recentrer():
    servos.set_angle(0, ANGLE_CENTRE)

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
# SCAN (peut être appelé plusieurs fois)
# ============================================================
def scanner_obstacle():
    global direction
    print("\n===== SCAN =====")
    servos.set_angle(1, ANGLE_SCAN_GAUCHE)
    time.sleep(0.35)
    dist_g = mesurer_distance()
    servos.set_angle(1, ANGLE_SCAN_CENTRE)
    time.sleep(0.35)
    dist_c = mesurer_distance()
    servos.set_angle(1, ANGLE_SCAN_DROITE)
    time.sleep(0.35)
    dist_d = mesurer_distance()
    servos.set_angle(1, ANGLE_SCAN_CENTRE)
    print(f"G={dist_g:.0f} mm | C={dist_c:.0f} mm | D={dist_d:.0f} mm")
    if dist_g >= dist_d:
        direction = "gauche"
    else:
        direction = "droite"
    print("Direction choisie :", direction)

# ============================================================
# CAPTEURS IR (pour rester dans l'arène)
# ============================================================
def lire_ir():
    s = tracker.get_status()
    return (s["left"], s["middle"], s["right"])

# ============================================================
# BOUCLE PRINCIPALE
# ============================================================
print("\n==================================================")
print("MISSION C - ÉVITEMENT D'OBSTACLES (AVEC SCAN FINAL)")
print("==================================================")
servos.set_angle(0, ANGLE_CENTRE)
servos.set_angle(1, ANGLE_SCAN_CENTRE)
stopper()
time.sleep(1)
print("\nRobot prêt.\n")

try:
    while True:
        distance = mesurer_distance()
        print(f"Etat={etat_robot} | Distance={distance:.0f} mm")

        # ---- 1. AVANCER ----
        if etat_robot == ETAT_AVANCER:
            avancer(VITESSE_AVANCE)
            if distance <= DISTANCE_SCAN:
                stopper()
                etat_robot = ETAT_SCAN

        # ---- 2. SCAN (initial) ----
        elif etat_robot == ETAT_SCAN:
            scanner_obstacle()
            etat_robot = ETAT_APPROCHE

        # ---- 3. APPROCHE (braqué dès le début, vitesse progressive) ----
        elif etat_robot == ETAT_APPROCHE:
            if direction == "gauche":
                angle_braque = ANGLE_GAUCHE
            else:
                angle_braque = ANGLE_DROITE

            if distance > 400:
                vitesse = VITESSE_APPROCHE_18
            elif distance > 350:
                vitesse = VITESSE_APPROCHE_15
            elif distance > 300:
                vitesse = VITESSE_APPROCHE_12
            else:
                vitesse = VITESSE_APPROCHE_8

            avancer_braque(angle_braque, vitesse)

            if distance <= DISTANCE_APPROCHE_FIN:
                etat_robot = ETAT_CONTOURNER

        # ---- 4. CONTOURNEMENT (reste braqué, suit la bordure) ----
        elif etat_robot == ETAT_CONTOURNER:
            if direction == "gauche":
                angle_braque = ANGLE_GAUCHE
            else:
                angle_braque = ANGLE_DROITE

            avancer_braque(angle_braque, VITESSE_SORTIE)

            ir = lire_ir()
            if ir[0] == 1 and ir[2] == 0:
                servos.set_angle(0, ANGLE_DROITE)
            elif ir[2] == 1 and ir[0] == 0:
                servos.set_angle(0, ANGLE_GAUCHE)

            # Sortie : obstacle dépassé ET arène retrouvée
            if distance > DISTANCE_SORTIE and ir == (0, 0, 0):
                print("Obstacle dépassé, on va faire un scan final.")
                stopper()
                etat_robot = ETAT_SCAN_SORTIE

            # Sécurité recul
            if distance < DISTANCE_CRITIQUE:
                print("Distance critique ! Recul d'urgence.")
                stopper()
                time.sleep(0.2)
                reculer(VITESSE_RECUL)
                time.sleep(0.6)
                stopper()

        # ---- 5. SCAN FINAL (après obstacle) ----
        elif etat_robot == ETAT_SCAN_SORTIE:
            scanner_obstacle()
            etat_robot = ETAT_RECENTRER

        # ---- 6. RECENTRAGE ----
        elif etat_robot == ETAT_RECENTRER:
            recentrer()
            avancer(VITESSE_SORTIE)
            time.sleep(0.6)
            stopper()
            etat_robot = ETAT_AVANCER
            print("Recentrage terminé, retour à l'avance.")

        time.sleep(0.03)

except KeyboardInterrupt:
    print("\nInterruption utilisateur.")

finally:
    print("\nArrêt du robot...")
    stopper()
    servos.set_angle(0, ANGLE_CENTRE)
    servos.set_angle(1, ANGLE_SCAN_CENTRE)
