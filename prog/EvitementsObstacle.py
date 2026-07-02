#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mission C : Évitement d'obstacles intelligent et maintien de zone.
Le robot attend un signal visuel (papier bleu au sol), s'élance pour le quitter,
puis navigue de manière autonome en évitant les obstacles grâce aux ultrasons.
"""

import time
import sys
import os
import cv2
import numpy as np
from gpiozero import InputDevice
from picamera2 import Picamera2

# Forcer Python à chercher les modules locaux du robot
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import des modules matériels du PiCar
import move
import RPIservo
import ultra

# ==========================================
# CONFIGURATION / PARAMÈTRES GLOBAUX CORRIGÉS
# ==========================================
# Vitesses (0 à 100)
SPEED_FORWARD    = 30    # Vitesse en ligne droite (ajustée pour anticiper les obstacles)
SPEED_TURN       = 60    # CORRIGÉ : Augmenté pour donner la puissance nécessaire au pivotement
SPEED_BACK       = 35    # Vitesse en marche arrière

# Distances ultrason (cm)
DIST_STOP        = 50   # Distance limite pour déclencher l'analyse d'obstacle
DIST_BACK        = 25    # Distance critique nécessitant une marche arrière immédiate

# Paramètres des servos et timings
SCAN_ANGLE       = 60    # Angle de rotation de la tête ultrason (degrés)
TURN_TIME        = 0.8   # CORRIGÉ : Augmenté pour laisser le temps physique au robot de braquer !
BACK_TIME        = 0.4   # CORRIGÉ : Augmenté pour reculer efficacement si besoin

# Seuils de détection de la couleur bleue (Espace HSV)
BLUE_LOWER       = np.array([100, 100, 50])
BLUE_UPPER       = np.array([130, 255, 255])
BLUE_MIN_PIXELS  = 500   # Sensibilité de détection du plot bleu

# Assignation des broches GPIO pour les capteurs infrarouges (IR) de sol
LINE_PIN_LEFT    = 22
LINE_PIN_MIDDLE  = 27
LINE_PIN_RIGHT   = 17

# ==========================================
# INITIALISATION DU MATÉRIEL
# ==========================================
print("🔧 Initialisation du matériel...")
scGear = RPIservo.ServoCtrl()
scGear.moveInit()  # Initialise les servos sur leurs positions de départ
move.setup()       # Initialise le contrôleur de moteurs PCA9685

# Initialisation des capteurs infrarouges de sol
track_left   = InputDevice(pin=LINE_PIN_LEFT)
track_middle = InputDevice(pin=LINE_PIN_MIDDLE)
track_right  = InputDevice(pin=LINE_PIN_RIGHT)

# Instanciation globale du capteur ultrason avec ses pins Tr et Ec
try:
    ultrasonic_sensor = ultra.Ultrasonic(ultra.Tr, ultra.Ec)
    print("✅ Capteur Ultrason initialisé.")
except Exception as e:
    print(f"⚠️ Erreur lors de l'initialisation de l'ultrason : {e}")
    ultrasonic_sensor = None


def init_camera():
    """Initialise et configure la Picamera2 en mode RGB."""
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (640, 480), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(1)  # Temps de stabilisation de la luminosité
    print("✅ Caméra démarrée avec succès.")
    return picam2


def detect_blue(picam2):
    """Capture une image et renvoie True si le papier bleu est détecté."""
    img = picam2.capture_array()
    if img is None:
        return False

    # Conversion RGB vers HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv, BLUE_LOWER, BLUE_UPPER)
    blue_pixels = np.sum(mask == 255)

    print(f"🔵 Analyse Vision -> Pixels bleus : {blue_pixels}/{BLUE_MIN_PIXELS}")
    return blue_pixels >= BLUE_MIN_PIXELS


def read_ir_sensors():
    """Renvoie l'état des 3 capteurs de sol (1 = Sol valide, 0 = Ligne/Vide)."""
    return track_left.value, track_middle.value, track_right.value


def is_out_of_zone():
    """Vérifie si les 3 capteurs sont hors-sol, signifiant la fin du parcours."""
    left, middle, right = read_ir_sensors()
    print(f"🔍 DEBUG IR -> Gauche: {left} | Milieu: {middle} | Droite: {right}")
    
    # Si les trois capteurs lisent 0 en même temps, le robot a quitté la zone de jeu
    if left == 0 and middle == 0 and right == 0:
        return True
    return False


def ir_correction():
    """
    Analyse les capteurs de sol et ajuste la trajectoire si le robot mord sur un bord.
    Renvoie True si une action de correction a été menée.
    """
    left, middle, right = read_ir_sensors()

    # Cas 1 : Bordure détectée pile en face
    if middle == 0:
        print("⚠️  Alerte IR : Bordure devant ! Recul d'urgence.")
        scGear.moveAngle(0, 0)
        move.move(SPEED_BACK, -1, "mid")
        time.sleep(BACK_TIME)
        move.motorStop()
        return True

    # Cas 2 : Le robot dévie vers la gauche (le capteur gauche quitte le sol)
    if left == 0 and right == 1:
        print("⚠️  Alerte IR : Bordure à gauche -> Virage serré à droite.")
        scGear.moveAngle(0, -38)
        move.move(SPEED_TURN, 1, "right")
        time.sleep(0.4)
        scGear.moveAngle(0, 0)
        return True

    # Cas 3 : Le robot dévie vers la droite (le capteur droit quitte le sol)
    if right == 0 and left == 1:
        print("⚠️  Alerte IR : Bordure à droite -> Virage serré à gauche.")
        scGear.moveAngle(0, 38)
        move.move(SPEED_TURN, 1, "left")
        time.sleep(0.4)
        scGear.moveAngle(0, 0)
        return True

    return False


