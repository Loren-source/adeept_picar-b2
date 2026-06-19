import time
import threading
from motor import RobotMotor
from ultra import Ultrasonic
from lineTracking import LineTracker
from servo import RobotServos

# Initialisation des composants
robot = RobotMotor()
ultra = Ultrasonic()
tracker = LineTracker()
servos = RobotServos()

# --- CONFIGURATION TRAJECTOIRE & CORRECTIONS ---
ANGLE_CENTRE = 97
GAIN_P = 15  

# Vitesses progressives
VITESSE_MAX = 52       # Légèrement baissée pour stabiliser le comportement
VITESSE_MIN = 25       
DECELERATION = 2.0     # Freinage plus réactif
ACCELERATION = 1.0     

DISTANCE_STOP = 200    

# --- GESTION DES TIMINGS D'INERTIE ---
DURÉE_INERTIE_VIRAGE = 0.20  # 200ms pour insister dans le virage
DURÉE_INERTIE_DROIT  = 0.50  # 500ms pour les pointillés / coupures

# --- ÉTATS DU SYSTÈME ---
actif = False
angle_actuel = ANGLE_CENTRE
vitesse_actuelle = 0.0

temps_perte_ligne = None
dernière_erreur = 0   

def piloter_robot(angle_cible, vitesse_cible, direction_moteur=1):
    """Gère l'évolution fluide de la vitesse, la direction du moteur et l'angle."""
    global angle_actuel, vitesse_actuelle
    
    # 1. Mise à jour de l'angle
    if angle_actuel != angle_cible:
        servos.set_angle(0, angle_cible)
        angle_actuel = angle_cible
        
    # 2. Rampe de vitesse
    if vitesse_actuelle < vitesse_cible:
        vitesse_actuelle = min(vitesse_cible, vitesse_actuelle + ACCELERATION)
    elif vitesse_actuelle > vitesse_cible:
        vitesse_actuelle = max(vitesse_cible, vitesse_actuelle - DECELERATION)
        
    # 3. Commande moteur (1 = avant, -1 = arrière)
    robot.set_motor(direction_moteur, int(vitesse_actuelle))

def clavier():
    global actif
    while True:
        c = input().strip().upper()
        if c == "M":
            actif = True
            robot.stop_feux()
            print("[INFO] Démarrage du robot")
        elif c == "A":
            actif = False
            robot.stopper()
            print("[INFO] Arrêt du robot")

threading.Thread(target=clavier, daemon=True).start()

print("Prêt. 'M' pour démarrer, 'A' pour arrêter.")

try:
    while True:
        if not actif:
            vitesse_actuelle = 0.0
            time.sleep(0.05)
            continue

        if ultra.get_distance() < DISTANCE_STOP:
            print("[ALERTE] Obstacle détecté !")
            robot.stop()
            actif = False
            continue

        # Lecture des capteurs
        s = tracker.get_status()
        l, m, r = s["left"], s["middle"], s["right"]
        etat_cap = (l, m, r)

        # ─── CALCUL DE L'ERREUR ───
        if etat_cap == (1, 1, 1) or etat_cap == (0, 1, 0):
            erreur = 0
            temps_perte_ligne = None # Reset complet dès qu'on revoit du noir au centre
            
        elif etat_cap == (1, 1, 0): 
            erreur = -1
            temps_perte_ligne = None
            
        elif etat_cap == (1, 0, 0): 
            erreur = -2
            temps_perte_ligne = None
            
        elif etat_cap == (0, 1, 1): 
            erreur = 1
            temps_perte_ligne = None
            
        elif etat_cap == (0, 0, 1): 
            erreur = 2
            temps_perte_ligne = None

        elif etat_cap == (0, 0, 0):
            # ─── STRATÉGIE DE TRAVERSÉE DE ZONE VIDE (0,0,0) ───
            if temps_perte_ligne is None:
                temps_perte_ligne = time.time()
                
            durée_perte = time.time() - temps_perte_ligne
            
            # Détermination du seuil selon l'état précédent
            seuil_tolerance = DURÉE_INERTIE_DROIT if dernière_erreur == 0 else DURÉE_INERTIE_VIRAGE
            
            if durée_perte < seuil_tolerance:
                # Étape A : On continue sur notre lancée (Inertie)
                erreur = dernière_erreur
                angle_cible = ANGLE_CENTRE + (erreur * GAIN_P)
                vitesse_cible = 35 if dernière_erreur == 0 else VITESSE_MIN
                piloter_robot(angle_cible, vitesse_cible, direction_moteur=1)
                time.sleep(0.015)
                continue
            else:
                # Étape B : La tolérance est dépassée, on RECHÈRCHE en marche arrière
                # Pour sortir du piège, on contre-braque légèrement par rapport à l'erreur 
                # qui nous a éjectés de la piste, afin de repositionner le nez du robot.
                if dernière_erreur < 0:
                    angle_cible = ANGLE_CENTRE + 15 # Si on fuyait à gauche, on oriente vers la droite
                elif dernière_erreur > 0:
                    angle_cible = ANGLE_CENTRE - 15 # Si on fuyait à droite, on oriente vers la gauche
                else:
                    angle_cible = ANGLE_CENTRE

                # On applique directement la marche arrière via notre fonction lissée
                piloter_robot(angle_cible, vitesse_cible=22, direction_moteur=-1)
                time.sleep(0.015)
                continue
        else:
            # Sécurité pour les états transitoires bizarres
            erreur = dernière_erreur

        # Mémorisation de la dernière erreur (uniquement hors du tout blanc)
        if etat_cap != (0, 0, 0):
            dernière_erreur = erreur

        # ─── ACTIONNEURS EN SUIVI NORMAL ───
        angle_cible = ANGLE_CENTRE + (erreur * GAIN_P)
        vitesse_cible = VITESSE_MAX - (abs(erreur) * 12)
        vitesse_cible = max(VITESSE_MIN, vitesse_cible)

        piloter_robot(angle_cible, vitesse_cible, direction_moteur=1)

        time.sleep(0.015)

except KeyboardInterrupt:
    pass
finally:
    robot.stopper()
    servos.set_angle(0, ANGLE_CENTRE)
    print("\nProgramme arrêté proprement.")
