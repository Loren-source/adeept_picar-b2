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

ANGLE_CENTRE=97
ANGLE_GAUCHE_LEGER=92
ANGLE_GAUCHE_FORT=85
ANGLE_DROITE_LEGER=102
ANGLE_DROITE_FORT=110
ANGLE_RECH_GAUCHE=70
ANGLE_RECH_DROITE=120

VITESSE_DROITE=55
VITESSE_CORRECTION=40
VITESSE_VIRAGE=28
VITESSE_RECHERCHE=20
DISTANCE_STOP=200

actif=False
etat="SUIVI"
angle_actuel=None
derniere_direction="centre"

etat_prec=(1,1,1)
virage_confirme=False

def braquer(a):
    global angle_actuel
    if angle_actuel!=a:
        servos.set_angle(0,a)
        angle_actuel=a

def avance(a,v):
    braquer(a)
    robot.set_motor(1,v)

def recule(a,v):
    braquer(a)
    robot.set_motor(-1,v)

def clavier():
    global actif
    while True:
        c=input().strip().upper()
        if c=="M":
            actif=True
            robot.stop_feux()
            print("Demarrage")
        elif c=="A":
            actif=False
            robot.stopper()
            print("Arret")

threading.Thread(target=clavier,daemon=True).start()

try:
    while True:

        if not actif:
            time.sleep(0.02)
            continue

        if ultra.get_distance()<DISTANCE_STOP:
            robot.stop()
            actif=False
            continue

        s=tracker.get_status()
        etat_cap=(s["left"],s["middle"],s["right"])
        l,m,r=etat_cap

        if etat=="RECHERCHE":

            if derniere_direction=="gauche":
                recule(ANGLE_RECH_GAUCHE,VITESSE_RECHERCHE)
            elif derniere_direction=="droite":
                recule(ANGLE_RECH_DROITE,VITESSE_RECHERCHE)
            else:
                recule(ANGLE_CENTRE,VITESSE_RECHERCHE)

            if etat_cap==(1,1,1):
                robot.stopper()
                braquer(ANGLE_CENTRE)
                etat="REALIGNEMENT"

            time.sleep(0.02)
            continue

        if etat=="REALIGNEMENT":
            avance(ANGLE_CENTRE,30)
            time.sleep(0.15)
            etat="SUIVI"
            virage_confirme=False
            etat_prec=(1,1,1)
            continue

        # confirmation des virages
        if etat_prec==(1,1,1):
            if etat_cap in [(1,1,0),(0,1,1)]:
                virage_confirme=False

        elif etat_prec==(1,1,0) and etat_cap==(1,0,0):
            virage_confirme=True

        elif etat_prec==(0,1,1) and etat_cap==(0,0,1):
            virage_confirme=True

        # suivi
        if etat_cap==(1,1,1):
            virage_confirme=False
            derniere_direction="centre"
            avance(ANGLE_CENTRE,VITESSE_DROITE)

        elif etat_cap==(1,1,0):
            derniere_direction="gauche"
            if virage_confirme:
                avance(ANGLE_GAUCHE_LEGER,32)
            else:
                avance(ANGLE_GAUCHE_LEGER,VITESSE_CORRECTION)

        elif etat_cap==(1,0,0):
            derniere_direction="gauche"
            avance(ANGLE_GAUCHE_FORT,VITESSE_VIRAGE)

        elif etat_cap==(0,1,1):
            derniere_direction="droite"
            if virage_confirme:
                avance(ANGLE_DROITE_LEGER,32)
            else:
                avance(ANGLE_DROITE_LEGER,VITESSE_CORRECTION)

        elif etat_cap==(0,0,1):
            derniere_direction="droite"
            avance(ANGLE_DROITE_FORT,VITESSE_VIRAGE)

        elif etat_cap==(0,0,0):
            etat="RECHERCHE"

        etat_prec=etat_cap
        time.sleep(0.02)

except KeyboardInterrupt:
    pass

finally:
    robot.stopper()
    braquer(ANGLE_CENTRE)
