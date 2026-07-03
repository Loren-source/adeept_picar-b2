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
# PARAMÈTRES (adaptés)
# ==========================
CENTRE = 97
ANGLE_BRAQUAGE = 45            # augmenté pour tourner plus franchement
VITESSE_NORMALE = 20
VITESSE_EVITEMENT = 12         # réduit pour avoir plus de temps
VITESSE_RECUL = -10            # vitesse de recul en cas d'obstacle trop proche
SEUIL_OBSTACLE = 50            # détection à 50 cm
SEUIL_SECURITE = 12            # distance d'arrêt d'urgence
DUREE_MAINTIEN = 0.8
TEMPS_BALAYAGE = 0.3
TEMPS_REPRISE = 0.8

# Pour le servo de tête (plage 0° = gauche, 90° = centre, 180° = droite)
ANGLE_TETE_CENTRE = 90
ANGLE_TETE_GAUCHE = 10          # un peu à gauche (0° est la butée)
ANGLE_TETE_DROITE = 170         # un peu à droite (180° est la butée)

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
    servos.set_angle(1, angle)

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
tourner_tete(ANGLE_TETE_CENTRE)
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

        # --- Sécurité : si trop proche, on recule immédiatement ---
        if distance < SEUIL_SECURITE and mode != "REPRISE":
            print("!!! TROP PROCHE ! RECUL !")
            arreter()
            reculer(12)
            time.sleep(0.3)
            arreter()
            continue

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

                # Balayage (avec les bons angles)
                tourner_tete(ANGLE_TETE_GAUCHE)
                time.sleep(TEMPS_BALAYAGE)
                dist_gauche = mesurer_distance()
                print(f"Gauche: {dist_gauche:.1f} cm")
                
                tourner_tete(ANGLE_TETE_DROITE)
                time.sleep(TEMPS_BALAYAGE)
                dist_droite = mesurer_distance()
                print(f"Droite: {dist_droite:.1f} cm")
                
                tourner_tete(ANGLE_TETE_CENTRE)
                time.sleep(0.2)

                # Choix du côté libre (avec un minimum de 30 cm pour être sûr)
                if dist_gauche > dist_droite and dist_gauche > 30:
                    direction_choisie = "gauche"
                    angle_braquage_actuel = ANGLE_BRAQUAGE
                elif dist_droite > dist_gauche and dist_droite > 30:
                    direction_choisie = "droite"
                    angle_braquage_actuel = -ANGLE_BRAQUAGE
                else:
                    # Si les deux côtés sont bloqués, on recule
                    direction_choisie = "reculer"
                    angle_braquage_actuel = 0

                print(f"Choix: {direction_choisie} (G={dist_gauche:.1f}, D={dist_droite:.1f})")
                
                if direction_choisie == "reculer":
                    reculer(15)
                    time.sleep(0.5)
                    arreter()
                    mode = "NAVIGATION"
                    continue
                else:
                    braquer(CENTRE + angle_braquage_actuel)
                    temps_debut_phase = time.time()

        # --- Évitement ---
        elif mode == "EVITEMENT":
            # On continue d'avancer en restant braqué
            avancer(VITESSE_EVITEMENT)
            
            # On force le braquage (ne pas le laisser être modifié par les bords)
            braquer(CENTRE + angle_braquage_actuel)

            # Si l'obstacle est dépassé
            if distance > SEUIL_OBSTACLE + 10:  # un peu de marge
                if time.time() - temps_debut_phase > DUREE_MAINTIEN:
                    print("--- Obstacle franchi ---")
                    arreter()
                    mode = "REPRISE"
                    temps_debut_phase = time.time()
            else:
                # Reset le timer tant que l'obstacle est là
                temps_debut_phase = time.time()

            # Surveillance des bords sans modifier le braquage
            if bord == "gauche":
                # Si on touche un bord, on braque plus à droite
                braquer(CENTRE - 15)
            elif bord == "droite":
                braquer(CENTRE + 15)

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
