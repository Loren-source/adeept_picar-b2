#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import threading
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic
from lineTracking import LineTracker

# ============================
# INITIALISATION
# ============================
robot = RobotMotor()
servos = RobotServos()
ultrasonic = Ultrasonic()
tracker = LineTracker()

# ============================
# CONSTANTES (ajustées)
# ============================
CENTRE = 97
ANGLE_VIRAGE = 35
ANGLE_EVITEMENT = 40
ANGLE_TETE_CENTRE = 90
ANGLE_TETE_GAUCHE = 0
ANGLE_TETE_DROITE = 180

VITESSE_LIGNE = 15
VITESSE_VIRAGE = 15
VITESSE_EVITEMENT = 18          # vitesse pendant les 5 secondes
VITESSE_RECUL = 12
VITESSE_RECHERCHE = 15

SEUIL_OBSTACLE = 700            # mm
SEUIL_COLLISION = 300           # mm
SEUIL_RECUL_FORT = 180          # mm
SEUIL_PASSAGE_LIBRE = 600       # mm
DISTANCE_MAX_FAUSSE = 2000

DUREE_RECUL_URGENCE = 0.4
DUREE_RECUL_BORDURE = 0.5
DUREE_PAS_EVITEMENT = 5.0       # <--- 5 secondes entre chaque scan
MAX_PAS_EVITEMENT = 8           # nombre de pas max
DUREE_RECENTRAGE = 1.5

PERIODE_BOUCLE = 0.04
PERIODE_ULTRASON = 0.1
PERIODE_IR = 0.04

ANGLES_SCAN = list(range(-60, 61, 10))

