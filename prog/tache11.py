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
def braquer(angle):
    servos.set_angle(0, angle)

def corriger_gauche():
    braquer(60)
    robot.set_motor(1, 30)

def corriger_droite():
    braquer(120)
    robot.set_motor(1, 30)

def corriger_centrer():
    braquer(90)
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
            robot.avancer()
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

                if l == 1 and m == 0 and r == 1:
                    corriger_centrer()
                elif l == 1 and m == 1 and r == 0:
                    corriger_droite()
                elif l == 0 and m == 1 and r == 1:
                    corriger_gauche()
                elif l == 0 and m == 0 and r == 0:
                    corriger_centrer()
                elif l == 1 and m == 1 and r == 1:
                    robot.stopper()

except KeyboardInterrupt:
    print('Fin de programme par Ctrl-C')

finally:
    robot.stopper()
    servos.set_angle(0, 90)
    print('Nettoyage final réalisé')
