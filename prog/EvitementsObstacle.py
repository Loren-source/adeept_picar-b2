

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


SPEED_FORWARD    = 50    # Vitesse en ligne droite
SPEED_TURN       = 50    # Vitesse pendant les virages d'évitement
SPEED_BACK       = 40    # Vitesse en marche arrière

# Distances ultrason (cm)
DIST_STOP        = 40    # Distance limite pour déclencher l'analyse d'obstacle
DIST_BACK        = 20    # Distance critique nécessitant une marche arrière immédiate

# Paramètres des servos et timings
SCAN_ANGLE       = 60    # Angle de rotation de la tête ultrason (degrés)
TURN_TIME        = 0.6   # Temps de braquage pour contourner l'obstacle (secondes)
BACK_TIME        = 0.3   # Temps de recul en cas d'urgence (secondes)

# Seuils de détection de la couleur bleue (Espace HSV)
BLUE_LOWER       = np.array([100, 100, 50])
BLUE_UPPER       = np.array([130, 255, 255])
BLUE_MIN_PIXELS  = 500   # Sensibilité de détection du plot bleu

# Assignation des broches GPIO pour les capteurs infrarouges (IR) de sol
LINE_PIN_LEFT    = 22
LINE_PIN_MIDDLE  = 27
LINE_PIN_RIGHT   = 17


print("🔧 Initialisation du matériel...")
scGear = RPIservo.ServoCtrl()
scGear.moveInit()  # Initialise les servos sur leurs positions de départ
move.setup()     # Initialise le contrôleur de moteurs PCA9685

# Initialisation des capteurs infrarouges de sol
track_left   = InputDevice(pin=LINE_PIN_LEFT)
track_middle = InputDevice(pin=LINE_PIN_MIDDLE)
track_right  = InputDevice(pin=LINE_PIN_RIGHT)


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
    """Capture une image et renvoie True si le plot bleu est détecté."""
    img = picam2.capture_array()
    if img is None:
        return False

    # Conversion RGB vers HSV (attention, picam2 capture en RGB natif et non BGR)
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
        scGear.moveAngle(0, -38)  # Braquage des roues vers la droite
        move.move(SPEED_TURN, 1, "right")
        time.sleep(0.4)
        scGear.moveAngle(0, 0)    # Redresse les roues
        return True

    # Cas 3 : Le robot dévie vers la droite (le capteur droit quitte le sol)
    if right == 0 and left == 1:
        print("⚠️  Alerte IR : Bordure à droite -> Virage serré à gauche.")
        scGear.moveAngle(0, 38)   # Braquage des roues vers la gauche
        move.move(SPEED_TURN, 1, "left")
        time.sleep(0.4)
        scGear.moveAngle(0, 0)    # Redresse les roues
        return True

    return False


def get_distance():
    """Effectue 3 mesures ultrason et renvoie la moyenne filtrée."""
    readings = []
    for _ in range(3):
        d = ultra.checkdist()
        if 0 < d < 200:  # Ignore les valeurs aberrantes ou hors de portée
            readings.append(d)
        time.sleep(0.02)
    if not readings:
        return 200
    return round(sum(readings) / len(readings), 2)

def scan_left_right():
    """Tourne le capteur ultrason à gauche et à droite pour évaluer le meilleur côté."""
    move.motorStop()  # Sécurité : arrêt pendant les mesures

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

    # Choisir la direction offrant le plus grand espace libre
    return 'left' if dist_left >= dist_right else 'right'

def avoid_obstacle():
    """Gère la marche avant continue et le contournement en cas d'obstacle."""
    dist = get_distance()
    print(f"📏 Obstacle devant à : {dist:.1f} cm")

    # Si la voie est libre
    if dist > DIST_STOP:
        scGear.moveAngle(0, 0)  # Roues bien droites
        move.move(SPEED_FORWARD, 1, "mid")
        return

    # Si l'obstacle est trop proche (distance critique)
    if dist < DIST_BACK:
        print("🔴 Danger : Obstacle trop près ! Marche arrière préventive.")
        scGear.moveAngle(0, 0)
        move.move(SPEED_BACK, -1, "mid")
        time.sleep(BACK_TIME)
        move.motorStop()

    # Phase d'analyse de l'environnement (Scan)
    print("🤔 Obstacle détecté. Recherche d'une voie d'évitement...")
    direction = scan_left_right()

    # Application de la manœuvre d'évitement
    if direction == 'left':
        print("↩️  Action : Évitement par la GAUCHE")
        scGear.moveAngle(0, 40)
        move.move(SPEED_TURN, 1, "left")
    else:
        print("↪️  Action : Évitement par la DROITE")
        scGear.moveAngle(0, -40)
        move.move(SPEED_TURN, 1, "right")

    time.sleep(TURN_TIME)
    scGear.moveAngle(0, 0)  # Remise en ligne droite après le virage


if __name__ == '__main__':
    print("\n=========================================")
    print("🚀 DÉMARRAGE : Mission C — PiCar-B Autonome")
    print("=========================================\n")

    # Alignement initial de la direction et du capteur ultrason
    scGear.moveAngle(0, 0)  # Roues
    scGear.moveAngle(1, 0)  # Tête ultrason axe X
    scGear.moveAngle(2, 0)  # Tête ultrason axe Y
    time.sleep(0.5)

    # Initialisation de la caméra
    picam2 = init_camera()

    # --- PHASE 1 : Attente du signal de départ (Plot Bleu) ---
    print("\n👀 Phase d'attente active : Présentez le plot bleu face à la caméra...")
    try:
        while True:
            if detect_blue(picam2):
                print("\n🔵 SIGNAL REÇU ! Le plot bleu a été validé. Départ imminent.")
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n🛑 Programme interrompu pendant la phase d'attente.")
        picam2.stop()
        sys.exit(0)

    time.sleep(0.5)

    # --- PHASE 2 : Exécution de la mission autonome ---
    print("\n🤖 Mode autonome activé. Le robot navigue...")
    try:
        while True:
            # 1. Condition d'arrêt : Sommes-nous sortis de la zone ?
            if is_out_of_zone():
                print("\n🏁 Mission accomplie : Sortie de zone détectée. Arrêt du robot.")
                break

            # 2. Sécurité des bordures : Priorité absolue aux lignes de sol
            if ir_correction():
                # Si le robot vient d'effectuer une correction de trajectoire, 
                # on saute la suite de la boucle pour ré-analyser immédiatement le sol.
                continue

            # 3. Navigation standard et évitement d'obstacles
            avoid_obstacle()

            # Petite pause pour ne pas saturer le processeur
            time.sleep(0.02)

    except KeyboardInterrupt:
        print("\n🛑 Navigation interrompue par l'utilisateur (Ctrl+C).")

    finally:
        # Assurer l'extinction complète et propre du matériel à la fermeture
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
