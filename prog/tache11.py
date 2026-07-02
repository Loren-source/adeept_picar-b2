#!/usr/bin/env python3
import time
from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker

# ============================================================
# INSTANCIATION
# ============================================================
robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()

# ============================================================
# PARAMÈTRES
# ============================================================
CENTRE            = 97
SERVO_ALPHA       = 0.7

# Angles (limites physiques)
ANGLE_GAUCHE_MAX  = 170
ANGLE_DROITE_MAX  = 20           # valeur minimale que votre servo peut atteindre

# VITESSES
VITESSE_DROITE    = 34
VITESSE_VIRAGE_GAUCHE = 18
VITESSE_VIRAGE_DROITE = 16       # très lent
VITESSE_PERDU     = 2
VITESSE_RECH      = 2

# LISSAGE
VITESSE_ALPHA     = 0.3

# Gestion des pertes
MAX_HOLD          = 60
MAINTIEN_AVANT_BALAYAGE = 100
DUREE_RECHERCHE   = 300

# ============================================================
# VARIABLES D'ÉTAT
# ============================================================
angle_actuel      = CENTRE
erreur_connue     = 0.0
compteur_000      = 0
dernier_sens      = 0
vitesse_actuelle  = VITESSE_DROITE
dernier_etat_non_nul = (1,1,1)

# ============================================================
# FONCTIONS
# ============================================================
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

def angle_cible_depuis_etat(etat):
    # Anticipation : dès qu'on voit (0,1,1) on braque à fond à droite
    if etat == (0,1,1) or etat == (0,0,1):
        return ANGLE_DROITE_MAX
    elif etat == (1,1,0) or etat == (1,0,0):
        return ANGLE_GAUCHE_MAX
    else:
        return CENTRE

# ============================================================
# DÉMARRAGE
# ============================================================
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
            dernier_etat_non_nul = etat

            if etat in [(1,1,0), (1,0,0)]:
                dernier_sens = 1
            elif etat in [(0,1,1), (0,0,1)]:
                dernier_sens = -1

            angle_cible = angle_cible_depuis_etat(etat)

            # Vitesse : très lente pour les virages à droite
            if etat in [(1,1,0), (1,0,0)]:
                vitesse_target = VITESSE_VIRAGE_GAUCHE
            elif etat in [(0,1,1), (0,0,1)]:
                vitesse_target = VITESSE_VIRAGE_DROITE
            else:
                vitesse_target = VITESSE_DROITE

        else:
            compteur_000 += 1

            if compteur_000 <= MAX_HOLD:
                angle_cible = angle_cible_depuis_etat(dernier_etat_non_nul)
                if dernier_etat_non_nul in [(1,1,0), (1,0,0)]:
                    vitesse_target = VITESSE_VIRAGE_GAUCHE
                elif dernier_etat_non_nul in [(0,1,1), (0,0,1)]:
                    vitesse_target = VITESSE_VIRAGE_DROITE
                else:
                    vitesse_target = VITESSE_DROITE
            else:
                if compteur_000 - MAX_HOLD <= MAINTIEN_AVANT_BALAYAGE:
                    if dernier_sens == 1:
                        angle_cible = ANGLE_GAUCHE_MAX
                    elif dernier_sens == -1:
                        angle_cible = ANGLE_DROITE_MAX
                    else:
                        angle_cible = CENTRE
                    vitesse_target = VITESSE_RECH
                else:
                    phase = (compteur_000 - MAX_HOLD - MAINTIEN_AVANT_BALAYAGE) // DUREE_RECHERCHE
                    if phase % 2 == 0:
                        if dernier_sens == 1:
                            angle_cible = ANGLE_GAUCHE_MAX
                        elif dernier_sens == -1:
                            angle_cible = ANGLE_DROITE_MAX
                        else:
                            angle_cible = CENTRE
                    else:
                        if dernier_sens == 1:
                            angle_cible = ANGLE_DROITE_MAX
                        elif dernier_sens == -1:
                            angle_cible = ANGLE_GAUCHE_MAX
                        else:
                            angle_cible = CENTRE
                    vitesse_target = VITESSE_PERDU

        # Lissage vitesse
        vitesse_actuelle = vitesse_actuelle * (1 - VITESSE_ALPHA) + vitesse_target * VITESSE_ALPHA
        vitesse_appliquee = int(round(vitesse_actuelle))

        tourner(angle_cible)
        robot.set_motor(1, vitesse_appliquee)

        if compteur_000 % 10 == 0:
            print(f"{etat}  pos={pos if pos is not None else '---'}  "
                  f"perdu={compteur_000}  angle={round(angle_actuel,1)}  vit={vitesse_appliquee}")

        time.sleep(0.025)

except KeyboardInterrupt:
    print("\nSTOP")
    robot.stopper()
    servos.set_angle(0, CENTRE)
    robot.destroy()
    servos.fermer()
