import threading
import time # Assure-toi que l'import de time est bien présent
from motor import RobotMotor
from ultra import Ultrasonic  # Changé ultra en Ultra si ton fichier s'appelle Ultra.py
from line import LineTracker   # Ajusté selon le nom de ton fichier line.py
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

# VITESSES OPTIMISÉES
VITESSE_DROITE = 25       # Légèrement réduit pour éviter de se faire éjecter par l'inertie
VITESSE_CORRECTION = 18
VITESSE_VIRAGE = 12       # Très lent pour les virages serrés pour donner du temps aux servos
VITESSE_PIVOT_ARRIERE = 15 # Vitesse de recul pour se repositionner

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
    robot.set_motor(-1, vitesse) # Utilise la direction -1 de ton motor.py

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

        # Obstacle
        if ultra.get_distance() < DISTANCE_STOP:
            robot.stopper()
            actif = False
            continue

        s = tracker.get_status()
        cap = (s["left"], s["middle"], s["right"])
        print(cap, f" | Dernière dir: {derniere_direction}")

        # =====================
        # TOUT DROIT
        # =====================
        if cap == (1, 1, 1):
            # Optionnel : si le robot voit tout noir, il va droit et on ne change pas la dernière direction
            avance(ANGLE_CENTRE, VITESSE_DROITE)

        elif cap == (0, 1, 0):
            # Ligne parfaitement centrée
            avance(ANGLE_CENTRE, VITESSE_DROITE)

        # =====================
        # VIRAGE GAUCHE
        # =====================
        elif cap == (0, 1, 1) or cap == (1, 1, 0): 
            # Note : Attention à la logique de tes capteurs (0=noir ou 1=noir ?)
            # Si cap=(0,1,1) signifie que le capteur gauche est sorti du noir :
            derniere_direction = "gauche"
            avance(ANGLE_GAUCHE_LEGER, VITESSE_CORRECTION)

        elif cap == (0, 0, 1):
            # Virage prononcé à gauche
            derniere_direction = "gauche"
            avance(ANGLE_GAUCHE_FORT, VITESSE_VIRAGE)

        # =====================
        # VIRAGE DROITE
        # =====================
        elif cap == (1, 1, 0) or cap == (0, 1, 1):
            derniere_direction = "droite"
            avance(ANGLE_DROITE_LEGER, VITESSE_CORRECTION)

        elif cap == (1, 0, 0):
            # Virage prononcé à droite
            derniere_direction = "droite"
            avance(ANGLE_DROITE_FORT, VITESSE_VIRAGE)

        # =====================
        # PERTE DE LIGNE (0, 0, 0) -> LE RECOURS AGRESSIF
        # =====================
        elif cap == (0, 0, 0):
            print(f"[ATTENTION] Ligne perdue ! Manœuvre de secours vers : {derniere_direction}")
            
            if derniere_direction == "gauche":
                # On braque à fond à GAUCHE et on RECOULE pour remettre l'avant sur la ligne
                recule(ANGLE_GAUCHE_FORT, VITESSE_PIVOT_ARRIERE)
                
            elif derniere_direction == "droite":
                # On braque à fond à DROITE et on RECOULE
                recule(ANGLE_DROITE_FORT, VITESSE_PIVOT_ARRIERE)
                
            else:
                # Si on ne sait pas, on recule tout droit lentement
                recule(ANGLE_CENTRE, VITESSE_PIVOT_ARRIERE)

        time.sleep(0.01) # Légèrement plus rapide pour augmenter la réactivité

except KeyboardInterrupt:
    pass
finally:
    robot.stopper()
    braquer(ANGLE_CENTRE)
    print("FIN")
