#!/usr/bin/env python3
import time
from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker

robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()

CENTRE = 97
GAIN_ANGLE = 40.0
SERVO_ALPHA = 0.7
MAX_HOLD = 20          # augmenté
VITESSE_MAX = 34
VITESSE_MIN = 6        # très lent dans les virages serrés
VITESSE_RECH = 8
VITESSE_PERDU = 6

SEUIL_GAUCHE = -0.3
SEUIL_DROITE = 0.3

SEUIL_BALAYAGE = 40
DUREE_PHASE = 60       # plus long pour laisser le temps

angle_actuel = CENTRE
erreur_connue = 0.0
compteur_000 = 0
dernier_sens = 0
compteur_virage = 0    # pour anticiper

def position_depuis_etat(etat):
    g, m, d = etat
    actifs = []
    if g: actifs.append(-1)
    if m: actifs.append(0)
    if d: actifs.append(1)
    if not actifs:
        return None
    return sum(actifs) / len(actifs)

def tourner(cible):
    global angle_actuel
    angle_actuel = angle_actuel * (1 - SERVO_ALPHA) + cible * SERVO_ALPHA
    servos.set_angle(0, round(angle_actuel, 1))

print("START")
tourner(CENTRE)
robot.set_motor(1, 30)
time.sleep(1)

try:
    while True:
        s = tracker.get_status()
        etat = (s["left"], s["middle"], s["right"])
        pos = position_depuis_etat(etat)

        if pos is not None:
            compteur_000 = 0
            erreur_connue = pos

            if pos < SEUIL_GAUCHE:
                dernier_sens = 1
                compteur_virage += 1
            elif pos > SEUIL_DROITE:
                dernier_sens = -1
                compteur_virage += 1
            else:
                compteur_virage = max(0, compteur_virage - 1)

            # Anticipation : si on a eu plusieurs virages consécutifs, on augmente le gain
            gain_effectif = GAIN_ANGLE
            if compteur_virage > 3:
                gain_effectif = GAIN_ANGLE * 1.2

            angle_cible = CENTRE - gain_effectif * pos
            angle_cible = max(50, min(144, angle_cible))

            # Réduction de vitesse en fonction de l'erreur et du compteur de virage
            vitesse = VITESSE_MAX - abs(pos) * 18
            if compteur_virage > 3:
                vitesse = vitesse * 0.7  # ralentit encore plus
            vitesse = max(VITESSE_MIN, min(VITESSE_MAX, vitesse))

        else:
            compteur_000 += 1

            if compteur_000 <= MAX_HOLD:
                angle_cible = CENTRE - GAIN_ANGLE * erreur_connue
                angle_cible = max(50, min(144, angle_cible))
                vitesse = VITESSE_MAX - abs(erreur_connue) * 18
                vitesse = max(VITESSE_MIN, min(VITESSE_MAX, vitesse))
            else:
                if compteur_000 < SEUIL_BALAYAGE:
                    if dernier_sens == 1:
                        angle_cible = 140
                    elif dernier_sens == -1:
                        angle_cible = 54
                    else:
                        angle_cible = CENTRE
                    vitesse = VITESSE_RECH
                else:
                    phase = (compteur_000 - SEUIL_BALAYAGE) // DUREE_PHASE
                    if phase % 2 == 0:
                        angle_cible = 140
                    else:
                        angle_cible = 54
                    vitesse = VITESSE_PERDU

        tourner(angle_cible)
        robot.set_motor(1, int(round(vitesse)))

        if compteur_000 % 10 == 0:
            print(f"{etat}  pos={pos if pos is not None else '---'}  "
                  f"perdu={compteur_000}  angle={round(angle_actuel,1)}  vit={int(vitesse)}")

        time.sleep(0.025)

except KeyboardInterrupt:
    print("\nSTOP")
    robot.stopper()
    servos.set_angle(0, CENTRE)
    robot.destroy()
    servos.fermer()
