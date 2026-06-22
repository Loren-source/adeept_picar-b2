import time
import threading
from motor import RobotMotor
from ultra import Ultrasonic
from lineTracking import LineTracker
from servo import RobotServos

# --- Initialisation ---
robot   = RobotMotor()
ultra   = Ultrasonic()
tracker = LineTracker()
servos  = RobotServos()

# --- Constantes ---
ANGLE_CENTRE   = 97
ANGLE_LEGER_G  = 88
ANGLE_LEGER_D  = 106
ANGLE_FORT_G   = 75
ANGLE_FORT_D   = 119

VITESSE_BASE    = 35
VITESSE_LEGER   = 30
VITESSE_VIRAGE  = 25
VITESSE_RECH    = 22

DISTANCE_STOP = 200

# --- État ---
actif = False
angle_actuel = None
derniere_direction = "centre"

# --- Fonctions de base ---
def braquer(angle):
    global angle_actuel
    if angle_actuel != angle:
        servos.set_angle(0, angle)
        angle_actuel = angle

def avancer(angle, vitesse):
    braquer(angle)
    robot.set_motor(1, vitesse)

# --- Thread clavier ---
def ecouter_clavier():
    global actif
    while True:
        commande = input().strip().upper()
        if commande == 'M':
            actif = True
            robot.stop_feux()
            print("Démarrage...")
        elif commande == 'A':
            actif = False
            robot.stopper()
            print("Arrêt.")

threading.Thread(target=ecouter_clavier, daemon=True).start()

# --- Boucle principale ---
try:
    while True:
        if not actif:
            time.sleep(0.02)
            continue

        if ultra.get_distance() < DISTANCE_STOP:
            robot.stop()
            actif = False
            continue

        capteurs = tracker.get_status()
        l, m, r = capteurs['left'], capteurs['middle'], capteurs['right']

        if l == 1 and m == 1 and r == 1:
            derniere_direction = "centre"
            avancer(ANGLE_CENTRE, VITESSE_BASE)

        elif l == 1 and m == 1 and r == 0:
            derniere_direction = "gauche"
            avancer(ANGLE_LEGER_G, VITESSE_LEGER)

        elif l == 0 and m == 1 and r == 1:
            derniere_direction = "droite"
            avancer(ANGLE_LEGER_D, VITESSE_LEGER)

        elif l == 1 and m == 0 and r == 0:
            derniere_direction = "gauche"
            avancer(ANGLE_FORT_G, VITESSE_VIRAGE)

        elif l == 0 and m == 0 and r == 1:
            derniere_direction = "droite"
            avancer(ANGLE_FORT_D, VITESSE_VIRAGE)

        elif l == 0 and m == 0 and r == 0:
            # Ligne perdue : continue à chercher en avançant dans la dernière direction
            if derniere_direction == "gauche":
                avancer(ANGLE_FORT_G, VITESSE_RECH)
            elif derniere_direction == "droite":
                avancer(ANGLE_FORT_D, VITESSE_RECH)
            else:
                avancer(ANGLE_CENTRE, VITESSE_RECH)

        time.sleep(0.02)

except KeyboardInterrupt:
    print('Fin de programme par Ctrl-C')

finally:
    robot.stopper()
    servos.set_angle(0, 97)
    print('Nettoyage final réalisé')
