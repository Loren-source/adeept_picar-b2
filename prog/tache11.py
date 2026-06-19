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

# --- Fonctions de direction ---
angle_actuel = None

def braquer(angle):
    global angle_actuel
    if angle_actuel != angle:
        servos.set_angle(0, angle)
        angle_actuel = angle

def corriger_gauche():
    braquer(84)
    robot.set_motor(1, 30)

def corriger_droite():
    braquer(110)
    robot.set_motor(1, 30)

def corriger_centrer():
    braquer(97)
    robot.set_motor(1, 50)

# --- Thread clavier ---
actif = False

def ecouter_clavier():
    global actif
    while True:
        commande = input()
        if commande == 'M':
            actif = True
            robot.stop_feux()
            robot.set_motor(1, 50)
            print("Démarrage...")
        elif commande == 'A' or commande == 'a':
            actif = False
            robot.stopper()
            print("Arrêt.")

thread_clavier = threading.Thread(target=ecouter_clavier, daemon=True)
thread_clavier.start()

# --- Boucle principale ---
try:
    while True:
        if actif:
            distance = ultra.get_distance()
            if distance < 200:
                robot.stop()
                actif = False
            else:
                capteurs = tracker.get_status()
                l = capteurs['left']
                m = capteurs['middle']
                r = capteurs['right']

                print(f"l={l} m={m} r={r}")  # debug

                if l == 0 and m == 1 and r == 0:
                    corriger_centrer()
                elif l == 1 and m == 1 and r == 1:
                    corriger_centrer()
                elif l == 0 and m == 1 and r == 1:
                    corriger_droite()
                elif l == 1 and m == 1 and r == 0:
                    corriger_gauche()
                elif l == 0 and m == 0 and r == 1:
                    corriger_droite()
                elif l == 1 and m == 0 and r == 0:
                    corriger_gauche()
                elif l == 0 and m == 0 and r == 0:
                    robot.stopper()

        time.sleep(0.05)

except KeyboardInterrupt:
    print('Fin de programme par Ctrl-C')

finally:
    robot.stopper()
    servos.set_angle(0, 97)
    print('Nettoyage final réalisé')