# ============================
# ÉTAT PARTAGÉ
# ============================
etat_lock = threading.Lock()
etat = {
    "distance": None,
    "pattern": (0,0,0),
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
        p = (s["left"], s["middle"], s["right"])
        with etat_lock:
            etat["pattern"] = p
        time.sleep(PERIODE_IR)

def lire_etat():
    with etat_lock:
        return etat["distance"], etat["pattern"]

def arreter_threads():
    with etat_lock:
        etat["running"] = False

# ============================
# FONCTIONS DE COMMANDE
# ============================
def avancer(vitesse):
    robot.set_motor(1, vitesse)

def reculer(vitesse):
    robot.set_motor(-1, vitesse)

def stop_robot():
    robot.set_motor(1, 0)

def tourner_roues(angle):
    servos.set_angle(0, angle)

def tourner_tete(angle):
    servos.set_angle(1, angle)

def roues_droites():
    tourner_roues(CENTRE)

def braquer_gauche(angle=ANGLE_VIRAGE):
    tourner_roues(CENTRE + angle)

def braquer_droite(angle=ANGLE_VIRAGE):
    tourner_roues(CENTRE - angle)

# ============================
# DÉTECTIONS
# ============================
def obstacle_detecte(distance):
    return distance is not None and distance < SEUIL_OBSTACLE

def collision_imminente(distance):
    return distance is not None and distance < SEUIL_COLLISION

def recul_fort_necessaire(distance):
    return distance is not None and distance < SEUIL_RECUL_FORT

def approche_lente_necessaire(distance):
    return distance is not None and SEUIL_COLLISION <= distance < SEUIL_OBSTACLE

# ============================
# RÉACTIONS D'URGENCE
# ============================
def recul_urgence():
    print("[URGENCE] Recule léger")
    stop_robot()
    time.sleep(0.1)
    roues_droites()
    reculer(VITESSE_RECUL)
    time.sleep(DUREE_RECUL_URGENCE)
    stop_robot()
    time.sleep(0.2)

def eviter_bordure(pattern):
    print(f"[BORDURE] Detectee : {pattern}")
    stop_robot()
    time.sleep(0.1)
    reculer(VITESSE_RECUL)
    time.sleep(DUREE_RECUL_BORDURE)
    stop_robot()
    time.sleep(0.2)

    if pattern[0] == 1 and pattern[2] == 0:
        braquer_droite(ANGLE_EVITEMENT)
        print("[BORDURE] gauche -> correction droite")
    elif pattern[2] == 1 and pattern[0] == 0:
        braquer_gauche(ANGLE_EVITEMENT)
        print("[BORDURE] droite -> correction gauche")
    else:
        braquer_droite(ANGLE_EVITEMENT)
        print("[BORDURE] les deux -> correction droite")

    avancer(VITESSE_RECHERCHE)
    time.sleep(0.5)
    stop_robot()
    roues_droites()

# ============================
# SCAN RADAR
# ============================
def scanner_environnement():
    mesures = []
    print("[SCAN] Debut scan")
    stop_robot()
    time.sleep(0.2)
    tourner_tete(ANGLE_TETE_CENTRE)
    time.sleep(0.2)

    for angle_rel in ANGLES_SCAN:
        angle_abs = ANGLE_TETE_CENTRE + angle_rel
        tourner_tete(angle_abs)
        time.sleep(0.2)
        d = ultrasonic.get_distance()
        if d is None or d > DISTANCE_MAX_FAUSSE:
            d = DISTANCE_MAX_FAUSSE
        libre = d >= SEUIL_PASSAGE_LIBRE
        mesures.append({"angle": angle_rel, "distance": d, "libre": libre})
        print(f"[SCAN] angle={angle_rel:>4} | distance={d:>5.0f} | libre={libre}")

    tourner_tete(ANGLE_TETE_CENTRE)
    time.sleep(0.2)
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
    centraux = [g for g in gaps if abs(g[len(g)//2]["angle"]) <= 30 and (abs(g[-1]["angle"] - g[0]["angle"]) + 10) >= 20]
    if centraux:
        best = max(centraux, key=score_gap)
    else:
        best = max(gaps, key=score_gap)
    angle_centre = best[len(best)//2]["angle"]
    print(f"[CHOIX] Gap: {best[0]['angle']} -> {best[-1]['angle']}, centre={angle_centre}")
    return angle_centre

def choisir_direction_par_radar():
    mesures = scanner_environnement()
    if not mesures:
        return None
    gaps = detecter_gaps(mesures)
    if not gaps:
        return None
    return choisir_meilleur_gap(gaps)

# ============================
# MOUVEMENT PAS-À-PAS (5 secondes)
# ============================
def avancer_un_pas(duree, vitesse, angle_roues):
    """
    Avance pendant 'duree' secondes avec l'angle donné,
    tout en surveillant les bords.
    Retourne True si le mouvement s'est bien passé.
    """
    debut = time.time()
    tourner_roues(angle_roues)
    avancer(vitesse)
    while time.time() - debut < duree:
        dist, pat = lire_etat()
        # Surveillance des bords (prioritaire)
        if pat[0] == 1 and pat[2] == 0:
            stop_robot()
            eviter_bordure(pat)
            return False
        if pat[2] == 1 and pat[0] == 0:
            stop_robot()
            eviter_bordure(pat)
            return False
        # Pas de vérification de collision pour avancer en confiance
        time.sleep(PERIODE_BOUCLE)
    return True

def recentrer_apres_evitement(angle_precedent):
    print("[RECENTRAGE] Contre-braquage")
    angle_oppose = - (angle_precedent - CENTRE) if angle_precedent != CENTRE else 0
    if angle_oppose == 0:
        angle_oppose = -ANGLE_EVITEMENT
    tourner_roues(CENTRE + angle_oppose)
    avancer(VITESSE_RECHERCHE)
    time.sleep(DUREE_RECENTRAGE)
    stop_robot()
    roues_droites()
    time.sleep(0.5)

# ============================
# CONTOURNEMENT PAR PAS SUCCESSIFS (5 secondes par pas)
# ============================
def contourner_obstacle_gap():
    print("[OBSTACLE] Contournement dynamique (pas-à-pas de 5s avec re-scan)")
    stop_robot()
    time.sleep(0.2)
    dernier_angle_roues = CENTRE
    pas = 0

    while pas < MAX_PAS_EVITEMENT:
        dist, pat = lire_etat()

        # Sécurité : si on est vraiment trop proche, on recule
        if recul_fort_necessaire(dist):
            recul_urgence()
            # Après recul, on re-scanne
            continue

        # Si l'obstacle n'est plus détecté, on sort
        if not obstacle_detecte(dist):
            print("[OBSTACLE] Plus d'obstacle devant -> recentrage")
            recentrer_apres_evitement(dernier_angle_roues)
            return

        # 1. Scanner pour choisir la direction
        angle_scan = choisir_direction_par_radar()
        if angle_scan is None:
            print("[ACTION] Pas de gap détecté -> recul léger")
            recul_urgence()
            continue

        # 2. Convertir en angle de braquage
        if angle_scan < -10:
            angle_roues = CENTRE - ANGLE_EVITEMENT
        elif angle_scan > 10:
            angle_roues = CENTRE + ANGLE_EVITEMENT
        else:
            angle_roues = CENTRE

        dernier_angle_roues = angle_roues
        print(f"[ACTION] Pas {pas+1}/{MAX_PAS_EVITEMENT}: scan={angle_scan} -> roues={angle_roues}")

        # 3. Avancer pendant 5 secondes
        ok = avancer_un_pas(DUREE_PAS_EVITEMENT, VITESSE_EVITEMENT, angle_roues)
        if not ok:
            # Si on a touché une bordure, on ne compte pas ce pas comme un échec,
            # on continue la boucle (le prochain scan ajustera)
            print("[BORDURE] Ajustement effectué, on re-scanne")
            continue

        pas += 1

    # Si on a atteint le nombre max de pas sans dépasser l'obstacle
    print("[SECURITE] Trop de pas sans succès -> recul long")
    recul_urgence()
    recentrer_apres_evitement(dernier_angle_roues)

# ============================
# SUIVI DE LIGNE AVEC IR
# ============================
def suivre_ligne():
    _, pattern = lire_etat()
    g, m, d = pattern
    print(f"[SUIVI] pattern={pattern}")

    if g == 1 and m == 1 and d == 1:
        roues_droites()
        avancer(VITESSE_LIGNE)
    elif g == 0 and m == 1 and d == 0:
        roues_droites()
        avancer(VITESSE_LIGNE)
    elif g == 0 and m == 0 and d == 1:
        braquer_droite(ANGLE_VIRAGE//2)
        avancer(VITESSE_VIRAGE)
    elif g == 1 and m == 0 and d == 0:
        braquer_gauche(ANGLE_VIRAGE//2)
        avancer(VITESSE_VIRAGE)
    elif g == 0 and m == 1 and d == 1:
        braquer_droite(ANGLE_VIRAGE)
        avancer(VITESSE_VIRAGE)
    elif g == 1 and m == 1 and d == 0:
        braquer_gauche(ANGLE_VIRAGE)
        avancer(VITESSE_VIRAGE)
    else:
        roues_droites()
        avancer(VITESSE_RECHERCHE)

# ============================
# BOUCLE PRINCIPALE
# ============================
def main():
    print("=== Mission : Suivi de ligne + Évitement d'obstacle (pas de 5s) ===")
    print("Appuyez sur Ctrl+C pour arrêter.")

    roues_droites()
    tourner_tete(ANGLE_TETE_CENTRE)
    stop_robot()

    t_ultra = threading.Thread(target=thread_ultrason, daemon=True)
    t_ir = threading.Thread(target=thread_ir, daemon=True)
    t_ultra.start()
    t_ir.start()
    time.sleep(0.5)

    try:
        while True:
            dist, pattern = lire_etat()
            print(f"[INFO] dist={dist if dist is not None else 'None'} mm, pattern={pattern}")

            # 1. Urgence : recul si vraiment trop proche
            if recul_fort_necessaire(dist):
                recul_urgence()
                continue

            # 2. Ralentissement progressif à l'approche
            if approche_lente_necessaire(dist):
                avancer(VITESSE_RECHERCHE)
                suivre_ligne()
                # On ne déclenche pas encore l'évitement, on continue le suivi

            # 3. Obstacle détecté -> contournement
            if obstacle_detecte(dist):
                contourner_obstacle_gap()
                continue

            # 4. Sinon, suivi de ligne normal
            suivre_ligne()

            time.sleep(PERIODE_BOUCLE)

    except KeyboardInterrupt:
        print("\n[FIN] Arrêt utilisateur")

    finally:
        arreter_threads()
        time.sleep(0.2)
        stop_robot()
        roues_droites()
        tourner_tete(ANGLE_TETE_CENTRE)
        robot.destroy()
        servos.fermer()
        print("Nettoyage terminé.")

if __name__ == "__main__":
    main()
