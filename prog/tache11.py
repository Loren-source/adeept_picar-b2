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
# TES REGLAGES D'ORIGINE
# ==========================
ANGLE_CENTRE = 97 
ANGLE_GAUCHE_LEGER = 125
ANGLE_GAUCHE_FORT = 145 
ANGLE_DROITE_LEGER = 75
ANGLE_DROITE_FORT = 55 

VITESSE_DROITE = 30
VITESSE_CORRECTION = 22
VITESSE_VIRAGE = 15
VITESSE_RECHERCHE = 12
VITESSE_RECUL = 15          # Vitesse de la marche arrière de secours

DISTANCE_STOP = 200 

# ==========================
# VARIABLES D'ÉTAT
# ==========================
actif = False
angle_actuel = None
dernier_angle = ANGLE_CENTRE
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

def recule(angle, vitesse):
    global dernier_angle
    dernier_angle = angle
    braquer(angle)
    robot.set_motor(-1, vitesse)

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

        s = tracker.get_status()
        cap = (s["left"], s["middle"], s["right"])
        print(cap, f" | Dernière dir: {derniere_direction}")

        # =================================================================
        # TA LOGIQUE D'ORIGINE STRICTE (1 = NOIR, 0 = BLANC)
        # =================================================================
        
        if cap == (1, 1, 1):
            avance(ANGLE_CENTRE, VITESSE_DROITE)

        # VIRAGE GAUCHE
        elif cap == (0, 1, 1):
            derniere_direction = "gauche_leger"
            avance(ANGLE_GAUCHE_LEGER, VITESSE_CORRECTION)
            
        elif cap == (0, 0, 1):
            derniere_direction = "gauche_fort"
            avance(ANGLE_GAUCHE_FORT, VITESSE_VIRAGE)

        # VIRAGE DROITE
        elif cap == (1, 1, 0):
            derniere_direction = "droite_leger"
            avance(ANGLE_DROITE_LEGER, VITESSE_CORRECTION)
            
        elif cap == (1, 0, 0):
            derniere_direction = "droite_fort"
            avance(ANGLE_DROITE_FORT, VITESSE_VIRAGE)

        # =================================================================
        # SÉCURITÉ RECUL SUR PERTE DE LIGNE (0, 0, 0)
        # =================================================================
        elif cap == (0, 0, 0):
            ifCompliance = (derniere_direction == "gauche_fort" or derniere_direction == "gauche_leger")
            
            if derniere_direction == "gauche_fort":
                # Perte dans le virage serré à gauche -> On recule roues braquées à gauche
                recule(ANGLE_GAUCHE_FORT, VITESSE_RECUL)
                
            elif derniere_direction == "droite_fort":
                # Perte dans l'épingle à droite -> On recule roues braquées à droite
                recule(ANGLE_DROITE_FORT, VITESSE_RECUL)
                
            elif derniere_direction == "gauche_leger":
                avance(ANGLE_GAUCHE_FORT, VITESSE_RECHERCHE)
                
            elif derniere_direction == "droite_leger":
                avance(ANGLE_DROITE_FORT, VITESSE_RECHERCHE)
                
            else:
                avance(ANGLE_CENTRE, VITESSE_RECHERCHE)

        time.sleep(0.02)

except KeyboardInterrupt:
    pass
finally:
    robot.stopper()
    braquer(ANGLE_CENTRE)
    print("FIN")
