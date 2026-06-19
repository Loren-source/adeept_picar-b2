import time
import threading
from motor import RobotMotor
from ultra import Ultrasonic
from lineTracking import LineTracker
from servo import RobotServos

robot = RobotMotor()
ultra = Ultrasonic()
tracker = LineTracker()
servos = RobotServos()


ANGLE_CENTRE = 97
ANGLE_GAUCHE_LEGER = 92
ANGLE_GAUCHE_FORT  = 85

ANGLE_DROITE_LEGER = 102
ANGLE_DROITE_FORT  = 110

ANGLE_RECH_GAUCHE = 70
ANGLE_RECH_DROITE = 120

VITESSE_DROITE = 45
VITESSE_CORRECTION = 35
VITESSE_VIRAGE = 25
VITESSE_RECHERCHE = 20

DISTANCE_STOP = 200      # mm

actif = False
etat = "SUIVI"
angle_actuel = None
derniere_direction = "centre"

# permet d'éviter les faux passages en RECHERCHE
compteur_000 = 0

def braquer(angle):
    global angle_actuel
    if angle_actuel != angle:
        servos.set_angle(0, angle)
        angle_actuel = angle
        
def avancer(angle, vitesse):
    braquer(angle)
    robot.set_motor(1, vitesse)
    
def reculer(angle, vitesse):
    braquer(angle)
    robot.set_motor(-1, vitesse)

def ecouter_clavier():
    global actif
    while True:
        cmd = input().strip().upper()
        if cmd == "M":
            actif = True
            robot.stop_feux()
            print("= DEMARRAGE =")
        elif cmd == "A":
            actif = False
            robot.stopper()
            print("== ARRET ==")
threading.Thread(
    target=ecouter_clavier,
    daemon=True
).start()


try:
    while True:
        if not actif:
            time.sleep(0.02)
            continue
        distance = ultra.get_distance()

        if distance < DISTANCE_STOP:
            print("Obstacle détecté")
            robot.stop()
            actif = False
            continue
        capteurs = tracker.get_status()
        l = capteurs["left"]
        m = capteurs["middle"]
        r = capteurs["right"]
        print(f"{l}{m}{r}   Etat={etat}")
        if etat == "RECHERCHE":
            if derniere_direction == "gauche":
                reculer(
                    ANGLE_RECH_GAUCHE,
                    VITESSE_RECHERCHE
                )
            elif derniere_direction == "droite":
                reculer(
                    ANGLE_RECH_DROITE,
                    VITESSE_RECHERCHE
                )
            else:
                reculer(
                    ANGLE_CENTRE,
                    VITESSE_RECHERCHE
                )
            if (l, m, r) == (1,1,1):

                print(">>> Ligne retrouvée")
                robot.stopper()
                braquer(ANGLE_CENTRE)
                time.sleep(0.05)
                etat = "REALIGNEMENT"
            time.sleep(0.02)
            continue

        if etat == "REALIGNEMENT":
            avancer(
                ANGLE_CENTRE,
                25
            )
            time.sleep(0.12)
            etat = "SUIVI"
            continue
        
        if (l,m,r) == (1,1,1):
            compteur_000 = 0
            derniere_direction = "centre"
            avancer(
                ANGLE_CENTRE,
                VITESSE_DROITE
            )
        elif (l,m,r) == (1,1,0):

            compteur_000 = 0

            derniere_direction = "gauche"

            avancer(
                ANGLE_GAUCHE_LEGER,
                VITESSE_CORRECTION
            )

        elif (l,m,r) == (1,0,0):
            compteur_000 = 0
            derniere_direction = "gauche"
            avancer(
                ANGLE_GAUCHE_FORT,
                VITESSE_VIRAGE
            )

        # Robot trop à gauche
        elif (l,m,r) == (0,1,1):
            compteur_000 = 0
            derniere_direction = "droite"
            avancer(
                ANGLE_DROITE_LEGER,
                VITESSE_CORRECTION
            )
        elif (l,m,r) == (0,0,1):
            compteur_000 = 0
            derniere_direction = "droite"
            avancer(
                ANGLE_DROITE_FORT,
                VITESSE_VIRAGE
            )

        # Ligne perdue
        elif (l,m,r) == (0,0,0):
            compteur_000 += 1
            # évite un faux déclenchement
            if compteur_000 >= 2:
                print(">>> Ligne perdue")
                etat = "RECHERCHE"
        else:
            compteur_000 = 0
        time.sleep(0.02)
except KeyboardInterrupt:
    print("Fin du programme")
finally:
    robot.stopper()
    braquer(ANGLE_CENTRE)
    print("Robot arrêté proprement.")
