#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import threading

from motor import RobotMotor
from servo import RobotServos
from Ultra import Ultrasonic
from line import LineTracker

# ============================================================
# INITIALISATION
# ============================================================

robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()
ultrasonic = Ultrasonic()

# ============================================================
# CONFIGURATION
# ============================================================

# Servo de direction (CH0)
ANGLE_CENTRE = 97
ANGLE_GAUCHE = 135
ANGLE_DROITE = 60

# Servo tête (CH1)
TETE_CENTRE = 97
SCAN_GAUCHE = 40
SCAN_DROITE = 150
PAS_SCAN = 10

# Vitesses
VITESSE_AVANCE = 30
VITESSE_EVITEMENT = 22
VITESSE_RECUL = 18

# Distances (mm)
SEUIL_OBSTACLE = 450
SEUIL_DANGER = 180
SEUIL_PASSAGE = 500
DISTANCE_FAUSSE = 3000

# Temporisations
PERIODE_ULTRASON = 0.05
PERIODE_IR = 0.03
PERIODE_DECISION = 0.05

DUREE_RECUL = 0.6
DUREE_CORRECTION = 0.35

MAX_PAS_EVITEMENT = 10

# ============================================================
# ETAT PARTAGE ENTRE THREADS
# ============================================================

etat = {
    "distance": DISTANCE_FAUSSE,
    "pattern": (1, 1, 1),
    "running": True
}

lock = threading.Lock()

# ============================================================
# FONCTIONS SERVO
# ============================================================

def roues(angle):
    angle = max(0, min(180, angle))
    servos.set_angle(0, angle)


def tete(angle):
    angle = max(0, min(180, angle))
    servos.set_angle(1, angle)

# ============================================================
# FONCTIONS MOTEUR
# ============================================================

def avancer(vitesse=VITESSE_AVANCE):
    robot.drive_with_ramp(vitesse, 1, 0.05)


def reculer(vitesse=VITESSE_RECUL):
    robot.drive_with_ramp(vitesse, -1, 0.05)


def stop():
    robot.stopper()

# ============================================================
# THREAD ULTRASON
# ============================================================

def lecture_ultrason():

    while True:

        with lock:
            if not etat["running"]:
                break

        distance = ultrasonic.get_distance()

        if distance <= 0:
            distance = DISTANCE_FAUSSE

        with lock:
            etat["distance"] = distance

        time.sleep(PERIODE_ULTRASON)

# ============================================================
# THREAD IR
# ============================================================

def lecture_ir():

    while True:

        with lock:
            if not etat["running"]:
                break

        valeurs = tracker.get_status()

        pattern = (
            valeurs["left"],
            valeurs["middle"],
            valeurs["right"]
        )

        with lock:
            etat["pattern"] = pattern

        time.sleep(PERIODE_IR)

# ============================================================
# LECTURE SYNCHRONISEE
# ============================================================

def lire_etat():

    with lock:
        return (
            etat["distance"],
            etat["pattern"]
        )

# ============================================================
# DEMARRAGE
# ============================================================

def demarrer_threads():

    t1 = threading.Thread(
        target=lecture_ultrason,
        daemon=True
    )

    t2 = threading.Thread(
        target=lecture_ir,
        daemon=True
    )

    t1.start()
    t2.start()

    return t1, t2


def arreter_threads():

    with lock:
        etat["running"] = False

# ============================================================
# DETECTION
# ============================================================

def obstacle_detecte(distance):
    return distance < SEUIL_OBSTACLE


def collision_imminente(distance):
    return distance < SEUIL_DANGER


def bordure_detectee(pattern):
    """
    1 = noir
    0 = blanc

    Si un capteur voit du blanc,
    on considère que le robot approche
    de la limite de la zone.
    """
    return 0 in pattern


# ============================================================
# SCAN RADAR
# ============================================================

def scanner():

    mesures = []

    stop()

    time.sleep(0.10)

    for angle in range(SCAN_GAUCHE,
                       SCAN_DROITE + PAS_SCAN,
                       PAS_SCAN):

        tete(angle)

        time.sleep(0.12)

        distance = ultrasonic.get_distance()

        if distance <= 0:
            distance = DISTANCE_FAUSSE

        libre = distance >= SEUIL_PASSAGE

        mesures.append({
            "angle": angle,
            "distance": distance,
            "libre": libre
        })

        print(
            f"[SCAN] {angle:3d}° "
            f"{distance:5.0f} mm "
            f"libre={libre}"
        )

    tete(TETE_CENTRE)

    return mesures


# ============================================================
# RECHERCHE DES PASSAGES
# ============================================================

def detecter_gaps(mesures):

    gaps = []

    courant = []

    for point in mesures:

        if point["libre"]:

            courant.append(point)

        else:

            if courant:

                gaps.append(courant)

            courant = []

    if courant:

        gaps.append(courant)

    return gaps


# ============================================================
# SCORE D'UN PASSAGE
# ============================================================

