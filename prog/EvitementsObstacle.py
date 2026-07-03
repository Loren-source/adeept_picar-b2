#!/usr/bin/env python3
# -*- coding: utf-8 -*-


import time
import sys
import os
import threading
import cv2
import numpy as np
from gpiozero import InputDevice
from picamera2 import Picamera2

from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

import move
import ultra


PCA_ADDRESS      = 0x5f
PWM_FREQ         = 50
MIN_PULSE        = 500
MAX_PULSE        = 2400
ACTUATION        = 180

CANAL_YEUX_0     = 0
CANAL_YEUX_1     = 1
CANAL_DIRECTION  = 2

TETE_CENTRE      = 90
TETE_GAUCHE      = 150   # offset +60
TETE_DROITE      = 30    # offset -60

ROUES_CENTRE     = 90
ROUES_GAUCHE     = 128
ROUES_DROITE     = 52

VITESSE_MARCHE     = 25
VITESSE_EVITEMENT  = 25
VITESSE_RECUL      = 14

# Seuils en CM (ultra.py renvoie des cm)
SEUIL_OBSTACLE        = 40
SEUIL_COLLISION       = 18
SEUIL_PASSAGE_LIBRE   = 40
DISTANCE_MAX_FAUSSE   = 200   # valeur "pas de mesure fiable"

PERIODE_ULTRASON  = 0.08
PERIODE_IR        = 0.03
PERIODE_DECISION  = 0.05

# Offsets de scan (par rapport au centre 90°), bornés à [-60, +60]
ANGLES_SCAN = list(range(-60, 61, 10))

DUREE_RECUL_URGENCE  = 0.8
DUREE_RECUL_BORDURE  = 0.5
DUREE_PAS_EVITEMENT  = 1.5
MAX_PAS_EVITEMENT    = 10
DUREE_RECENTRAGE     = 1.5

# Détection papier bleu (déclenchement de mission, comme ton script d'origine)
BLUE_LOWER      = np.array([100, 100, 50])
BLUE_UPPER      = np.array([130, 255, 255])
BLUE_MIN_PIXELS = 500

LINE_PIN_LEFT   = 22
LINE_PIN_MIDDLE = 27
LINE_PIN_RIGHT  = 17



print("🔧 Initialisation du matériel...")

move.setup()

try:
    i2c = busio.I2C(SCL, SDA)
    pca = PCA9685(i2c, address=PCA_ADDRESS)
    pca.frequency = PWM_FREQ

    servo_yeux_0 = servo.Servo(pca.channels[CANAL_YEUX_0], min_pulse=MIN_PULSE, max_pulse=MAX_PULSE, actuation_range=ACTUATION)
    servo_yeux_1 = servo.Servo(pca.channels[CANAL_YEUX_1], min_pulse=MIN_PULSE, max_pulse=MAX_PULSE, actuation_range=ACTUATION)
    servo_dir    = servo.Servo(pca.channels[CANAL_DIRECTION], min_pulse=MIN_PULSE, max_pulse=MAX_PULSE, actuation_range=ACTUATION)
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



etat_lock = threading.Lock()
etat = {
    "distance": None,
    "pattern": "000",
    "running": True,
}

dernier_angle_direction = 0  # >0 = dernier virage GAUCHE, <0 = dernier virage DROITE


def get_distance_cm():
    """Moyenne de 3 mesures ultrason, en CM. Renvoie None si rien de fiable."""
    if ultrasonic_sensor is None:
        return None
    readings = []
    for _ in range(3):
        try:
            d = ultrasonic_sensor.distance()
            if 0 < d < DISTANCE_MAX_FAUSSE:
                readings.append(d)
        except Exception:
            pass
        time.sleep(0.01)
    return round(sum(readings) / len(readings), 2) if readings else None


def lire_pattern_ir():
    """'1' = bordure détectée sur ce capteur. Inverse ici si ta polarité est opposée."""
    g = int(bool(track_left.value))
    m = int(bool(track_middle.value))
    d = int(bool(track_right.value))
    return f"{g}{m}{d}"


def thread_ultrason():
    while True:
        with etat_lock:
            running = etat["running"]
        if not running:
            break
        d = get_distance_cm()
        with etat_lock:
            etat["distance"] = d
        time.sleep(PERIODE_ULTRASON)


