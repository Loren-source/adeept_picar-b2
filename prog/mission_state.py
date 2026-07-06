#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import threading
import sys

# ============================================================
# MISSION A : Suivi de ligne IR (adapté de Suivi-ligne.py)
# ============================================================
def run_mission_ir(res, panel_name="travaux"):
    """
    Suivi de ligne par capteurs IR.
    Sortie : détection du panneau 'travaux' (transition A → C)
    """
    print("[MISSION A] Démarrage suivi IR.")
    robot = res.motor
    servos = res.servos
    tracker = res.tracker

    # --- Paramètres exacts de Suivi-ligne.py ---
    CENTRE = 97
    GAUCHE_LEGER = 115
    DROITE_LEGER = 82
    GAUCHE_FORT = 128
    DROITE_FORT = 65
    VITESSE_LIGNE = 45
    VITESSE_VIRAGE = 22
    VITESSE_PERDU = 19
    VITESSE_POINTILLE = 38
    SEUIL_POINTILLE = 50
    SEUIL_PERDU_MAX = 150
    SEUIL_ANGLE_DROIT = 12

    angle_actuel = CENTRE
    dernier_sens = 0
    compteur_virage = 0
    dernier_etat = (1, 1, 1)
    compteur_pointille = 0
    compteur_perdu = 0
    derniere_cible = CENTRE
    derniere_vitesse = VITESSE_LIGNE

    def tourner(cible):
        nonlocal angle_actuel
        if cible == CENTRE:
            angle_actuel = angle_actuel * 0.3 + cible * 0.7
        else:
            angle_actuel = angle_actuel * 0.6 + cible * 0.4
        servos.set_angle(0, round(angle_actuel, 1))

    # --- Initialisation ---
    servos.set_angle(0, CENTRE)
    robot.set_motor(1, 30)
    time.sleep(1)

    try:
        while True:
            # --- VÉRIFICATION DU PANNEAU DE TRANSITION A→C ---
            frame = res.capture_frame()
            if frame is not None:
                detected = res.panel_detector.detect(frame, target_name=panel_name)
                if detected == panel_name:
                    print("[MISSION A] 🛑 Panneau 'Travaux' détecté – transition vers C.")
                    robot.set_motor(1, 0)
                    servos.set_angle(0, CENTRE)
                    return "OBSTACLE_AVOID"

            # --- Logique IR originale (copiée depuis Suivi-ligne.py) ---
            s = tracker.get_status()
            etat = (s["left"], s["middle"], s["right"])

            if etat == (1, 1, 1):
                compteur_virage = 0
                compteur_pointille = 0
                compteur_perdu = 0
                cible = CENTRE
                vitesse = VITESSE_LIGNE
                derniere_cible = cible
                derniere_vitesse = vitesse
            elif etat == (1, 1, 0):
                compteur_pointille = 0
                compteur_perdu = 0
                compteur_virage = min(compteur_virage + 1, 5)
                dernier_sens = 1
                cible = GAUCHE_LEGER
                vitesse = 28
                derniere_cible = cible
                derniere_vitesse = vitesse
            elif etat == (1, 0, 0):
                compteur_pointille = 0
                compteur_perdu = 0
                compteur_virage = min(compteur_virage + 1, 5)
                dernier_sens = 1
                if compteur_virage > 3:
                    cible = GAUCHE_FORT
                else:
                    cible = 120
                vitesse = VITESSE_VIRAGE
                derniere_cible = cible
                derniere_vitesse = vitesse
            elif etat == (0, 1, 1):
                compteur_pointille = 0
                compteur_perdu = 0
                compteur_virage = min(compteur_virage + 1, 5)
                dernier_sens = -1
                cible = DROITE_LEGER
                vitesse = 28
                derniere_cible = cible
                derniere_vitesse = vitesse
            elif etat == (0, 0, 1):
                compteur_pointille = 0
                compteur_perdu = 0
                compteur_virage = min(compteur_virage + 1, 5)
                dernier_sens = -1
                if compteur_virage > 3:
                    cible = DROITE_FORT
                else:
                    cible = 75
                vitesse = VITESSE_VIRAGE
                derniere_cible = cible
                derniere_vitesse = vitesse
            elif etat == (0, 0, 0):
                venait_de_virage_serre = dernier_etat in ((1, 0, 0), (0, 0, 1))
                venait_de_ligne_modere = dernier_etat in ((1, 1, 1), (1, 1, 0), (0, 1, 1))

                if venait_de_virage_serre:
                    compteur_perdu += 1
                    if compteur_perdu > SEUIL_PERDU_MAX:
                        print("[MISSION A] Fin de ligne (perte définitive) – passage à C par sécurité.")
                        robot.set_motor(1, 0)
                        servos.set_angle(0, CENTRE)
                        return "OBSTACLE_AVOID"
                    cible = derniere_cible
                    vitesse = VITESSE_PERDU
                elif venait_de_ligne_modere and abs(angle_actuel - CENTRE) < SEUIL_ANGLE_DROIT:
                    compteur_pointille += 1
                    if compteur_pointille <= SEUIL_POINTILLE:
                        if compteur_pointille == 1:
                            cible = derniere_cible
                        elif compteur_pointille == 2:
                            cible = (derniere_cible + CENTRE) / 2
                        else:
                            cible = CENTRE
                        vitesse = VITESSE_POINTILLE
                    else:
                        compteur_perdu += 1
                        if compteur_perdu > SEUIL_PERDU_MAX:
                            print("[MISSION A] Fin de ligne (perte définitive) – passage à C par sécurité.")
                            robot.set_motor(1, 0)
                            servos.set_angle(0, CENTRE)
                            return "OBSTACLE_AVOID"
                        phase = (compteur_perdu - 1) // 30
                        cible = GAUCHE_FORT if phase % 2 == 0 else DROITE_FORT
                        vitesse = VITESSE_PERDU
                else:
                    compteur_perdu += 1
                    if compteur_perdu > SEUIL_PERDU_MAX:
                        print("[MISSION A] Fin de ligne (perte définitive) – passage à C par sécurité.")
                        robot.set_motor(1, 0)
                        servos.set_angle(0, CENTRE)
                        return "OBSTACLE_AVOID"
                    phase = (compteur_perdu - 1) // 30
                    cible = GAUCHE_FORT if phase % 2 == 0 else DROITE_FORT
                    vitesse = VITESSE_PERDU

            tourner(cible)
            robot.set_motor(1, vitesse)
            if etat != (0, 0, 0):
                dernier_etat = etat

            time.sleep(0.025)

    except KeyboardInterrupt:
        print("[MISSION A] Interrompue.")
        robot.set_motor(1, 0)
        servos.set_angle(0, CENTRE)
        return "FINISH"


