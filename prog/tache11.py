import threading
import time
from motor import RobotMotor
from ultra import Ultrasonic
from lineTracking import LineTracker # Remis exactement ton import d'origine
from servo import RobotServos

robot = RobotMotor()
ultra = Ultrasonic()
tracker = LineTracker()
servos = RobotServos()

# ==========================
# REGLAGES
# ==========================
ANGLE_CENTRE = 97 
# GAUCHE physique
ANGLE_GAUCHE_LEGER = 125
ANGLE_GAUCHE_FORT = 145 
# DROITE physique
ANGLE_DROITE_LEGER = 75
ANGLE_DROITE_FORT = 55 

VITESSE_DROITE = 30
VITESSE_CORRECTION = 22
VITESSE_VIRAGE = 15
VITESSE_RECHERCHE = 12
VITESSE_PIVOT_ARRIERE = 15 # Vitesse de secours pour reculer dans l'épingle
DISTANCE_STOP = 200 

# ==========================
# VARIABLES
# ==========================
actif = False
angle_actuel = None
dernier_angle = ANGLE_CENTRE
derniere_direction = "centre" 

# ==========================
# MOTEURS
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
    robot.set_motor(-1, vitesse) # Commande le pont en H en marche arrière

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

        # obstacle
        if ultra.get_distance() < DISTANCE_STOP:
            robot.stopper()
            actif = False
            continue

        s = tracker.get_status()
        cap = (s["left"], s["middle"], s["right"])
        print(cap)

        # =====================
        # TOUT DROIT
        # =====================
        if cap == (1, 1, 1):
            avance(ANGLE_CENTRE, VITESSE_DROITE)

        # =====================
        # VIRAGE GAUCHE (Tes conditions d'origine)
        # =====================
        elif cap == (0, 1, 1):
            derniere_direction = "gauche_leger"
            avance(ANGLE_GAUCHE_LEGER, VITESSE_CORRECTION)
            
        elif cap == (0, 0, 1):
            derniere_direction = "gauche_fort"
            avance(ANGLE_GAUCHE_FORT, VITESSE_VIRAGE)

        # =====================
        # VIRAGE DROITE (Tes conditions d'origine)
        # =====================
        elif cap == (1, 1, 0):
            derniere_direction = "droite_leger"
            avance(ANGLE_DROITE_LEGER, VITESSE_CORRECTION)
            
        elif cap == (1, 0, 0):
            derniere_direction = "droite_fort"
            avance(ANGLE_DROITE_FORT, VITESSE_VIRAGE)

        # =====================
        # PERTE DE LIGNE INTELLIGENTE
        # =====================
        elif cap == (0, 0, 0):
            # Cas 1 : On a perdu la ligne alors qu'on tournait déjà FERMEMENT à droite (Virage serré numéro 2)
            if Lab_direction == "droite_fort":
                print("[INFO] Épingle manquée à droite ! Recul de secours.")
                recule(ANGLE_DROITE_FORT, VITESSE_PIVOT_ARRIERE)
                
            # Cas 2 : On a perdu la ligne alors qu'on tournait déjà FERMEMENT à gauche
            elif Lab_direction == "gauche_fort":
                print("[INFO] Épingle manquée à gauche ! Recul de secours.")
                recule(ANGLE_GAUCHE_FORT, VITESSE_PIVOT_ARRIERE)
                
            # Cas 3 : Perte classique sur virage léger (ton comportement d'origine qui fonctionnait)
            elif Lab_direction == "gauche_leger":
                avance(ANGLE_GAUCHE_FORT, VITESSE_RECHERCHE)
                
            elif Lab_direction == "droite_leger":
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