def thread_ir():
    while True:
        with etat_lock:
            running = etat["running"]
        if not running:
            break
        p = lire_pattern_ir()
        with etat_lock:
            etat["pattern"] = p
        time.sleep(PERIODE_IR)


def lire_etat():
    with etat_lock:
        return etat["distance"], etat["pattern"]


def arreter_threads():
    with etat_lock:
        etat["running"] = False



def positionner_servos_centre():
    servo_dir.angle = ROUES_CENTRE
    servo_yeux_0.angle = TETE_CENTRE
    servo_yeux_1.angle = TETE_CENTRE
    time.sleep(0.3)


def stop_robot():
    move.motorStop()
    servo_dir.angle = ROUES_CENTRE


def set_head_offset(offset):
    """Fait pivoter les DEUX yeux (CH00+CH01) ensemble, offset borné à [-60,+60]."""
    offset = max(-60, min(60, offset))
    angle = TETE_CENTRE + offset
    servo_yeux_0.angle = angle
    servo_yeux_1.angle = angle


def offset_vers_angle_roues(offset):
    """Convertit un offset de scan (-60..+60) en angle absolu du servo de direction."""
    offset = max(-60, min(60, offset))
    if offset >= 0:
        return ROUES_CENTRE + (offset / 60.0) * (ROUES_GAUCHE - ROUES_CENTRE)
    else:
        return ROUES_CENTRE + (offset / 60.0) * (ROUES_CENTRE - ROUES_DROITE)


def avancer_tout_droit():
    set_head_offset(0)
    servo_dir.angle = ROUES_CENTRE
    move.move(VITESSE_MARCHE, 1, "mid")


def obstacle_detecte(distance):
    return distance is not None and distance < SEUIL_OBSTACLE


def collision_imminente(distance):
    return distance is not None and distance < SEUIL_COLLISION


def bordure_detectee(pattern):
    return pattern != "000"


def alerte_sonore(msg):
    # Pas de buzzer câblé sur ce robot -> on garde une trace console.
    print(f"🔔 {msg}")



def recul_urgence():
    print("[URGENCE] Obstacle trop proche -> recul")
    alerte_sonore("Recul d'urgence")

    stop_robot()
    time.sleep(0.1)

    set_head_offset(0)
    servo_dir.angle = ROUES_CENTRE

    move.move(VITESSE_RECUL, -1, "mid")
    time.sleep(DUREE_RECUL_URGENCE)

    stop_robot()
    time.sleep(0.2)


def dernier_angle_recentrer():
    global dernier_angle_direction
    if dernier_angle_direction > 0:
        return -60
    elif dernier_angle_direction < 0:
        return 60
    else:
        return 60


def tourner_roues(offset):
    global dernier_angle_direction
    servo_dir.angle = offset_vers_angle_roues(offset)
    if offset != 0:
        dernier_angle_direction = offset


def eviter_bordure(pattern):
    print(f"[BORDURE] Détectée : {pattern}")
    alerte_sonore("Bordure détectée")

    stop_robot()
    time.sleep(0.1)

    set_head_offset(0)
    servo_dir.angle = ROUES_CENTRE

    move.move(VITESSE_RECUL, -1, "mid")
    time.sleep(DUREE_RECUL_BORDURE)
    stop_robot()
    time.sleep(0.4)

    if pattern in ("100", "110"):
        offset = -60
        print("[BORDURE] gauche -> correction droite")
        tourner_roues(offset)
        move.move(VITESSE_EVITEMENT, 1, "right")

    elif pattern in ("001", "011"):
        offset = 60
        print("[BORDURE] droite -> correction gauche")
        tourner_roues(offset)
        move.move(VITESSE_EVITEMENT, 1, "left")

    else:
        offset = dernier_angle_recentrer()
        print("[BORDURE] devant/ambigu -> recul plus long puis correction")
        tourner_roues(-offset)
        move.move(20, -1, "mid")
        time.sleep(1.0)
        stop_robot()
        tourner_roues(offset)
        move.move(VITESSE_EVITEMENT, 1, "left" if offset > 0 else "right")
        time.sleep(1.0)
        stop_robot()
        servo_dir.angle = ROUES_CENTRE
        return

    time.sleep(0.25)
    stop_robot()
    servo_dir.angle = ROUES_CENTRE


