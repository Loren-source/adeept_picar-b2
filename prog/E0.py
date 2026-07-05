#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import threading
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
# CONFIGURATION
# ============================================================
ANGLE_CENTRE = 97
ANGLE_GAUCHE = 135
ANGLE_DROITE = 55
ANGLE_SCAN_GAUCHE = 150
ANGLE_SCAN_CENTRE = 97
ANGLE_SCAN_DROITE = 40

VITESSE_AVANCE = 25
VITESSE_EVITEMENT = 18
VITESSE_RECUL = 14
VITESSE_SORTIE = 22

SEUIL_OBSTACLE = 400          # mm
SEUIL_COLLISION = 180         # mm
SEUIL_PASSAGE_LIBRE = 400     # mm
DISTANCE_MAX_FAUSSE = 2000

DUREE_RECUL_URGENCE = 0.6
DUREE_RECUL_BORDURE = 0.4
DUREE_PAS_EVITEMENT = 1.2
MAX_PAS_EVITEMENT = 8
DUREE_RECENTRAGE = 1.5

PERIODE_ULTRASON = 0.08
PERIODE_IR = 0.03
PERIODE_DECISION = 0.04

ANGLES_SCAN = list(range(-60, 61, 10))

# ============================================================
# THREADS CAPTEURS
# ============================================================
etat_lock = threading.Lock()
etat = {
    "distance": None,
    "pattern": "000",
    "running": True,
}

def thread_ultrason():
    while True:
        with etat_lock:
            if not etat["running"]:
                break
        d = ultrasonic.get_distance()
        with etat_lock:
            etat["distance"] = d
        time.sleep(PERIODE_ULTRASON)

def thread_ir():
    while True:
        with etat_lock:
            if not etat["running"]:
                break
        s = tracker.get_status()
        # Convertir en chaîne "LMR" (0=blanc, 1=noir)
        pattern = f"{s['left']}{s['middle']}{s['right']}"
        with etat_lock:
            etat["pattern"] = pattern
        time.sleep(PERIODE_IR)

def lire_etat():
    with etat_lock:
        return etat["distance"], etat["pattern"]

def arreter_threads():
    with etat_lock:
        etat["running"] = False

# ============================================================
# FONCTIONS DE COMMANDE (adaptées à vos classes)
# ============================================================
def avancer(vitesse):
    servos.set_angle(0, ANGLE_CENTRE)
    robot.set_motor(1, vitesse)

def avancer_braque(angle, vitesse):
    servos.set_angle(0, angle)
    robot.set_motor(1, vitesse)

def reculer(vitesse):
    robot.set_motor(-1, vitesse)

def stop_robot():
    robot.set_motor(1, 0)
    servos.set_angle(0, ANGLE_CENTRE)

def set_head_angle(angle):
    servos.set_angle(1, angle)

def tourner_roues(angle):
    servos.set_angle(0, angle)

# ============================================================
# FONCTIONS DE DÉTECTION
# ============================================================
def obstacle_detecte(distance):
    return distance is not None and distance < SEUIL_OBSTACLE

def collision_imminente(distance):
    return distance is not None and distance < SEUIL_COLLISION

def bordure_detectee(pattern):
    # Retourne True si un capteur latéral voit du noir (1)
    return pattern[0] == '1' or pattern[2] == '1'

# ============================================================
# GESTION DES BORDURES (reste dans la zone)
# ============================================================
def eviter_bordure(pattern):
    print(f"[BORDURE] Detectee : {pattern}")
    stop_robot()
    time.sleep(0.1)

    # Reculer pour se dégager
    reculer(VITESSE_RECUL)
    time.sleep(DUREE_RECUL_BORDURE)
    stop_robot()
    time.sleep(0.2)

    # Corriger la direction en fonction du côté détecté
    if pattern[0] == '1' and pattern[2] == '0':
        # Bord gauche → braquer à droite
        angle = ANGLE_DROITE
        print("[BORDURE] gauche -> correction droite")
    elif pattern[2] == '1' and pattern[0] == '0':
        # Bord droit → braquer à gauche
        angle = ANGLE_GAUCHE
        print("[BORDURE] droite -> correction gauche")
    else:
        # Ambigu (les deux ou autre) → braquer à droite par défaut
        angle = ANGLE_DROITE
        print("[BORDURE] les deux -> correction droite")

    tourner_roues(angle)
    avancer(VITESSE_EVITEMENT)
    time.sleep(0.4)
    stop_robot()
    time.sleep(0.2)

