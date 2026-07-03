#!/usr/bin/env python3
import time
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic
from lineTracker import LineTracker

# ==========================
# INSTANCIATION
# ==========================
robot = RobotMotor()
servos = RobotServos()
ultrasonic = Ultrasonic()
tracker = LineTracker()  # capteurs IR (gauche, milieu, droite)

# ==========================
# PARAMÈTRES (à ajuster selon votre robot)
# ==========================
CENTRE = 97                    # position neutre du servo de direction
ANGLE_BRAQUAGE = 35            # amplitude de braquage pour contourner (en degrés)
VITESSE_NORMALE = 30           # vitesse en ligne droite (dans la zone)
VITESSE_EVITEMENT = 20         # vitesse pendant la manœuvre d'évitement
VITESSE_RECHERCHE = 15         # vitesse pour chercher un passage (si bloqué)
SEUIL_OBSTACLE = 30            # distance en cm pour déclencher l'évitement
DISTANCE_SECURITE = 25         # distance d'arrêt avant collision
DUREE_MAINTIEN = 0.5           # temps de maintien du braquage après avoir dépassé l'obstacle
TEMPS_BALAYAGE = 0.3           # temps d'attente entre les mesures de balayage
TEMPS_REPRISE = 0.8            # durée de la transition de reprise (retour au centre)

# Positions de la tête (capteur ultrason)
ANGLE_TETE_CENTRE = 0
ANGLE_TETE_GAUCHE = -90
ANGLE_TETE_DROITE = 90

# ==========================
# VARIABLES GLOBALES
# ==========================
mode = "NAVIGATION"           # "NAVIGATION", "EVITEMENT", "REPRISE"
direction_choisie = None      # "gauche" ou "droite"
angle_braquage_actuel = 0     # angle de braquage pour la manœuvre (relatif au CENTRE)
temps_debut_phase = 0

# ==========================
# FONCTIONS UTILITAIRES
# ==========================

def mesurer_distance():
    """Retourne la distance en cm devant le robot."""
    # Si votre classe Ultrasonic retourne en mm, divisez par 10
    return ultrasonic.get_distance() / 10

def tourner_tete(angle):
    """Oriente la tête du capteur ultrason (servo canal 1)."""
    servos.set_angle(1, angle)

def braquer(angle):
    """Braque les roues (servo canal 0)."""
    servos.set_angle(0, round(angle))

def avancer(vitesse):
    """Avance à la vitesse donnée (positive)."""
    robot.set_motor(1, vitesse)

def arreter():
    """Arrête le moteur."""
    robot.set_motor(1, 0)

def reculer(vitesse):
    """Recule à la vitesse donnée (négative)."""
    robot.set_motor(1, -vitesse)

def get_ir_status():
    """Lit les capteurs IR et retourne un tuple (gauche, milieu, droite)."""
    s = tracker.get_status()
    return (s["left"], s["middle"], s["right"])

def detecter_bord():
    """
    Vérifie si un capteur IR latéral détecte la ligne noire (bord de zone).
    Retourne 'gauche', 'droite', 'les_deux' ou None.
    """
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
        # ---- Mise à jour des capteurs ----
        distance = mesurer_distance()
        bord = detecter_bord()
        print(f"Dist={distance:.1f}cm, mode={mode}, bord={bord}")

        # ---- PRIORITÉ ABSOLUE : Gestion des bords (pour ne pas sortir de la zone) ----
        if bord == "les_deux":
            print("!!! Les deux bords détectés ! recul et rotation !")
            arreter()
            time.sleep(0.2)
            reculer(15)
            time.sleep(0.5)
            braquer(CENTRE - 30)  # tourner à gauche pour se dégager
            time.sleep(0.5)
            arreter()
            braquer(CENTRE)
            continue  # recommencer la boucle

        # ---- Navigation normale ----
        if mode == "NAVIGATION":
            # Ajustement pour rester dans la zone (suivi des bords)
            if bord == "gauche":
                # Trop à gauche → braquer à droite
                braquer(CENTRE + 20)
                avancer(VITESSE_NORMALE)
            elif bord == "droite":
                # Trop à droite → braquer à gauche
                braquer(CENTRE - 20)
                avancer(VITESSE_NORMALE)
            else:
                # Pas de bord → avancer tout droit
                braquer(CENTRE)
                avancer(VITESSE_NORMALE)

            # Détection d'obstacle
            if distance < SEUIL_OBSTACLE and distance > 0:
                print("--- Obstacle détecté ! ---")
                arreter()
                mode = "EVITEMENT"

                # 1. Balayage : mesurer à gauche et à droite
                tourner_tete(ANGLE_TETE_GAUCHE)
                time.sleep(TEMPS_BALAYAGE)
                dist_gauche = mesurer_distance()
                tourner_tete(ANGLE_TETE_DROITE)
                time.sleep(TEMPS_BALAYAGE)
                dist_droite = mesurer_distance()
                tourner_tete(ANGLE_TETE_CENTRE)
                time.sleep(0.2)

                # 2. Choix du côté le plus dégagé
                if dist_gauche > dist_droite:
                    direction_choisie = "gauche"
                    angle_braquage_actuel = ANGLE_BRAQUAGE   # positif = gauche
                else:
                    direction_choisie = "droite"
                    angle_braquage_actuel = -ANGLE_BRAQUAGE  # négatif = droite

                print(f"Choix: {direction_choisie} (gauche={dist_gauche:.1f}, droite={dist_droite:.1f})")
                braquer(CENTRE + angle_braquage_actuel)
                temps_debut_phase = time.time()

        # ---- Mode Évitement ----
        elif mode == "EVITEMENT":
            # Avancer lentement en restant braqué
            avancer(VITESSE_EVITEMENT)

            # Si l'obstacle est dépassé (distance > seuil), on prépare la reprise
            if distance > SEUIL_OBSTACLE:
                # Obstacle franchi, on maintient le braquage un instant puis reprise
                if time.time() - temps_debut_phase > DUREE_MAINTIEN:
                    print("--- Obstacle franchi, reprise ---")
                    arreter()
                    mode = "REPRISE"
                    temps_debut_phase = time.time()
            else:
                # Obstacle toujours présent → on continue et on reset le timer de maintien
                temps_debut_phase = time.time()

            # Pendant l'évitement, on surveille les bords pour ne pas sortir
            if bord == "gauche":
                # On est trop à gauche → on corrige en braquant à droite
                braquer(CENTRE - 10)
            elif bord == "droite":
                braquer(CENTRE + 10)

        # ---- Mode Reprise (retour progressif au centre) ----
        elif mode == "REPRISE":
            # Réduire progressivement le braquage pour revenir au centre
            facteur = 1.0 - (time.time() - temps_debut_phase) / TEMPS_REPRISE
            if facteur < 0:
                facteur = 0
            angle_cible = CENTRE + angle_braquage_actuel * facteur
            braquer(angle_cible)
            avancer(VITESSE_EVITEMENT * 0.7)

            if time.time() - temps_debut_phase > TEMPS_REPRISE:
                print("--- Reprise terminée, retour à la navigation ---")
                mode = "NAVIGATION"
                braquer(CENTRE)
                arreter()
                time.sleep(0.1)

        # Pause pour éviter de saturer la boucle
        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nSTOP")
    arreter()
    braquer(CENTRE)
    tourner_tete(ANGLE_TETE_CENTRE)
    robot.destroy()
    servos.fermer()