# ============================================================
# MISSION C : Évitement d'obstacles (adapté de E0.py)
# ============================================================
def run_mission_obstacle(res, panel_name="travaux"):
    """
    Évitement d'obstacles avec ultrason et IR.
    Sortie : détection du panneau 'travaux' (transition C → B)
    """
    print("[MISSION C] Démarrage évitement obstacles.")
    robot = res.motor
    servos = res.servos
    ultrasonic = res.ultrasonic
    tracker = res.tracker

    # --- Paramètres exacts de E0.py ---
    ANGLE_CENTRE = 97
    ANGLE_GAUCHE = 135
    ANGLE_DROITE = 55
    ANGLE_SCAN_GAUCHE = 150
    ANGLE_SCAN_CENTRE = 97
    ANGLE_SCAN_DROITE = 40

    VITESSE_AVANCE = 25
    VITESSE_APPROCHE_18 = 18
    VITESSE_APPROCHE_15 = 15
    VITESSE_APPROCHE_12 = 12
    VITESSE_APPROCHE_8 = 8
    VITESSE_CONTOURNEMENT = 18
    VITESSE_RECUL = 15

    DISTANCE_SCAN = 500          # 50 cm
    DISTANCE_APPROCHE_FIN = 300  # 30 cm
    DISTANCE_SORTIE = 400        # 40 cm
    DISTANCE_CRITIQUE = 150      # 15 cm
    CONFIRMATION_SORTIE = 8
    SEUIL_BLOCAGE = 80
    DISTANCE_FAUSSE = 3000
    ANGLES_SCAN = list(range(-60, 61, 10))

    def avancer(vitesse):
        servos.set_angle(0, ANGLE_CENTRE)
        robot.set_motor(1, vitesse)

    def avancer_braque(angle, vitesse):
        servos.set_angle(0, angle)
        robot.set_motor(1, vitesse)

    def reculer(vitesse):
        robot.set_motor(-1, vitesse)

    def stopper():
        robot.set_motor(1, 0)

    def recentrer():
        servos.set_angle(0, ANGLE_CENTRE)

    def tourner_tete(angle):
        servos.set_angle(1, angle)

    def mesurer_distance():
        try:
            d = ultrasonic.get_distance()
            return d if d > 0 else DISTANCE_FAUSSE
        except:
            return DISTANCE_FAUSSE

    def lire_ir():
        s = tracker.get_status()
        return (s["left"], s["middle"], s["right"])

    def scanner_obstacle():
        mesures = []
        stopper()
        time.sleep(0.1)
        tourner_tete(ANGLE_SCAN_CENTRE)
        time.sleep(0.1)
        for angle in ANGLES_SCAN:
            tourner_tete(ANGLE_SCAN_CENTRE + angle)
            time.sleep(0.15)
            d = mesurer_distance()
            if d is None or d > 3000:
                d = 3000
            libre = d >= DISTANCE_SORTIE
            mesures.append({"angle": angle, "distance": d, "libre": libre})
        tourner_tete(ANGLE_SCAN_CENTRE)
        time.sleep(0.1)

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

        if not gaps:
            return "droite"

        def score_gap(gap):
            largeur = abs(gap[-1]["angle"] - gap[0]["angle"]) + 10
            dist_moy = sum(p["distance"] for p in gap) / len(gap)
            angle_centre = gap[len(gap)//2]["angle"]
            return largeur * 30 + dist_moy - abs(angle_centre) * 15

        meilleur_gap = max(gaps, key=score_gap)
        angle_centre = meilleur_gap[len(meilleur_gap)//2]["angle"]
        if angle_centre < -10:
            return "gauche"
        elif angle_centre > 10:
            return "droite"
        else:
            return "gauche"

    def angle_avec_correction_ir(base_angle, ir):
        if ir[0] == 1 and ir[2] == 0:
            return max(ANGLE_DROITE, base_angle - 10)
        elif ir[2] == 1 and ir[0] == 0:
            return min(ANGLE_GAUCHE, base_angle + 10)
        else:
            return base_angle

    # --- Initialisation ---
    ETAT_AVANCER = 0
    ETAT_SCAN = 1
    ETAT_APPROCHE = 2
    ETAT_CONTOURNER = 3
    ETAT_SCAN_SORTIE = 4
    ETAT_RECENTRER = 5

    etat_robot = ETAT_AVANCER
    direction = "gauche"
    compteur_sortie = 0
    compteur_blocage = 0
    dernier_angle = ANGLE_CENTRE

    servos.set_angle(0, ANGLE_CENTRE)
    tourner_tete(ANGLE_SCAN_CENTRE)
    stopper()
    time.sleep(1)

    try:
        while True:
            # --- VÉRIFICATION DU PANNEAU DE TRANSITION C→B ---
            frame = res.capture_frame()
            if frame is not None:
                detected = res.panel_detector.detect(frame, target_name=panel_name)
                if detected == panel_name:
                    print("[MISSION C] 🛑 Panneau 'Travaux' détecté – transition vers B.")
                    stopper()
                    servos.set_angle(0, ANGLE_CENTRE)
                    tourner_tete(ANGLE_SCAN_CENTRE)
                    return "LINE_CAMERA"

            # --- Logique E0 originale ---
            distance = mesurer_distance()
            ir = lire_ir()

            if etat_robot == ETAT_AVANCER:
                avancer(VITESSE_AVANCE)
                if distance <= DISTANCE_SCAN:
                    stopper()
                    etat_robot = ETAT_SCAN

            elif etat_robot == ETAT_SCAN:
                direction = scanner_obstacle()
                etat_robot = ETAT_APPROCHE

            elif etat_robot == ETAT_APPROCHE:
                base_angle = ANGLE_GAUCHE if direction == "gauche" else ANGLE_DROITE
                angle = angle_avec_correction_ir(base_angle, ir)
                dernier_angle = angle
                if distance > 400:
                    vitesse = VITESSE_APPROCHE_18
                elif distance > 350:
                    vitesse = VITESSE_APPROCHE_15
                elif distance > 300:
                    vitesse = VITESSE_APPROCHE_12
                else:
                    vitesse = VITESSE_APPROCHE_8
                avancer_braque(angle, vitesse)
                if distance <= DISTANCE_APPROCHE_FIN:
                    etat_robot = ETAT_CONTOURNER

            elif etat_robot == ETAT_CONTOURNER:
                base_angle = ANGLE_GAUCHE if direction == "gauche" else ANGLE_DROITE
                angle = angle_avec_correction_ir(base_angle, ir)
                dernier_angle = angle
                avancer_braque(angle, VITESSE_CONTOURNEMENT)

                if distance > DISTANCE_SORTIE and ir == (0, 0, 0):
                    compteur_sortie += 1
                    if compteur_sortie >= CONFIRMATION_SORTIE:
                        stopper()
                        etat_robot = ETAT_SCAN_SORTIE
                        compteur_sortie = 0
                        compteur_blocage = 0
                else:
                    compteur_sortie = 0

                if 250 <= distance <= 300:
                    compteur_blocage += 1
                    if compteur_blocage >= SEUIL_BLOCAGE:
                        stopper()
                        etat_robot = ETAT_SCAN
                        compteur_blocage = 0
                else:
                    compteur_blocage = 0

                if distance < DISTANCE_CRITIQUE:
                    stopper()
                    time.sleep(0.1)
                    reculer(VITESSE_RECUL)
                    time.sleep(0.4)
                    stopper()

            elif etat_robot == ETAT_SCAN_SORTIE:
                direction = scanner_obstacle()
                etat_robot = ETAT_RECENTRER

            elif etat_robot == ETAT_RECENTRER:
                recentrer()
                avancer(VITESSE_AVANCE)
                time.sleep(0.5)
                stopper()
                etat_robot = ETAT_AVANCER

            time.sleep(0.03)

    except KeyboardInterrupt:
        print("[MISSION C] Interrompue.")
        stopper()
        servos.set_angle(0, ANGLE_CENTRE)
        tourner_tete(ANGLE_SCAN_CENTRE)
        return "FINISH"


# ============================================================
# MISSION B : Suivi de ligne rouge par caméra (adapté de ligne rouge.py)
# ============================================================

def run_mission_camera(res, panel_name="tunnel"):
    """
    Suivi de ligne rouge par caméra.
    Lance le thread CVThread et attend la fin (ligne perdue) ou détection du panneau 'tunnel'.
    """
    print("[MISSION B] Démarrage suivi ligne rouge.")

    # On importe le module original et la classe CVThread
    # ATTENTION : nous allons patcher les globaux du module pour utiliser nos ressources partagées.
    import ligne_rouge as lr
    from ligne_rouge import CVThread

    # --- Patch des globaux de ligne_rouge pour utiliser nos ressources ---
    class MotorWrapper:
        @staticmethod
        def video_Tracking_Move(speed, direction):
            # direction : 1=avant, -1=arrière
            res.motor.set_motor(direction, speed)
        @staticmethod
        def motorStop():
            res.motor.set_motor(1, 0)
        @staticmethod
        def destroy():
            pass

    class ServoWrapper:
        def __init__(self, servos):
            self.servos = servos
        def moveAngle(self, servo_id, angle):
            # Le script utilise servo_id=0 pour la direction
            # angle est en degrés relatifs (-30 à +30). On le mappe sur notre échelle (65 à 130)
            if servo_id == 0:
                # MAP : -30 -> 130 (gauche), 0 -> 97 (centre), +30 -> 65 (droite)
                mapped = 97 + (angle * -1.1)  # approximation
                mapped = max(40, min(150, mapped))
                self.servos.set_angle(0, mapped)
        def moveInit(self):
            self.servos.set_angle(0, 97)
        def stopWiggle(self):
            pass

    # On remplace les globaux dans le module importé
    lr.move = MotorWrapper()
    lr.scGear = ServoWrapper(res.servos)

    # Création et démarrage du thread
    cv_thread = CVThread()
    cv_thread.start()

    # Boucle de supervision : on alimente le thread en images et on surveille le panneau
    timeout = 60  # secondes max
    start_time = time.time()

    try:
        while not cv_thread.stopped and (time.time() - start_time) < timeout:
            # 1. Capturer une image et la donner au thread (si disponible)
            frame = res.capture_frame()
            if frame is not None and not cv_thread.threading:
                cv_thread.send_frame(frame.copy())

            # 2. Vérifier le panneau "Tunnel" (transition B→D)
            if frame is not None:
                detected = res.panel_detector.detect(frame, target_name=panel_name)
                if detected == panel_name:
                    print("[MISSION B] 🛑 Panneau 'Tunnel' détecté – transition vers D.")
                    cv_thread.stop()   # demande d'arrêt au thread
                    break

            time.sleep(0.03)

    except Exception as e:
        print(f"[MISSION B] Erreur dans la boucle : {e}")

    # Attente de la fin du thread
    cv_thread.join(timeout=2)

    # Arrêt propre
    res.motor.set_motor(1, 0)
    res.servos.set_angle(0, 97)
    print("[MISSION B] Terminée.")
    return "MAZE_NAV"


# ============================================================
# MISSION D : Labyrinthe (adapté de Obstacle_labyrinthe.py)
# ============================================================

def run_mission_maze(res):
    """
    Navigation dans le labyrinthe avec ultrason et détection de flèches.
    Sortie : compteur de virages atteint (paramétrable) ou panneau de sortie.
    """
    print("[MISSION D] Démarrage labyrinthe.")

    # On importe les fonctions nécessaires depuis le module original
    # Mais on remplace les appels matériels par nos ressources partagées.
    # Pour plus de propreté, on recopie la logique ici, comme pour les autres missions.
    import time
    from arrow_detector import detect_arrow

    robot = res.motor
    servos = res.servos
    ultrasonic = res.ultrasonic

    # --- Constantes exactes de Obstacle_labyrinthe.py ---
    DIST_MIN = 38
    DIST_MAX = 40
    ARROW_TIMEOUT = 5.0
    CAPTURE_INTERVAL = 0.5

    ANGLE_CENTER = 97
    ANGLE_LEFT = 130
    ANGLE_RIGHT = 65

    DRIVE_SPEED = 30
    TURN_SPEED = 35
    BACKUP_SPEED = 20
    BACKUP_TIME = 0.5
    TURN_HOLD = 1.4
    TURN_HOLD_OPPOSITE = 0.6
    STEERING_CANAL = 0

    # Paramètre de sortie du labyrinthe : nombre de virages effectués
    # Ajustez cette valeur selon votre labyrinthe (ex: 4 pour un carré, 6 pour plus complexe)
    MAX_MAZE_TURNS = 6
    virage_count = 0

    def steer(direction):
        if direction == 'left':
            servos.set_angle(STEERING_CANAL, ANGLE_LEFT)
        elif direction == 'right':
            servos.set_angle(STEERING_CANAL, ANGLE_RIGHT)
        else:
            servos.set_angle(STEERING_CANAL, ANGLE_CENTER)

    def turn_with_obstacle_check(direction, duration, duration_opposite, speed, repetitions=2):
        poll_interval = 0.05
        fwd_slice = duration / repetitions
        bwd_slice = duration_opposite / repetitions

        for _ in range(repetitions):
            steer(direction)
            time.sleep(0.3)
            robot.set_motor(1, speed)
            remaining = fwd_slice
            while remaining > 0:
                t0 = time.time()
                time.sleep(min(poll_interval, remaining))
                remaining -= time.time() - t0
            robot.set_motor(1, 0)
            time.sleep(0.3)

            steer('right' if direction == 'left' else 'left')
            time.sleep(0.3)
            robot.set_motor(-1, speed)
            remaining = bwd_slice
            while remaining > 0:
                t0 = time.time()
                time.sleep(min(poll_interval, remaining))
                remaining -= time.time() - t0
            robot.set_motor(1, 0)
            time.sleep(0.2)

    try:
        while True:
            # --- VÉRIFICATION DE SORTIE DU LABYRINTHE ---
            # Option 1 : compteur de virages
            if virage_count >= MAX_MAZE_TURNS:
                print("[MISSION D] 🏁 Nombre de virages atteint – sortie du labyrinthe.")
                robot.set_motor(1, 0)
                steer('forward')
                return "FINISH"

            # Option 2 (future) : détection d'un panneau de sortie
            # frame = res.capture_frame()
            # if frame is not None and res.panel_detector.detect(frame, target_name="sortie"):
            #     return "FINISH"

            # --- Logique labyrinthe originale ---
            steer('forward')
            robot.set_motor(1, DRIVE_SPEED)

            dist = ultrasonic.get_distance() / 10.0
            print(f"[MAZE] Distance: {dist:.1f} cm")

            if dist < DIST_MIN:
                print(f"  Trop près ({dist:.1f} cm) – recul.")
                robot.set_motor(-1, BACKUP_SPEED)
                while ultrasonic.get_distance() / 10.0 < DIST_MIN:
                    time.sleep(0.05)
                robot.set_motor(1, 0)
                continue

            if DIST_MIN <= dist <= DIST_MAX:
                robot.set_motor(1, 0)
                print(f"  Mur à {dist:.1f} cm – lecture flèche...")

                direction = None
                deadline = time.time() + ARROW_TIMEOUT
                while time.time() < deadline:
                    frame = res.capture_frame()
                    if frame is not None:
                        direction = detect_arrow(frame)
                        if direction in ('left', 'right'):
                            print(f"  Flèche détectée : {direction}")
                            break
                    time.sleep(CAPTURE_INTERVAL)

                if direction is None:
                    print("  Pas de flèche – recul.")
                    steer('forward')
                    robot.set_motor(-1, BACKUP_SPEED)
                    time.sleep(BACKUP_TIME)
                    robot.set_motor(1, 0)
                    continue

                print(f"  Virage {direction}...")
                turn_with_obstacle_check(direction, TURN_HOLD, TURN_HOLD_OPPOSITE, TURN_SPEED)
                steer('forward')
                virage_count += 1  # On incrémente le compteur

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("[MISSION D] Interrompue.")
        robot.set_motor(1, 0)
        steer('forward')
        return "FINISH"
