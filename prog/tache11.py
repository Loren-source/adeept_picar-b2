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
VITESSE_MAX = 55       
VITESSE_MIN = 25       
DECELERATION = 1.5     
ACCELERATION = 1.0     

DISTANCE_STOP = 200    

# --- GESTION DES TIMINGS D'INERTIE (LIGNE PERDUE) ---
DURÉE_INERTIE_VIRAGE = 0.18  # 180ms pour insister dans un virage avant de reculer
DURÉE_INERTIE_DROIT  = 0.50  # 500ms pour traverser les coupures en ligne droite !

# --- ÉTATS DU SYSTÈME ---
actif = False
angle_actuel = ANGLE_CENTRE
vitesse_actuelle = 0.0

temps_perte_ligne = None
dernière_erreur = 0   

def piloter_robot(angle_cible, vitesse_cible):
    """Gère l'évolution fluide (lissage) de la vitesse et applique l'angle."""
    global angle_actuel, vitesse_actuelle
    
    if angle_actuel != angle_cible:
        servos.set_angle(0, angle_cible)
        angle_actuel = angle_cible
        
    if vitesse_actuelle < vitesse_cible:
        vitesse_actuelle = min(vitesse_cible, vitesse_actuelle + ACCELERATION)
    elif vitesse_actuelle > vitesse_cible:
        vitesse_actuelle = max(vitesse_cible, vitesse_actuelle - DECELERATION)
        
    robot.set_motor(1, int(vitesse_actuelle))

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

        # ─── CALCUL DE L'ERREUR POUR LE CONTRÔLEUR ───
        if etat_cap == (1, 1, 1):
            erreur = 0
            temps_perte_ligne = None 
            
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
            
            # Choix du seuil de tolérance selon ce qu'on faisait avant de perdre la ligne
            if dernière_erreur == 0:
                seuil_tolerance = DURÉE_INERTIE_DROIT
            else:
                seuil_tolerance = DURÉE_INERTIE_VIRAGE
            
            if durée_perte < seuil_tolerance:
                # On maintient le cap précédent (si dernière_erreur était 0, il reste à 0 et va tout droit)
                erreur = dernière_erreur
            else:
                # VRAIE PERTE : Le délai max est dépassé, on lance la recherche en arrière
                print("[RECHERCHE] Ligne perdue (délai dépassé), marche arrière...")
                if dernière_erreur < 0:
                    servos.set_angle(0, ANGLE_CENTRE - 15) 
                elif dernière_erreur > 0:
                    servos.set_angle(0, ANGLE_CENTRE + 15)
                else:
                    servos.set_angle(0, ANGLE_CENTRE)
                robot.set_motor(-1, 20)
                continue 
        else:
            # Cas (0, 1, 0) : ligne fine bien centrée
            erreur = 0
            temps_perte_ligne = None

        # Mémorisation du dernier état connu (uniquement s'il est stable)
        if etat_cap != (0, 0, 0):
            dernière_erreur = erreur

        # ─── ACTIONNEURS ───
        angle_cible = ANGLE_CENTRE + (erreur * GAIN_P)
        
        # En ligne droite (erreur = 0), on bombarde. En virage ou en coupure, on adapte.
        if etat_cap == (0, 0, 0) and dernière_erreur == 0:
            # Si on est dans un blanc des pointillés, on maintient une vitesse stable (ex: 40) 
            # pour ne pas surprendre les moteurs, au lieu d'accélérer à fond.
            vitesse_cible = 40 
        else:
            vitesse_cible = VITESSE_MAX - (abs(erreur) * 12)
            vitesse_cible = max(VITESSE_MIN, vitesse_cible)

        piloter_robot(angle_cible, vitesse_cible)

        time.sleep(0.015)

except KeyboardInterrupt:
    pass
finally:
    robot.stopper()
    servos.set_angle(0, ANGLE_CENTRE)
    print("\nProgramme arrêté proprement.")
