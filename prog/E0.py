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
# RÉGLAGES (ajustés)
# ============================================================
ANGLE_CENTRE = 97
ANGLE_GAUCHE = 135
ANGLE_DROITE = 55

ANGLE_SCAN_GAUCHE = 150
ANGLE_SCAN_CENTRE = 97
ANGLE_SCAN_DROITE = 40

VITESSE_AVANCE = 25
VITESSE_APPROCHE_18 = 18
VITESSE_APPROCHE_15 = 15
VITESSE_APPROCHE_12 = 12
VITESSE_APPROCHE_8 = 8
VITESSE_CONTOURNEMENT = 18
VITESSE_RECUL = 15

DISTANCE_SCAN = 500          # 50 cm (début du scan)
DISTANCE_APPROCHE_FIN = 300  # 30 cm (fin de l'approche)
DISTANCE_SORTIE = 400        # 40 cm (obstacle dépassé)
DISTANCE_CRITIQUE = 150      # 15 cm (recul d'urgence)

CONFIRMATION_SORTIE = 8      # cycles pour confirmer le dépassement
SEUIL_BLOCAGE = 80           # cycles de blocage (≈ 2,4 s)

DISTANCE_FAUSSE = 3000
ANGLES_SCAN = list(range(-60, 61, 10))

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
# SCAN AVEC SCORE DE GAP
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
        libre = d >= DISTANCE_SORTIE
        mesures.append({"angle": angle, "distance": d, "libre": libre})
        print(f"[SCAN] angle={angle:>4} | distance={d:>5.0f} | libre={libre}")

    tourner_tete(ANGLE_SCAN_CENTRE)
    time.sleep(0.1)

    # Détection des gaps
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
        print("[SCAN] Aucun passage libre -> droite par défaut")
        return "droite"

    # Score : largeur * 30 + distance_moyenne - abs(angle_centre) * 15
    def score_gap(gap):
        largeur = abs(gap[-1]["angle"] - gap[0]["angle"]) + 10
        dist_moy = sum(p["distance"] for p in gap) / len(gap)
        angle_centre = gap[len(gap)//2]["angle"]
        return largeur * 30 + dist_moy - abs(angle_centre) * 15

    meilleur_gap = max(gaps, key=score_gap)
    angle_centre = meilleur_gap[len(meilleur_gap)//2]["angle"]
    print(f"[CHOIX] Gap: {meilleur_gap[0]['angle']}° -> {meilleur_gap[-1]['angle']}°, centre={angle_centre}°")
    print(f"[SCORE] largeur={abs(meilleur_gap[-1]['angle'] - meilleur_gap[0]['angle'])} score={score_gap(meilleur_gap):.1f}")

    if angle_centre < -10:
        return "gauche"
    elif angle_centre > 10:
        return "droite"
    else:
        return "gauche"

# ============================================================
# CORRECTION IR DOUCE (sans écraser la direction)
# ============================================================
def angle_avec_correction_ir(base_angle, ir):
    """Applique une légère correction IR sans écraser la direction."""
    if ir[0] == 1 and ir[2] == 0:
        # Bord gauche détecté -> on braque à droite (diminuer l'angle)
        return max(ANGLE_DROITE, base_angle - 10)
    elif ir[2] == 1 and ir[0] == 0:
        # Bord droit détecté -> on braque à gauche (augmenter l'angle)
        return min(ANGLE_GAUCHE, base_angle + 10)
    else:
        return base_angle

# ============================================================
# BOUCLE PRINCIPALE
# ============================================================
print("\n==================================================")
print("MISSION C - ÉVITEMENT D'OBSTACLES (VERSION FINALE)")
print("==================================================")
servos.set_angle(0, ANGLE_CENTRE)
tourner_tete(ANGLE_SCAN_CENTRE)
stopper()
time.sleep(1)
print("\nRobot prêt.\n")

# États
ETAT_AVANCER = 0
ETAT_SCAN = 1
ETAT_APPROCHE = 2
ETAT_CONTOURNER = 3
ETAT_SCAN_SORTIE = 4
ETAT_RECENTRER = 5

etat_robot = ETAT_AVANCER
direction = "gauche"
compteur_sortie = 0
compteur_blocage = 0
distance_parcourue = 0
dernier_angle = ANGLE_CENTRE

try:
    while True:
        distance = mesurer_distance()
        ir = lire_ir()
        print(f"Etat={etat_robot} | Dist={distance:.0f} | IR={ir} | sortie={compteur_sortie} | blocage={compteur_blocage}")

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
            base_angle = ANGLE_GAUCHE if direction == "gauche" else ANGLE_DROITE
            angle = angle_avec_correction_ir(base_angle, ir)
            dernier_angle = angle
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

        # ---- 4. CONTOURNEMENT (avec progression et correction IR douce) ----
        elif etat_robot == ETAT_CONTOURNER:
            base_angle = ANGLE_GAUCHE if direction == "gauche" else ANGLE_DROITE
            angle = angle_avec_correction_ir(base_angle, ir)
            dernier_angle = angle
            avancer_braque(angle, VITESSE_CONTOURNEMENT)

            # Détection de dépassement avec confirmation
            if distance > DISTANCE_SORTIE and ir == (0, 0, 0):
                compteur_sortie += 1
                if compteur_sortie >= CONFIRMATION_SORTIE:
                    print("Obstacle dépassé confirmé, scan final.")
                    stopper()
                    etat_robot = ETAT_SCAN_SORTIE
                    compteur_sortie = 0
                    compteur_blocage = 0
            else:
                compteur_sortie = 0

            # Détection de blocage (distance stable entre 250 et 300 mm)
            if 250 <= distance <= 300:
                compteur_blocage += 1
                if compteur_blocage >= SEUIL_BLOCAGE:
                    print("Blocage détecté, re-scan.")
                    stopper()
                    etat_robot = ETAT_SCAN
                    compteur_blocage = 0
            else:
                compteur_blocage = 0

            # Sécurité recul (seuil à 150 mm)
            if distance < DISTANCE_CRITIQUE:
                print("Distance critique, recul.")
                stopper()
                time.sleep(0.1)
                reculer(VITESSE_RECUL)
                time.sleep(0.4)
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
