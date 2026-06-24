import threading
import time
from motor import RobotMotor
from ultra import Ultrasonic
from lineTracking import LineTracker
from servo import RobotServos

robot = RobotMotor()
ultra = Ultrasonic()
tracker = LineTracker()
servos = RobotServos()

# ==========================
# REGLAGES
# ==========================
ANGLE_CENTRE = 97 

# GAUCHE physique (ajustements adoucis pour la fluidité)
ANGLE_GAUCHE_DOUX = 112    # Pour corriger les petites déviations sans secousse
ANGLE_GAUCHE_LEGER = 125   # Virage standard
ANGLE_GAUCHE_FORT = 145    # Virage très serré

# DROITE physique (ajustements adoucis pour la fluidité)
ANGLE_DROITE_DOUX = 82     # Pour corriger les petites déviations sans secousse
ANGLE_DROITE_LEGER = 75    # Virage standard
ANGLE_DROITE_FORT = 55     # Virage très serré

# VITESSES
VITESSE_DROITE = 30
VITESSE_CORRECTION = 22
VITESSE_VIRAGE = 14        # Un poil plus lent pour stabiliser le robot dans le virage serré
VITESSE_RECHERCHE = 12

DISTANCE_STOP = 200 

# ==========================
# VARIABLES D'ÉTAT
# ==========================
actif = False
angle_actuel = None
dernier_angle = ANGLE_CENTRE
# Mémorise le dernier côté vers lequel le robot a tourné ("gauche" ou "droite")
derniere_direction = "centre" 

# ==========================
# FONCTIONS MOTEURS
# ==========================
def braquer(angle):
    global angle_actuel
    if angle_actuel != angle:
        servos.set_angle(0, angle)
        print("[CH00] →", angle, "°")
        angle_actuel = angle

def avance(angle, vitesse):
    global dernier_angle
    dernier_angle = angle
    braquer(angle)
    robot.set_motor(1, vitesse)

# ==========================
# CLAVIER
# ==========================
def clavier():
    global actif
    while True:
        c = input().strip().upper()
        if c == "M":
            actif = True
            print("START")
        elif c == "A":
            actif = False
            robot.stopper()
            print("STOP")

threading.Thread(target=clavier, daemon=True).start()

# ==========================
# PROGRAMME PRINCIPAL
# ==========================
try:
    while True:
        if not actif:
            time.sleep(0.02)
            continue

        # Obstacle sécurité
        if ultra.get_distance() < DISTANCE_STOP:
            robot.stopper()
            actif = False
            continue

        # Lecture des capteurs
        s = tracker.get_status()
        cap = (s["left"], s["middle"], s["right"])
        print(cap, f" | Dir: {derniere_direction}")

        # =================================================================
        # LOGIQUE DYNAMIQUE POUR LIGNE LARGE (1 = NOIR, 0 = BLANC)
        # =================================================================
        
        # 1. PARFAITEMENT CENTRÉ (Les 3 capteurs sont bien sur la grosse ligne noire)
        if cap == (1, 1, 1):
            avance(ANGLE_CENTRE, VITESSE_DROITE)

        # 2. DÉVIATION OU VIRAGE À GAUCHE 
        # (Le robot part à droite, donc le capteur gauche sort de la ligne et passe sur le blanc)
        elif cap == (0, 1, 1):
            derniere_direction = "gauche"
            avance(ANGLE_GAUCHE_DOUX, VITESSE_CORRECTION) # Correction douce au lieu de brutale
            
        elif cap == (0, 0, 1):
            derniere_direction = "gauche"
            avance(ANGLE_GAUCHE_LEGER, VITESSE_CORRECTION)
            
        elif cap == (0, 0, 0) and derniere_direction == "gauche":
            # Le robot est sorti complètement par la droite du virage serré à gauche
            avance(ANGLE_GAUCHE_FORT, VITESSE_VIRAGE)

        # 3. DÉVIATION OU VIRAGE À DROITE 
        # (Le robot part à gauche, donc le capteur droit sort de la ligne et passe sur le blanc)
        elif cap == (1, 1, 0):
            derniere_direction = "droite"
            avance(ANGLE_DROITE_DOUX, VITESSE_CORRECTION) # Correction douce au lieu de brutale
            
        elif cap == (1, 0, 0):
            derniere_direction = "droite"
            avance(ANGLE_DROITE_LEGER, VITESSE_CORRECTION)
            
        elif cap == (0, 0, 0) and derniere_direction == "droite":
            # Le robot est sorti complètement par la gauche du virage serré à droite
            avance(ANGLE_DROITE_FORT, VITESSE_VIRAGE)

        # 4. CAS DE PERTE INDÉTERMINÉE (Sécurité)
        elif cap == (0, 0, 0):
            # Si on perd la ligne sans historique clair, on avance prudemment en cherchant au centre
            avance(ANGLE_CENTRE, VITESSE_RECHERCHE)

        time.sleep(0.015) # Légèrement plus rapide pour capter les transitions à temps

except KeyboardInterrupt:
    pass
finally:
    robot.stopper()
    braquer(ANGLE_CENTRE)
    print("FIN")
