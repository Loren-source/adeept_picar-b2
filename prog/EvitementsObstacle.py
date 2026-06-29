#!/usr/bin/env python3
# Mission C : Évitement d'obstacles
# Le robot évite les obstacles avec l'ultrason, reste dans la zone grâce aux IR,
# et s'arrête quand il sort de la zone (fin de mission).

import time
import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

import move
import RPIservo
import ultra
from gpiozero import InputDevice

SPEED_FORWARD   = 50    # Vitesse d'avance normale
SPEED_TURN      = 50    # Vitesse en virage
SPEED_BACK      = 40    # Vitesse de marche arrière
DIST_STOP       = 40    # Distance (cm) en dessous de laquelle on scanne
DIST_BACK       = 20    # Distance (cm) en dessous de laquelle on recule
SCAN_ANGLE      = 60    # Angle de scan gauche/droite (degrés)
TURN_TIME       = 0.6   # Durée du virage (secondes)
BACK_TIME       = 0.3   # Durée de la marche arrière (secondes)

# GPIO capteurs infrarouges de sol
LINE_PIN_LEFT   = 22
LINE_PIN_MIDDLE = 27
LINE_PIN_RIGHT  = 17


scGear = RPIservo.ServoCtrl()
scGear.moveInit()
move.setup()

track_left   = InputDevice(pin=LINE_PIN_LEFT)
track_middle = InputDevice(pin=LINE_PIN_MIDDLE)
track_right  = InputDevice(pin=LINE_PIN_RIGHT)



def read_ir_sensors():
    """Retourne les valeurs des 3 capteurs IR (0=noir/bordure, 1=blanc/zone)."""
    return track_left.value, track_middle.value, track_right.value


def is_out_of_zone():
    """
    Retourne True si le robot sort de la zone.
    Les 3 capteurs détectent la bordure noire = sortie de zone.
    """
    left, middle, right = read_ir_sensors()
    # Si tous les capteurs détectent le noir = hors zone
    if left == 0 and middle == 0 and right == 0:
        return True
    return False


def ir_correction():
    """
    Corrige la trajectoire si le robot s'approche d'une bordure.
    Retourne True si une correction a été appliquée, False sinon.
    """
    left, middle, right = read_ir_sensors()
    print(f"IR → gauche={left} milieu={middle} droite={right}")

    if middle == 0:
        # Bordure détectée devant — reculer
        print("⚠️  Bordure devant — marche arrière")
        scGear.moveAngle(0, 0)
        move.move(SPEED_BACK, -1, "mid")
        time.sleep(BACK_TIME)
        move.motorStop()
        return True

    if left == 0 and right == 1:
        # Bordure à gauche — tourner à droite
        print("⚠️  Bordure gauche — virage droite")
        scGear.moveAngle(0, -38)
        move.move(SPEED_TURN, 1, "right")
        time.sleep(0.4)
        scGear.moveAngle(0, 0)
        return True

    if right == 0 and left == 1:
        # Bordure à droite — tourner à gauche
        print("⚠️  Bordure droite — virage gauche")
        scGear.moveAngle(0, 38)
        move.move(SPEED_TURN, 1, "left")
        time.sleep(0.4)
        scGear.moveAngle(0, 0)
        return True

    return False


def get_distance():
    """Mesure la distance en filtrant les valeurs aberrantes."""
    readings = []
    for _ in range(3):
        d = ultra.checkdist()
        if d < 200:
            readings.append(d)
        time.sleep(0.02)
    if not readings:
        return 200
    return round(sum(readings) / len(readings), 2)


def scan_left_right():
    """
    Scanne à gauche et à droite avec l'ultrason.
    Retourne 'left' ou 'right' selon le côté le plus libre.
    """
    move.motorStop()

    scGear.moveAngle(1, SCAN_ANGLE)
    time.sleep(0.5)
    dist_left = get_distance()
    print(f"🔍 Distance gauche : {dist_left:.1f} cm")

    scGear.moveAngle(1, -SCAN_ANGLE)
    time.sleep(0.5)
    dist_right = get_distance()
    print(f"🔍 Distance droite : {dist_right:.1f} cm")

    scGear.moveAngle(1, 0)
    time.sleep(0.3)

    if dist_left >= dist_right:
        return 'left'
    else:
        return 'right'


def avoid_obstacle():
    """
    Gère l'évitement d'un obstacle détecté par l'ultrason.
    """
    dist = get_distance()
    print(f"📏 Distance : {dist:.1f} cm")

    if dist > DIST_STOP:
        # Voie libre — avancer
        scGear.moveAngle(0, 0)
        move.move(SPEED_FORWARD, 1, "mid")
        return

    if dist < DIST_BACK:
        # Trop proche — reculer d'abord
        print("🔴 Obstacle très proche — marche arrière")
        scGear.moveAngle(0, 0)
        move.move(SPEED_BACK, -1, "mid")
        time.sleep(BACK_TIME)
        move.motorStop()

    # Scanner gauche/droite et tourner du côté libre
    direction = scan_left_right()

    if direction == 'left':
        print("↩️  Virage gauche")
        scGear.moveAngle(0, 40)
        move.move(SPEED_TURN, 1, "left")
    else:
        print("↪️  Virage droite")
        scGear.moveAngle(0, -40)
        move.move(SPEED_TURN, 1, "right")

    time.sleep(TURN_TIME)
    scGear.moveAngle(0, 0)



if __name__ == '__main__':
    print("=== Mission C : Évitement d'obstacles ===")
    print("Ctrl+C pour arrêter.\n")

    # Orientation de la tête vers l'avant
    scGear.moveAngle(1, 0)
    scGear.moveAngle(2, 0)
    time.sleep(0.5)

    try:
        while True:
            # 1. Vérifier les capteurs IR de bordure
            if is_out_of_zone():
                print("🏁 Sortie de zone détectée — fin de mission C.")
                move.motorStop()
                break

            # 2. Correction si proche d'une bordure
            corrected = ir_correction()
            if corrected:
                continue

            # 3. Évitement d'obstacles avec l'ultrason
            avoid_obstacle()

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé par l'utilisateur.")

    finally:
        move.motorStop()
        scGear.moveAngle(0, 0)
        scGear.moveAngle(1, 0)
        scGear.moveAngle(2, 0)
        print("✅ Arrêt propre effectué.")
