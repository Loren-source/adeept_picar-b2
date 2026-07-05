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
# Direction des roues (servo canal 0)
ANGLE_CENTRE = 97
ANGLE_GAUCHE = 135              # braquage pour tourner à gauche
ANGLE_DROITE = 55               # braquage pour tourner à droite

# Tête du capteur ultrason (servo canal 1)
ANGLE_SCAN_GAUCHE = 150
ANGLE_SCAN_CENTRE = 97
ANGLE_SCAN_DROITE = 40

# Vitesses (valeur entre 0 et 100 pour le moteur)
VITESSE_AVANCE = 20
VITESSE_APPROCHE_18 = 18
VITESSE_APPROCHE_15 = 15
VITESSE_APPROCHE_12 = 12
VITESSE_APPROCHE_8 = 8
VITESSE_CONTOURNEMENT = 20
VITESSE_RECUL = 15

# Distances en mm
DISTANCE_SCAN = 450          # début du scan (45 cm)
DISTANCE_APPROCHE_FIN = 300  # fin de l'approche (30 cm), début contournement
DISTANCE_SORTIE = 500        # obstacle considéré dépassé (50 cm)
DISTANCE_CRITIQUE = 200      # sécurité (20 cm) – recul d'urgence

DISTANCE_FAUSSE = 3000       # valeur par défaut si mesure invalide

# États de la machine à états
ETAT_AVANCER = 0
ETAT_SCAN = 1
ETAT_APPROCHE = 2
ETAT_CONTOURNER = 3
ETAT_SCAN_SORTIE = 4
ETAT_RECENTRER = 5

etat_robot = ETAT_AVANCER
direction = None               # "gauche" ou "droite"
distance = DISTANCE_FAUSSE

# ============================================================
# FONCTIONS DE DÉPLACEMENT
# ============================================================
def avancer(vitesse):
    """Avance tout droit."""
    servos.set_angle(0, ANGLE_CENTRE)
    robot.set_motor(1, vitesse)

def avancer_braque(angle, vitesse):
    """Avance avec un braquage donné."""
    servos.set_angle(0, angle)
    robot.set_motor(1, vitesse)

def reculer(vitesse):
    """Recule (vitesse négative)."""
    robot.set_motor(-1, vitesse)

def stopper():
    """Arrête le moteur."""
    robot.set_motor(1, 0)

def recentrer():
    """Remet les roues au centre."""
    servos.set_angle(0, ANGLE_CENTRE)

# ============================================================
# MESURE DE DISTANCE ULTRASON
# ============================================================
def mesurer_distance():
    """Retourne la distance en mm, ou DISTANCE_FAUSSE en cas d'erreur."""
    try:
        d = ultrasonic.get_distance()
        if d <= 0:
            return DISTANCE_FAUSSE
        return d
    except:
        return DISTANCE_FAUSSE

# ============================================================
# SCANNER (balayage de la tête)
# ============================================================
def scanner_obstacle():
    """
    Effectue un scan à gauche, centre, droite et choisit le côté le plus libre.
    Met à jour la variable globale 'direction'.
    """
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
# LECTURE DES CAPTEURS IR (pour rester dans le périmètre)
# ============================================================
def lire_ir():
    """Retourne un tuple (gauche, milieu, droite) avec 1 pour noir, 0 pour blanc."""
    s = tracker.get_status()
    return (s["left"], s["middle"], s["right"])

# ============================================================
# BOUCLE PRINCIPALE
# ============================================================
print("\n==================================================")
print("MISSION C - ÉVITEMENT D'OBSTACLES (AVEC SURVEILLANCE DES BORDS)")
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

        # ----------------------------------------------------------
        # ÉTAT 0 : AVANCER
        # ----------------------------------------------------------
        if etat_robot == ETAT_AVANCER:
            avancer(VITESSE_AVANCE)
            if distance <= DISTANCE_SCAN:
                stopper()
                etat_robot = ETAT_SCAN

        # ----------------------------------------------------------
        # ÉTAT 1 : SCAN (premier balayage)
        # ----------------------------------------------------------
        elif etat_robot == ETAT_SCAN:
            scanner_obstacle()
            etat_robot = ETAT_APPROCHE

        # ----------------------------------------------------------
        # ÉTAT 2 : APPROCHE (progressif, déjà braqué)
        # ----------------------------------------------------------
        elif etat_robot == ETAT_APPROCHE:
            angle = ANGLE_GAUCHE if direction == "gauche" else ANGLE_DROITE
            # Vitesse progressive selon la distance
            if distance > 400:
                vitesse = VITESSE_APPROCHE_18
            elif distance > 350:
                vitesse = VITESSE_APPROCHE_15
            elif distance > 300:
                vitesse = VITESSE_APPROCHE_12
            else:
                vitesse = VITESSE_APPROCHE_8
            avancer_braque(angle, vitesse)
            if distance <= DISTANCE_APPROCHE_FIN:
                etat_robot = ETAT_CONTOURNER

        # ----------------------------------------------------------
        # ÉTAT 3 : CONTOURNEMENT (reste braqué, surveille les bords)
        # ----------------------------------------------------------
        elif etat_robot == ETAT_CONTOURNER:
            angle = ANGLE_GAUCHE if direction == "gauche" else ANGLE_DROITE
            avancer_braque(angle, VITESSE_CONTOURNEMENT)

            # Lecture des capteurs IR pour rester dans l'arène
            ir = lire_ir()
            # Correction de bordure (sans recentrer complètement)
            if ir[0] == 1 and ir[2] == 0:
                # Bord gauche détecté → braquer à droite
                servos.set_angle(0, ANGLE_DROITE)
            elif ir[2] == 1 and ir[0] == 0:
                # Bord droit détecté → braquer à gauche
                servos.set_angle(0, ANGLE_GAUCHE)
            # Si les deux ou aucun, on garde l'angle initial (pas de changement)

            # Conditions de sortie du contournement : obstacle dépassé ET arène retrouvée
            if distance > DISTANCE_SORTIE and ir == (0, 0, 0):
                print("Obstacle dépassé, scan final.")
                stopper()
                etat_robot = ETAT_SCAN_SORTIE

            # Sécurité : recul d'urgence si trop proche
            if distance < DISTANCE_CRITIQUE:
                print("Distance critique ! Recul d'urgence.")
                stopper()
                time.sleep(0.2)
                reculer(VITESSE_RECUL)
                time.sleep(0.6)
                stopper()

        # ----------------------------------------------------------
        # ÉTAT 4 : SCAN FINAL (après obstacle)
        # ----------------------------------------------------------
        elif etat_robot == ETAT_SCAN_SORTIE:
            scanner_obstacle()
            etat_robot = ETAT_RECENTRER

        # ----------------------------------------------------------
        # ÉTAT 5 : RECENTRAGE
        # ----------------------------------------------------------
        elif etat_robot == ETAT_RECENTRER:
            recentrer()
            avancer(VITESSE_CONTOURNEMENT)
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