# ==========================================
# SCAN RADAR (yeux CH00+CH01)
# ==========================================
def scanner_environnement():
    mesures = []
    print("[SCAN] Début scan")

    stop_robot()
    time.sleep(0.1)

    for offset in ANGLES_SCAN:
        _, pattern = lire_etat()
        if bordure_detectee(pattern):
            print("[SCAN] Bordure détectée pendant scan")
            break

        set_head_offset(offset)
        time.sleep(0.15)

        d = get_distance_cm()
        if d is None:
            d = DISTANCE_MAX_FAUSSE

        libre = d >= SEUIL_PASSAGE_LIBRE

        mesures.append({"angle": offset, "distance": d, "libre": libre})
        print(f"[SCAN] offset={offset:>4} | distance={d:>5.0f}cm | libre={libre}")

    set_head_offset(0)
    time.sleep(0.1)

    return mesures


def detecter_gaps(mesures):
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
    return gaps


def score_gap(gap):
    largeur = abs(gap[-1]["angle"] - gap[0]["angle"]) + 10
    distance_moyenne = sum(p["distance"] for p in gap) / len(gap)
    angle_centre = gap[len(gap) // 2]["angle"]

    penalite_angle = abs(angle_centre) * 20
    penalite_extreme = 800 if abs(angle_centre) >= 50 else 0

    return largeur * 20 + distance_moyenne - penalite_angle - penalite_extreme


def choisir_meilleur_gap(gaps):
    if not gaps:
        return None

    candidats_centraux = []
    for gap in gaps:
        angle_centre = gap[len(gap) // 2]["angle"]
        largeur = abs(gap[-1]["angle"] - gap[0]["angle"]) + 10
        if abs(angle_centre) <= 30 and largeur >= 20:
            candidats_centraux.append(gap)

    if candidats_centraux:
        meilleur_gap = max(candidats_centraux, key=score_gap)
        print("[CHOIX] Mode central : passage entre obstacles")
    else:
        meilleur_gap = max(gaps, key=score_gap)
        print("[CHOIX] Mode secours : passage latéral")

    point_centre = meilleur_gap[len(meilleur_gap) // 2]
    angle_choisi = point_centre["angle"]

    print("[CHOIX] Passage choisi :")
    print(f"        début  = {meilleur_gap[0]['angle']}")
    print(f"        fin    = {meilleur_gap[-1]['angle']}")
    print(f"        centre = {angle_choisi}")
    print(f"        score  = {score_gap(meilleur_gap):.1f}")

    return angle_choisi


def choisir_direction_par_radar():
    mesures = scanner_environnement()
    if not mesures:
        print("[SCAN] Aucune mesure exploitable")
        return None

    gaps = detecter_gaps(mesures)
    if not gaps:
        print("[SCAN] Aucun passage libre")
        return None

    return choisir_meilleur_gap(gaps)


# ==========================================
# MOUVEMENTS SURVEILLÉS
# ==========================================
def avancer_surveille(duree, vitesse, offset_direction):
    debut = time.time()

    tourner_roues(offset_direction)
    position = "left" if offset_direction > 0 else ("right" if offset_direction < 0 else "mid")
    move.move(vitesse, 1, position)

    while time.time() - debut < duree:
        distance, pattern = lire_etat()

        if collision_imminente(distance):
            print("[SURVEILLANCE] Collision imminente")
            stop_robot()
            recul_urgence()
            return False

        if bordure_detectee(pattern):
            print("[SURVEILLANCE] Bordure pendant mouvement")
            stop_robot()
            eviter_bordure(pattern)
            return False

        time.sleep(PERIODE_DECISION)

    return True


def recentrer_sur_voie(offset_precedent, duree_max=DUREE_RECENTRAGE):
    print("[RECENTRAGE] Contre-braquage adaptatif")

    offset_recentrage = -offset_precedent
    debut = time.time()

    set_head_offset(0)
    tourner_roues(offset_recentrage)
    position = "left" if offset_recentrage > 0 else ("right" if offset_recentrage < 0 else "mid")
    move.move(VITESSE_MARCHE, 1, position)

    while time.time() - debut < duree_max:
        distance, pattern = lire_etat()

        if collision_imminente(distance):
            recul_urgence()
            return False

        if bordure_detectee(pattern):
            eviter_bordure(pattern)
            return False

        if distance is None or distance > SEUIL_OBSTACLE:
            break

        time.sleep(PERIODE_DECISION)

    stop_robot()
    servo_dir.angle = ROUES_CENTRE
    set_head_offset(0)
    time.sleep(0.5)

    return True


# ==========================================
# CONTOURNEMENT MULTI-OBSTACLES
# ==========================================
def contourner_obstacle_gap():
    global dernier_angle_direction
    print("[OBSTACLE] Contournement dynamique")

    offset_actuel = 0
    stop_robot()
    time.sleep(0.1)

    for i in range(MAX_PAS_EVITEMENT):
        distance, pattern = lire_etat()

        if collision_imminente(distance):
            recul_urgence()
            continue

        if bordure_detectee(pattern):
            eviter_bordure(pattern)
            continue

        if not obstacle_detecte(distance):
            print("[OBSTACLE] Plus d'obstacle devant -> recentrage obligatoire")

            ok = avancer_surveille(1.5, VITESSE_EVITEMENT, -dernier_angle_direction)
            if not ok:
                continue

            ok = avancer_surveille(0.50, VITESSE_MARCHE, 0)
            if not ok:
                continue

            print("[OBSTACLE] Recentrage terminé")
            return

        angle_scan = choisir_direction_par_radar()

        if angle_scan is None:
            print("[ACTION] Aucun gap -> recul")
            recul_urgence()
            continue

        offset_actuel = angle_scan
        dernier_angle_direction = angle_scan

        print(f"[ACTION] pas {i + 1}/{MAX_PAS_EVITEMENT}")
        print(f"         offset choisi = {angle_scan}")

        ok = avancer_surveille(DUREE_PAS_EVITEMENT, VITESSE_EVITEMENT, angle_scan)
        if not ok:
            continue

    print("[SÉCURITÉ] Trop de tentatives -> recul long")
    recul_urgence()
    recentrer_sur_voie(offset_actuel)


# ==========================================
# VISION (déclenchement papier bleu)
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
# BOUCLE PRINCIPALE
# ==========================================
def main():
    print("============================================")
    print("MISSION C — RADAR + THREADS + BORDURE IR")
    print("Ctrl+C pour arrêter")
    print("============================================")

    positionner_servos_centre()
    picam2 = init_camera()

    print("\n👀 Phase d'attente active : présentez le papier bleu face à la caméra...")
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

    t_ultrason = threading.Thread(target=thread_ultrason, daemon=True)
    t_ir = threading.Thread(target=thread_ir, daemon=True)

    try:
        print("\n🤖 Mode autonome activé. Le robot navigue...")
        print("🚀 Propulsion initiale pour quitter la marque bleue de départ...")
        servo_dir.angle = ROUES_CENTRE
        set_head_offset(0)
        move.move(VITESSE_MARCHE, 1, "mid")
        time.sleep(0.5)

        t_ultrason.start()
        t_ir.start()
        time.sleep(0.5)

        while True:
            distance, pattern = lire_etat()

            if distance is not None:
                print(f"[INFO] distance={distance:.0f}cm | pattern={pattern}")
            else:
                print(f"[INFO] distance=None | pattern={pattern}")

            if collision_imminente(distance):
                recul_urgence()

            elif bordure_detectee(pattern):
                eviter_bordure(pattern)

            elif obstacle_detecte(distance):
                contourner_obstacle_gap()

            else:
                avancer_tout_droit()

            time.sleep(PERIODE_DECISION)

    except KeyboardInterrupt:
        print("\n[FIN] Arrêt utilisateur")

    finally:
        print("[SÉCURITÉ] Arrêt complet")

        arreter_threads()
        time.sleep(0.2)

        try:
            picam2.stop()
        except Exception:
            pass

        stop_robot()
        positionner_servos_centre()

        try:
            pca.deinit()
        except Exception:
            pass

        print("✅ Système sécurisé.")


if __name__ == "__main__":
    main()