def get_distance():
    """Effectue 3 mesures via la méthode .distance() de la classe d'Adeept."""
    if ultrasonic_sensor is None:
        return 200

    readings = []
    for _ in range(3):
        try:
            d = ultrasonic_sensor.distance()
            if 0 < d < 200:
                readings.append(d)
        except Exception as e:
            print(f"⚠️ Erreur mesure ultrason : {e}")
        time.sleep(0.02)
        
    if not readings:
        return 200
    return round(sum(readings) / len(readings), 2)


def scan_left_right():
    """Tourne le capteur ultrason à gauche et à droite pour évaluer le meilleur côté."""
    move.motorStop()

    # Regarder à gauche
    scGear.moveAngle(1, SCAN_ANGLE)
    time.sleep(0.4)
    dist_left = get_distance()
    print(f"🔍 Scan Gauche : {dist_left:.1f} cm")

    # Regarder à droite
    scGear.moveAngle(1, -SCAN_ANGLE)
    time.sleep(0.5)
    dist_right = get_distance()
    print(f"🔍 Scan Droit : {dist_right:.1f} cm")

    # Replacer le capteur bien en face
    scGear.moveAngle(1, 0)
    time.sleep(0.3)

    return 'left' if dist_left >= dist_right else 'right'


def avoid_obstacle():
    """Gère la marche avant continue et le contournement en cas d'obstacle."""
    dist = get_distance()
    print(f"📏 Obstacle devant à : {dist:.1f} cm")

    if dist > DIST_STOP:
        scGear.moveAngle(0, 0)
        move.move(SPEED_FORWARD, 1, "mid")
        return

    if dist < DIST_BACK:
        print("🔴 Danger : Obstacle trop près ! Marche arrière préventive.")
        scGear.moveAngle(0, 0)
        move.move(SPEED_BACK, -1, "mid")
        time.sleep(BACK_TIME)
        move.motorStop()

    print("🤔 Obstacle détecté. Recherche d'une voie d'évitement...")
    direction = scan_left_right()

    if direction == 'left':
        print("↩️  Action : Évitement par la GAUCHE")
        scGear.moveAngle(0, 40)              # Braquage des roues
        move.move(SPEED_TURN, 1, "left")    # Propulsion adaptée
    else:
        print("↪️  Action : Évitement par la DROITE")
        scGear.moveAngle(0, -40)             # Braquage des roues
        move.move(SPEED_TURN, 1, "right")   # Propulsion adaptée

    time.sleep(TURN_TIME)                    # Temps nécessaire pour que le véhicule pivote
    scGear.moveAngle(0, 0)                   # Redressage des roues après la manœuvre


# ==========================================
# BOUCLE PRINCIPALE EXÉCUTABLE
# ==========================================
if __name__ == '__main__':
    print("\n=========================================")
    print("🚀 DÉMARRAGE : Mission C — PiCar-B Autonome")
    print("=========================================\n")

    scGear.moveAngle(0, 0)  # Roues
    scGear.moveAngle(1, 0)  # Tête ultrason axe X
    scGear.moveAngle(2, 0)  # Tête ultrason axe Y
    time.sleep(0.5)

    picam2 = init_camera()

    print("\n👀 Phase d'attente active : Présentez le papier bleu face à la caméra...")
    try:
        while True:
            if detect_blue(picam2):
                print("\n🔵 SIGNAL REÇU ! Le papier bleu a été validé.")
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n🛑 Programme interrompu pendant la phase d'attente.")
        picam2.stop()
        sys.exit(0)

    time.sleep(0.2)

    print("\n🤖 Mode autonome activé. Le robot navigue...")
    print("🚀 Propulsion initiale pour quitter la marque bleue de départ...")
    scGear.moveAngle(0, 0)
    move.move(SPEED_FORWARD, 1, "mid")
    time.sleep(0.5) 
    
    try:
        while True:
            if is_out_of_zone():
                print("\n🏁 Mission accomplie : Sortie de zone détectée. Arrêt du robot.")
                break

            if ir_correction():
                continue

            avoid_obstacle()
            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\n🛑 Navigation interrompue par l'utilisateur (Ctrl+C).")

    finally:
        print("\n⚙️  Fermeture propre des périphériques...")
        try:
            picam2.stop()
        except Exception:
            pass
        
        move.motorStop()
        scGear.moveAngle(0, 0)
        scGear.moveAngle(1, 0)
        scGear.moveAngle(2, 0)
        
        try:
            move.destroy()
        except Exception:
            pass
            
        print("✅ Système réinitialisé. Arrêt complet.")
