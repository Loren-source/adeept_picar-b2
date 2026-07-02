#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mission C Finale : Évitement d'obstacles intelligent et maintien de zone.
Utilise l'initialisation Adafruit PCA9685 (Adresse 0x5f) pour les servomoteurs.
"""

import time
import sys
import os
import cv2
import numpy as np
from gpiozero import InputDevice
from picamera2 import Picamera2

# Matériel Adafruit pour les Servomoteurs
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

# Forcer Python à chercher les modules locaux pour les moteurs de traction
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

import move
import ultra

# ==========================================
# CONFIGURATION / PARAMÈTRES GLOBAUX
# ==========================================
PCA_ADDRESS      = 0x5f
PWM_FREQ         = 50
MIN_PULSE        = 500
MAX_PULSE        = 2400
ACTUATION        = 180

CANAL_TETE_H     = 1     # Servomoteur horizontal de la tête ultrason
CANAL_DIRECTION  = 2     # Servomoteur de direction des roues avant

# Angles absolus Adafruit (Base 90° au centre)
TETE_CENTRE      = 90
TETE_GAUCHE      = 150   
TETE_DROITE      = 30    

ROUES_CENTRE     = 90
ROUES_GAUCHE     = 128   
ROUES_DROITE     = 52    

# Vitesses moteurs (0 à 100)
SPEED_FORWARD    = 35    
SPEED_TURN       = 45    
SPEED_BACK       = 35    

# Distances ultrason (cm)
DIST_STOP        = 45    
DIST_BACK        = 25    

# Timings de mouvement (secondes)
TURN_TIME        = 0.85  
BACK_TIME        = 0.4   

# Seuils de détection de la couleur bleue (Espace HSV)
BLUE_LOWER       = np.array([100, 100, 50])
BLUE_UPPER       = np.array([130, 255, 255])
BLUE_MIN_PIXELS  = 500   

# Assignation des broches GPIO pour les capteurs infrarouges (IR) de sol
LINE_PIN_LEFT    = 22
LINE_PIN_MIDDLE  = 27
LINE_PIN_RIGHT   = 17

# ==========================================
# INITIALISATION DU MATÉRIEL
# ==========================================
print("🔧 Initialisation du matériel...")

move.setup()

try:
    i2c = busio.I2C(SCL, SDA)
    pca = PCA9685(i2c, address=PCA_ADDRESS)
    pca.frequency = PWM_FREQ
    
    servo_tete = servo.Servo(pca.channels[CANAL_TETE_H], min_pulse=MIN_PULSE, max_pulse=MAX_PULSE, actuation_range=ACTUATION)
    servo_dir  = servo.Servo(pca.channels[CANAL_DIRECTION], min_pulse=MIN_PULSE, max_pulse=MAX_PULSE, actuation_range=ACTUATION)
    print("✅ Contrôleur de Servomoteurs Adafruit (0x5f) initialisé.")
except Exception as e:
    print(f"❌ Erreur critique d'initialisation des servos : {e}")
    sys.exit(1)

track_left   = InputDevice(pin=LINE_PIN_LEFT)
track_middle = InputDevice(pin=LINE_PIN_MIDDLE)
track_right  = InputDevice(pin=LINE_PIN_RIGHT)

try:
    ultrasonic_sensor = ultra.Ultrasonic(ultra.Tr, ultra.Ec)
    print("✅ Capteur Ultrason prêt.")
except Exception as e:
    print(f"⚠️ Erreur ultrason : {e}")
    ultrasonic_sensor = None


# ==========================================
# FONCTIONS DE NAVIGATION ET DES SERVOS
# ==========================================
def positionner_servos_centre():
    servo_dir.angle = ROUES_CENTRE
    servo_tete.angle = TETE_CENTRE
    time.sleep(0.3)

def get_distance():
    if ultrasonic_sensor is None:
        return 200
    readings = []
    for _ in range(3):
        try:
            d = ultrasonic_sensor.distance()
            if 0 < d < 200:
                readings.append(d)
        except Exception:
            pass
        time.sleep(0.02)
    return round(sum(readings) / len(readings), 2) if readings else 200


def scan_left_right():
    """Fait pivoter physiquement la tête à gauche et à droite pour mesurer."""
    move.motorStop()
    time.sleep(0.1)

    # 1. Balayage à GAUCHE (150°)
    print("🔄 Scan : La tête pivote à GAUCHE...")
    servo_tete.angle = TETE_GAUCHE
    time.sleep(0.6)  
    dist_left = get_distance()
    print(f"📊 Distance Gauche : {dist_left:.1f} cm")

    # 2. Balayage à DROITE (30°)
    print("🔄 Scan : La tête pivote à DROITE...")
    servo_tete.angle = TETE_DROITE
    time.sleep(0.8)  
    dist_right = get_distance()
    print(f"📊 Distance Droite : {dist_right:.1f} cm")

    # 3. Retour au CENTRE (90°)
    print("🔄 Scan terminé : Remise de la tête au CENTRE.")
    servo_tete.angle = TETE_CENTRE
    time.sleep(0.4)

    return 'left' if dist_left >= dist_right else 'right'


def avoid_obstacle():
    dist = get_distance()
    print(f"📏 Obstacle devant à : {dist:.1f} cm")

    if dist > DIST_STOP:
        servo_dir.angle = ROUES_CENTRE  
        move.move(SPEED_FORWARD, 1, "mid")
        return

    if dist < DIST_BACK:
        print("🔴 Danger : Obstacle trop près ! Marche arrière d'urgence.")
        servo_dir.angle = ROUES_CENTRE
        move.move(SPEED_BACK, -1, "mid")
        time.sleep(BACK_TIME)
        move.motorStop()

    print("🤔 Obstacle détecté. Analyse du champ libre...")
    direction = scan_left_right()

    if direction == 'left':
        print("↩️  Action : Évitement par la GAUCHE")
        servo_dir.angle = ROUES_GAUCHE      
        move.move(SPEED_TURN, 1, "left")
    else:
        print("↪️  Action : Évitement par la DROITE")
        servo_dir.angle = ROUES_DROITE      
        move.move(SPEED_TURN, 1, "right")

    time.sleep(TURN_TIME)
    servo_dir.angle = ROUES_CENTRE      


# ==========================================
# FONCTIONS DE VISION (CAMÉRA)
# ==========================================
def init_camera():
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(main={"size": (640, 480), "format": "RGB888"})
    picam2.configure(config)
    picam2.start()
    time.sleep(1)
    print("✅ Caméra démarrée avec succès.")
    return picam2

def detect_blue(picam2):
    img = picam2.capture_array()
    if img is None:
        return False
    hsv = cv2.cvtColor(img, cv2.COLOR_RGB2HSV)
    mask = cv2.inRange(hsv, BLUE_LOWER, BLUE_UPPER)
    blue_pixels = np.sum(mask == 255)
    print(f"🔵 Vision -> Pixels bleus : {blue_pixels}/{BLUE_MIN_PIXELS}")
    return blue_pixels >= BLUE_MIN_PIXELS


# ==========================================
# GESTION DES BORDURES (CAPTEURS IR)
# ==========================================
def read_ir_sensors():
    return track_left.value, track_middle.value, track_right.value

def is_out_of_zone():
    left, middle, right = read_ir_sensors()
    print(f"🔍 DEBUG IR -> Gauche: {left} | Milieu: {middle} | Droite: {right}")
    
    # 🔓 MODIFICATION APPLIQUÉE : On renvoie False pour le moment afin d'empêcher 
    # le robot de se couper direct. Tu l'arrêteras manuellement avec Ctrl+C.
    return False

def ir_correction():
    # Desactivé temporairement pour éviter les interférences avec le sol non calibré
    return False


# ==========================================
# BOUCLE PRINCIPALE EXÉCUTABLE
# ==========================================
if __name__ == '__main__':
    print("\n=========================================")
    print("🚀 DÉMARRAGE : Mission C — PiCar-B Autonome")
    print("=========================================\n")

    positionner_servos_centre()
    picam2 = init_camera()

    print("\n👀 Phase d'attente active : Présentez le papier bleu face à la caméra...")
    try:
        while True:
            if detect_blue(picam2):
                print("\n🔵 SIGNAL REÇU ! Le papier bleu a été validé.")
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        picam2.stop()
        pca.deinit()
        sys.exit(0)

    time.sleep(0.2)

    print("\n🤖 Mode autonome activé. Le robot navigue...")
    print("🚀 Propulsion initiale pour quitter la marque bleue de départ...")
    servo_dir.angle = ROUES_CENTRE
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
        print("\n🛑 Navigation interrompue.")

    finally:
        print("\n⚙️  Fermeture propre des périphériques...")
        try:
            picam2.stop()
        except Exception:
            pass
        
        move.motorStop()
        positionner_servos_centre()
        
        try:
            pca.deinit()
        except Exception:
            pass
            
        print("✅ Système réinitialisé. Arrêt complet.")