def recul_urgence():
    print("[URGENCE] Collision imminente -> recul")
    stop_robot()
    time.sleep(0.1)
    reculer(VITESSE_RECUL)
    time.sleep(DUREE_RECUL_URGENCE)
    stop_robot()
    time.sleep(0.2)

# ============================================================
# SCAN RADAR
# ============================================================
def scanner_environnement():
    mesures = []
    print("[SCAN] Debut scan")
    stop_robot()
    time.sleep(0.1)

    for angle in ANGLES_SCAN:
        # Vérifier si une bordure est détectée pendant le scan (sécurité)
        _, pattern = lire_etat()
        if bordure_detectee(pattern):
            print("[SCAN] Bordure detectee, scan interrompu")
            eviter_bordure(pattern)
            return None

        set_head_angle(angle)
        time.sleep(0.15)
        d = ultrasonic.get_distance()
        if d is None or d <= 0:
            d = DISTANCE_MAX_FAUSSE
        libre = d >= SEUIL_PASSAGE_LIBRE
        mesures.append({"angle": angle, "distance": d, "libre": libre})
        print(f"[SCAN] angle={angle:>4} | distance={d:>5.0f} | libre={libre}")

    set_head_angle(ANGLE_SCAN_CENTRE)
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
    dist_moy = sum(p["distance"] for p in gap) / len(gap)
    angle_centre = gap[len(gap)//2]["angle"]
    penalite = abs(angle_centre) * 20
    penalite_extreme = 800 if abs(angle_centre) >= 50 else 0
    return largeur * 20 + dist_moy - penalite - penalite_extreme

def choisir_meilleur_gap(gaps):
    if not gaps:
        return None
    # Priorité aux gaps centraux (passages entre obstacles)
    centraux = [g for g in gaps if abs(g[len(g)//2]["angle"]) <= 30 and (abs(g[-1]["angle"] - g[0]["angle"]) + 10) >= 20]
    if centraux:
        best = max(centraux, key=score_gap)
        print("[CHOIX] Mode central")
    else:
        best = max(gaps, key=score_gap)
        print("[CHOIX] Mode latéral")
    angle_centre = best[len(best)//2]["angle"]
    print(f"        debut={best[0]['angle']} fin={best[-1]['angle']} centre={angle_centre}")
    return angle_centre

def choisir_direction_par_radar():
    mesures = scanner_environnement()
    if not mesures:
        return None
    gaps = detecter_gaps(mesures)
    if not gaps:
        return None
    return choisir_meilleur_gap(gaps)

def convertir_scan_vers_direction(angle_scan):
    if angle_scan < -10:
        return ANGLE_DROITE      # droite
    elif angle_scan > 10:
        return ANGLE_GAUCHE      # gauche
    else:
        return ANGLE_CENTRE

# ============================================================
# CONTOURNEMENT PAS-À-PAS
# ============================================================
def contourner_obstacle_gap():
    print("[OBSTACLE] Contournement dynamique")
    stop_robot()
    time.sleep(0.1)
    dernier_angle = ANGLE_CENTRE

    for i in range(MAX_PAS_EVITEMENT):
        distance, pattern = lire_etat()

        # 1. Gestion des collisions et des bords (prioritaires)
        if collision_imminente(distance):
            recul_urgence()
            continue
        if bordure_detectee(pattern):
            eviter_bordure(pattern)
            continue

        # 2. Vérifier si l'obstacle est toujours présent
        if not obstacle_detecte(distance):
            print("[OBSTACLE] Obstacle dépassé, on sort")
            # Re-scan après obstacle
            scan_apres_obstacle()
            return

        # 3. Choisir une direction
        angle_scan = choisir_direction_par_radar()
        if angle_scan is None:
            print("[ACTION] Pas de gap, recul")
            recul_urgence()
            continue

        angle_roues = convertir_scan_vers_direction(angle_scan)
        dernier_angle = angle_roues
        print(f"[ACTION] Pas {i+1}/{MAX_PAS_EVITEMENT}: scan={angle_scan} -> roues={angle_roues}")

        # 4. Avancer d'un pas
        tourner_roues(angle_roues)
        avancer(VITESSE_EVITEMENT)
        debut = time.time()
        while time.time() - debut < DUREE_PAS_EVITEMENT:
            d, p = lire_etat()
            # Surveiller les bords pendant le mouvement
            if bordure_detectee(p):
                stop_robot()
                eviter_bordure(p)
                break
            if collision_imminente(d):
                stop_robot()
                recul_urgence()
                break
            time.sleep(PERIODE_DECISION)
        else:
            continue  # pas terminé normalement
        # Si on a break à cause d'une bordure ou collision, on continue la boucle

    # Si trop de tentatives
    print("[SECURITE] Trop de tentatives, recul et recentrage")
    recul_urgence()
    recentrer_apres_evitement(dernier_angle)

# ============================================================
# SCAN APRÈS OBSTACLE
# ============================================================
def scan_apres_obstacle():
    print("[SCAN FINAL] Après obstacle")
    stop_robot()
    time.sleep(0.2)
    angle_scan = choisir_direction_par_radar()
    if angle_scan is not None:
        angle_roues = convertir_scan_vers_direction(angle_scan)
        print(f"[SCAN FINAL] direction={angle_roues}")
        tourner_roues(angle_roues)
    else:
        tourner_roues(ANGLE_CENTRE)
    avancer(VITESSE_SORTIE)
    time.sleep(DUREE_RECENTRAGE)
    stop_robot()
    time.sleep(0.3)

def recentrer_apres_evitement(angle_precedent):
    print("[RECENTRAGE] Contre-braquage")
    if angle_precedent > ANGLE_CENTRE:
        angle_oppose = ANGLE_DROITE
    elif angle_precedent < ANGLE_CENTRE:
        angle_oppose = ANGLE_GAUCHE
    else:
        angle_oppose = ANGLE_DROITE
    tourner_roues(angle_oppose)
    avancer(VITESSE_SORTIE)
    time.sleep(DUREE_RECENTRAGE)
    stop_robot()
    tourner_roues(ANGLE_CENTRE)
    time.sleep(0.3)

# ============================================================
# SUIVI DE LIGNE (pour rester dans la zone) – optionnel
# ============================================================
def avancer_tout_droit():
    tourner_roues(ANGLE_CENTRE)
    avancer(VITESSE_AVANCE)

# ============================================================
# MAIN
# ============================================================
def main():
    print("============================================")
    print("MISSION C - ÉVITEMENT D'OBSTACLES (INSPIRÉ DE VOTRE AMIE)")
    print("Ctrl+C pour arrêter")
    print("============================================")

    # Initialisation
    tourner_roues(ANGLE_CENTRE)
    set_head_angle(ANGLE_SCAN_CENTRE)
    stop_robot()

    # Démarrer les threads
    t_ultra = threading.Thread(target=thread_ultrason, daemon=True)
    t_ir = threading.Thread(target=thread_ir, daemon=True)
    t_ultra.start()
    t_ir.start()
    time.sleep(0.5)

    try:
        while True:
            distance, pattern = lire_etat()
            if distance is not None:
                print(f"[INFO] distance={distance:.0f} mm | pattern={pattern}")
            else:
                print(f"[INFO] distance=None | pattern={pattern}")

            # Priorité absolue : collision
            if collision_imminente(distance):
                recul_urgence()
                continue

            # Bordure (rester dans la zone)
            if bordure_detectee(pattern):
                eviter_bordure(pattern)
                continue

            # Obstacle
            if obstacle_detecte(distance):
                contourner_obstacle_gap()
                continue

            # Sinon, avancer tout droit
            avancer_tout_droit()

            time.sleep(PERIODE_DECISION)

    except KeyboardInterrupt:
        print("\n[FIN] Arrêt utilisateur")

    finally:
        arreter_threads()
        time.sleep(0.2)
        stop_robot()
        tourner_roues(ANGLE_CENTRE)
        set_head_angle(ANGLE_SCAN_CENTRE)
        robot.destroy()
        servos.fermer()
        print("Nettoyage terminé.")

if __name__ == "__main__":
    main()
