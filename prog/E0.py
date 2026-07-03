#!/usr/bin/env python3
import time
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic
from lineTracking import LineTracker

# ==========================
# INSTANCIATION
# ==========================
robot = RobotMotor()
servos = RobotServos()
ultrasonic = Ultrasonic()
tracker = LineTracker()

# ==========================
# PARAMÈTRES
# ==========================
CENTRE = 97
ANGLE_BRAQUAGE = 35
VITESSE_NORMALE = 20
VITESSE_EVITEMENT = 15
VITESSE_RECHERCHE = 12
SEUIL_OBSTACLE = 50
DISTANCE_SECURITE = 25
DUREE_MAINTIEN = 0.5
TEMPS_BALAYAGE = 0.3
TEMPS_REPRISE = 0.8

# Angles de la tête (à ajuster selon le montage)
ANGLE_TETE_CENTRE = 90         # position neutre du servo (par ex 90°)
ANGLE_TETE_GAUCHE = 0          # position à gauche (par ex 0°)
ANGLE_TETE_DROITE = 180        # position à droite (par ex 180°)

# ==========================
# VARIABLES
# ==========================
mode = "NAVIGATION"
direction_choisie = None
angle_braquage_actuel = 0
temps_debut_phase = 0

# ==========================
# FONCTIONS
# ==========================

def mesurer_distance():
    """Retourne la distance en cm (moyenne sur 3 lectures)."""
    total = 0
    for _ in range(3):
        total += ultrasonic.get_distance() / 10
        time.sleep(0.02)
    return total / 3

def tourner_tete(angle):
    """Oriente la tête du capteur ultrason (servo canal 1)."""
    # Assurez-vous que l'angle est dans la plage autorisée [0, 180]
    if angle < 0:
        angle = 0
    elif angle > 180:
        angle = 180
    servos.set_angle(1, angle)
    time.sleep(0.05)  # laisser le temps au servo de bouger

def braquer(angle):
    servos.set_angle(0, round(angle))

def avancer(vitesse):
    robot.set_motor(1, vitesse)

def arreter():
    robot.set_motor(1, 0)

def reculer(vitesse):
    robot.set_motor(1, -vitesse)

def get_ir_status():
    s = tracker.get_status()
    return (s["left"], s["middle"], s["right"])

def detecter_bord():
    g, m, d = get_ir_status()
    if g == 1 and d == 1:
        return "les_deux"
    elif g == 1:
        return "gauche"
    elif d == 1:
        return "droite"
    else:
        return None

# ==========================
# INITIALISATION
# ==========================
print("START Mission C")
tourner_tete(ANGLE_TETE_CENTRE)  # on place la tête au centre
time.sleep(0.5)
braquer(CENTRE)
avancer(VITESSE_NORMALE)

# ==========================
# BOUCLE PRINCIPALE
# ==========================
try:
    while True:
        distance = mesurer_distance()
        bord = detecter_bord()
        print(f"Dist={distance:.1f}cm, mode={mode}, bord={bord}")

        # --- Gestion prioritaire des bords ---
        if bord == "les_deux":
            print("!!! Les deux bords détectés ! recul !")
            arreter()
            time.sleep(0.2)
            reculer(12)
            time.sleep(0.5)
            braquer(CENTRE - 30)
            time.sleep(0.5)
            arreter()
            braquer(CENTRE)
            continue

        # --- Navigation normale ---
        if mode == "NAVIGATION":
            if bord == "gauche":
                braquer(CENTRE + 20)
                avancer(VITESSE_NORMALE)
            elif bord == "droite":
                braquer(CENTRE - 20)
                avancer(VITESSE_NORMALE)
            else:
                braquer(CENTRE)
                avancer(VITESSE_NORMALE)

            # Détection d'obstacle
            if distance < SEUIL_OBSTACLE and distance > 0:
                print(f"--- Obstacle à {distance:.1f} cm ! ---")
                arreter()
                mode = "EVITEMENT"

                # Balayage : tête à gauche, mesure, tête à droite, mesure
                print("Balayage gauche...")
                tourner_tete(ANGLE_TETE_GAUCHE)
                time.sleep(TEMPS_BALAYAGE)
                dist_gauche = mesurer_distance()
                print(f"Gauche: {dist_gauche:.1f} cm")

                print("Balayage droite...")
                tourner_tete(ANGLE_TETE_DROITE)
                time.sleep(TEMPS_BALAYAGE)
                dist_droite = mesurer_distance()
                print(f"Droite: {dist_droite:.1f} cm")

                # Remettre la tête au centre
                tourner_tete(ANGLE_TETE_CENTRE)
                time.sleep(0.2)

                # Choix du côté libre
                if dist_gauche > dist_droite:
                    direction_choisie = "gauche"
                    angle_braquage_actuel = ANGLE_BRAQUAGE
                else:
                    direction_choisie = "droite"
                    angle_braquage_actuel = -ANGLE_BRAQUAGE

                print(f"Choix: {direction_choisie} (G={dist_gauche:.1f}, D={dist_droite:.1f})")
                braquer(CENTRE + angle_braquage_actuel)
                temps_debut_phase = time.time()

        # --- Évitement ---
        elif mode == "EVITEMENT":
            avancer(VITESSE_EVITEMENT)

            # Si l'obstacle est dépassé
            if distance > SEUIL_OBSTACLE:
                if time.time() - temps_debut_phase > DUREE_MAINTIEN:
                    print("--- Obstacle franchi ---")
                    arreter()
                    mode = "REPRISE"
                    temps_debut_phase = time.time()
            else:
                temps_debut_phase = time.time()

            # Surveillance des bords
            if bord == "gauche":
                braquer(CENTRE - 10)
            elif bord == "droite":
                braquer(CENTRE + 10)

        # --- Reprise ---
        elif mode == "REPRISE":
            facteur = 1.0 - (time.time() - temps_debut_phase) / TEMPS_REPRISE
            if facteur < 0:
                facteur = 0
            angle_cible = CENTRE + angle_braquage_actuel * facteur
            braquer(angle_cible)
            avancer(VITESSE_EVITEMENT * 0.7)

            if time.time() - temps_debut_phase > TEMPS_REPRISE:
                print("--- Reprise OK ---")
                mode = "NAVIGATION"
                braquer(CENTRE)
                arreter()
                time.sleep(0.1)

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nSTOP")
    arreter()
    braquer(CENTRE)
    tourner_tete(ANGLE_TETE_CENTRE)
    robot.destroy()
    servos.fermer()
