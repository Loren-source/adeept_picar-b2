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
VITESSE_CONTOURNEMENT = 22
VITESSE_RECUL = 15

DISTANCE_SCAN = 400         # début du scan (40 cm)
DISTANCE_APPROCHE_FIN = 300  # fin de l'approche (30 cm)
DISTANCE_SORTIE = 500        # obstacle derrière (50 cm)
DISTANCE_CRITIQUE = 200      # sécurité (recul si < 20 cm)

DISTANCE_FAUSSE = 3000
ANGLES_SCAN = list(range(-60, 61, 10))  # angles de balayage de la tête

# États
ETAT_AVANCER = 0
ETAT_SCAN = 1
ETAT_APPROCHE = 2
ETAT_CONTOURNER = 3
ETAT_SCAN_SORTIE = 4
ETAT_RECENTRER = 5

# ============================================================
# FONCTIONS DE BASE
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

def tourner_tete(angle):
    servos.set_angle(1, angle)

def mesurer_distance():
    try:
        d = ultrasonic.get_distance()
        if d <= 0:
            return DISTANCE_FAUSSE
        return d
    except:
        return DISTANCE_FAUSSE

def lire_ir():
    s = tracker.get_status()
    return (s["left"], s["middle"], s["right"])

# ============================================================
# SCAN UNIQUE (avec recherche de gaps)
# ============================================================
def scanner_obstacle():
    print("\n===== SCAN =====")
    mesures = []
    stopper()
    time.sleep(0.1)
    tourner_tete(ANGLE_SCAN_CENTRE)
    time.sleep(0.1)

    for angle in ANGLES_SCAN:
        tourner_tete(ANGLE_SCAN_CENTRE + angle)
        time.sleep(0.15)
        d = mesurer_distance()
        if d is None or d > 3000:
            d = 3000
        libre = d >= DISTANCE_SORTIE  # seuil de passage libre (50 cm)
        mesures.append({"angle": angle, "distance": d, "libre": libre})
        print(f"[SCAN] angle={angle:>4} | distance={d:>5.0f} | libre={libre}")

    tourner_tete(ANGLE_SCAN_CENTRE)
    time.sleep(0.1)

    # Détection des gaps (zones libres consécutives)
    gaps = []
    gap_actuel = []
    for point in mesures:
        if point["libre"]:
            gap_actuel.append(point)
        else:
            if gap_actuel:
                gaps.append(gap_actuel)
                gap_actuel = []
    if gap_actuel:
        gaps.append(gap_actuel)

    if not gaps:
        print("[SCAN] Aucun passage libre, je vais tourner à droite par défaut")
        return "droite"

    # Choix du meilleur gap (plus large et le plus central possible)
    meilleur_gap = max(gaps, key=lambda g: (abs(g[-1]["angle"] - g[0]["angle"]), -abs(g[len(g)//2]["angle"])))
    angle_centre = meilleur_gap[len(meilleur_gap)//2]["angle"]
    print(f"[CHOIX] Gap: {meilleur_gap[0]['angle']}° -> {meilleur_gap[-1]['angle']}°, centre={angle_centre}°")

    if angle_centre < -10:
        return "gauche"
    elif angle_centre > 10:
        return "droite"
    else:
        return "gauche"  # par défaut si on est centré

# ============================================================
# BOUCLE PRINCIPALE
# ============================================================
print("\n==================================================")
print("MISSION C - ÉVITEMENT D'OBSTACLES (SIMPLIFIÉ)")
print("==================================================")
servos.set_angle(0, ANGLE_CENTRE)
tourner_tete(ANGLE_SCAN_CENTRE)
stopper()
time.sleep(1)
print("\nRobot prêt.\n")

etat_robot = ETAT_AVANCER
direction = "gauche"

try:
    while True:
        distance = mesurer_distance()
        ir = lire_ir()
        print(f"Etat={etat_robot} | Dist={distance:.0f} mm | IR={ir}")

        # ---- 1. AVANCER ----
        if etat_robot == ETAT_AVANCER:
            avancer(VITESSE_AVANCE)
            if distance <= DISTANCE_SCAN:
                stopper()
                etat_robot = ETAT_SCAN

        # ---- 2. SCAN UNIQUE ----
        elif etat_robot == ETAT_SCAN:
            direction = scanner_obstacle()
            print("Direction choisie :", direction)
            etat_robot = ETAT_APPROCHE

        # ---- 3. APPROCHE (braqué, vitesse progressive) ----
        elif etat_robot == ETAT_APPROCHE:
            angle_braque = ANGLE_GAUCHE if direction == "gauche" else ANGLE_DROITE
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

        # ---- 4. CONTOURNEMENT (reste braqué, surveille les bords) ----
        elif etat_robot == ETAT_CONTOURNER:
            angle_braque = ANGLE_GAUCHE if direction == "gauche" else ANGLE_DROITE
            avancer_braque(angle_braque, VITESSE_CONTOURNEMENT)

            # Correction des bords IR
            if ir[0] == 1:      # bord gauche détecté
                servos.set_angle(0, ANGLE_DROITE)
            elif ir[2] == 1:    # bord droit détecté
                servos.set_angle(0, ANGLE_GAUCHE)
            # Sinon, on garde le braquage initial

            # Sortie si obstacle dépassé ET arène retrouvée
            if distance > DISTANCE_SORTIE and ir == (0, 0, 0):
                print("Obstacle dépassé, scan final.")
                stopper()
                etat_robot = ETAT_SCAN_SORTIE

            # Sécurité recul
            if distance < DISTANCE_CRITIQUE:
                print("Distance critique, recul.")
                stopper()
                time.sleep(0.2)
                reculer(VITESSE_RECUL)
                time.sleep(0.5)
                stopper()

        # ---- 5. SCAN FINAL ----
        elif etat_robot == ETAT_SCAN_SORTIE:
            direction = scanner_obstacle()
            print("Direction après obstacle :", direction)
            etat_robot = ETAT_RECENTRER

        # ---- 6. RECENTRAGE ----
        elif etat_robot == ETAT_RECENTRER:
            recentrer()
            avancer(VITESSE_AVANCE)
            time.sleep(0.5)
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
    tourner_tete(ANGLE_SCAN_CENTRE)