def score_gap(gap):

    largeur = len(gap)

    distance = sum(
        p["distance"] for p in gap
    ) / largeur

    centre = gap[largeur // 2]["angle"]

    penalite = abs(centre - TETE_CENTRE)

    return (
        largeur * 250
        + distance
        - penalite * 12
    )


# ============================================================
# CHOIX DU MEILLEUR PASSAGE
# ============================================================

def choisir_gap(gaps):

    if not gaps:
        return None

    meilleur = max(
        gaps,
        key=score_gap
    )

    debut = meilleur[0]["angle"]
    fin = meilleur[-1]["angle"]
    centre = meilleur[len(meilleur)//2]["angle"]

    print()

    print("Passage choisi")
    print("----------------------")
    print("Début :", debut)
    print("Fin   :", fin)
    print("Centre:", centre)
    print("Score :", score_gap(meilleur))

    return centre


# ============================================================
# CONVERSION EN ANGLE DES ROUES
# ============================================================

def angle_direction(angle_scan):

    erreur = angle_scan - TETE_CENTRE

    if abs(erreur) < 8:

        return ANGLE_CENTRE

    if erreur < 0:

        return ANGLE_GAUCHE

    return ANGLE_DROITE


# ============================================================
# DECISION
# ============================================================

def choisir_direction():

    mesures = scanner()

    if not mesures:
        return None

    gaps = detecter_gaps(mesures)

    if not gaps:

        print("Aucun passage trouvé")

        return None

    angle_scan = choisir_gap(gaps)

    if angle_scan is None:
        return None

    return angle_direction(angle_scan)

# ============================================================
# SECURITES
# ============================================================

def recul_urgence():

    print("[URGENCE] Obstacle trop proche")

    stop()
    time.sleep(0.15)

    roues(ANGLE_CENTRE)

    reculer()
    time.sleep(DUREE_RECUL)

    stop()
    time.sleep(0.2)


def corriger_bordure(pattern):

    print(f"[IR] {pattern}")

    stop()
    time.sleep(0.1)

    reculer()
    time.sleep(0.4)

    stop()

    if pattern[0] == 0:
        # Bord à gauche
        roues(ANGLE_DROITE)

    elif pattern[2] == 0:
        # Bord à droite
        roues(ANGLE_GAUCHE)

    else:
        # Devant ou ambigu
        roues(ANGLE_GAUCHE)

    avancer(VITESSE_EVITEMENT)
    time.sleep(DUREE_CORRECTION)

    stop()

    roues(ANGLE_CENTRE)


# ============================================================
# AVANCEMENT SURVEILLE
# ============================================================

def avancer_surveille(duree, angle):

    roues(angle)
    avancer(VITESSE_EVITEMENT)

    debut = time.time()

    while time.time() - debut < duree:

        distance, pattern = lire_etat()

        if collision_imminente(distance):

            stop()
            recul_urgence()
            return False

        if bordure_detectee(pattern):

            stop()
            corriger_bordure(pattern)
            return False

        time.sleep(PERIODE_DECISION)

    stop()

    return True


# ============================================================
# CONTOURNEMENT
# ============================================================

def contourner():

    print()
    print("===== CONTORNEMENT =====")

    for tentative in range(MAX_PAS_EVITEMENT):

        distance, pattern = lire_etat()

        if collision_imminente(distance):

            recul_urgence()
            continue

        if bordure_detectee(pattern):

            corriger_bordure(pattern)
            continue

        if not obstacle_detecte(distance):

            print("Obstacle dépassé")

            roues(ANGLE_CENTRE)

            avancer(VITESSE_AVANCE)
            time.sleep(0.6)

            stop()

            return

        angle = choisir_direction()

        if angle is None:

            print("Aucun passage")

            recul_urgence()

            continue

        print(f"Direction roues : {angle}")

        ok = avancer_surveille(
            0.9,
            angle
        )

        if not ok:

            continue

    print("Nombre maximum de tentatives atteint")

    recul_urgence()


# ============================================================
# RECENTRAGE
# ============================================================

def recentrer():

    print("Recentrage")

    roues(ANGLE_CENTRE)

    avancer(VITESSE_AVANCE)

    debut = time.time()

    while time.time() - debut < 1.0:

        distance, pattern = lire_etat()

        if collision_imminente(distance):

            stop()
            return

        if bordure_detectee(pattern):

            stop()
            return

        time.sleep(PERIODE_DECISION)

    stop()
# ============================================================
# INITIALISATION
# ============================================================

def initialiser():

    print("=" * 50)
    print("MISSION C - EVITEMENT D'OBSTACLES")
    print("=" * 50)

    roues(ANGLE_CENTRE)
    tete(TETE_CENTRE)

    stop()

    demarrer_threads()

    time.sleep(0.5)

    print("Robot prêt.\n")


# ============================================================
# BOUCLE PRINCIPALE
# ============================================================

def boucle_principale():

    while True:

        distance, pattern = lire_etat()

        print(
            f"[INFO] Distance = {distance:.0f} mm | "
            f"IR = {pattern}"
        )

        # ---------------------------------------
        # Bordure détectée
        # ---------------------------------------

        if bordure_detectee(pattern):

            corriger_bordure(pattern)

            continue

        # ---------------------------------------
        # Obstacle très proche
        # ---------------------------------------

        if collision_imminente(distance):

            recul_urgence()

            continue

        # ---------------------------------------
        # Obstacle détecté
        # ---------------------------------------

        if obstacle_detecte(distance):

            contourner()

            recentrer()

            continue

        # ---------------------------------------
        # Route libre
        # ---------------------------------------

        roues(ANGLE_CENTRE)

        avancer(VITESSE_AVANCE)

        time.sleep(PERIODE_DECISION)


# ============================================================
# FERMETURE
# ============================================================

def fermeture():

    print("\nArrêt du robot...")

    arreter_threads()

    stop()

    roues(ANGLE_CENTRE)
    tete(TETE_CENTRE)

    time.sleep(0.3)

    robot.destroy()

    servos.pca.deinit()

    print("Robot arrêté.")


# ============================================================
# MAIN
# ============================================================

def main():

    try:

        initialiser()

        boucle_principale()

    except KeyboardInterrupt:

        print("\nInterruption utilisateur.")

    finally:

        fermeture()


# ============================================================

if __name__ == "__main__":

    main()
