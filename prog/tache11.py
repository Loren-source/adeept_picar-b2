#!/usr/bin/env python3
import time
from motor import RobotMotor
from servo import RobotServos
from line import LineTracker

# ============================================================
# INSTANCIATION
# ============================================================
robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()

# ============================================================
# PARAMÈTRES RÉGLABLES
# ============================================================
CENTRE        = 97
GAIN_ANGLE    = 45.0
SERVO_ALPHA   = 0.7
MAX_HOLD      = 30            # mémoire plus longue en 000

VITESSE_MAX   = 34
VITESSE_MIN   = 4             # très lent dans les virages serrés
VITESSE_RECH  = 4
VITESSE_PERDU = 4

SEUIL_GAUCHE  = -0.3
SEUIL_DROITE  =  0.3

# Anticipation : si on voit (1,1,0) ou (0,1,1) plusieurs fois
SEUIL_ANTICIP = 2
FACTEUR_ANTICIP = 0.3          # ralentissement brutal

# Recherche : rester dans une direction plus longtemps
DUREE_RECHERCHE = 120          # cycles (3 secondes)
MAINTIEN_AVANT_BALAYAGE = 30   # cycles de maintien avant d'alterner

# ============================================================
# VARIABLES D'ÉTAT
# ============================================================
angle_actuel   = CENTRE
erreur_connue  = 0.0
compteur_000   = 0
dernier_sens   = 0
compteur_virag = 0

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

# ============================================================
# DÉMARRAGE
# ============================================================
print("START")
tourner(CENTRE)
robot.set_motor(1, 30)
time.sleep(1)

# ============================================================
# BOUCLE PRINCIPALE
# ============================================================
try:
    while True:
        s = tracker.get_status()
        etat = (s["left"], s["middle"], s["right"])
        pos = position_depuis_etat(etat)

        if pos is not None:
            # ---- Ligne visible ----
            compteur_000 = 0
            erreur_connue = pos

            if pos < SEUIL_GAUCHE:
                dernier_sens = 1
                compteur_virag += 1
            elif pos > SEUIL_DROITE:
                dernier_sens = -1
                compteur_virag += 1
            else:
                compteur_virag = max(0, compteur_virag - 1)

            gain_effectif = GAIN_ANGLE
            if compteur_virag >= SEUIL_ANTICIP:
                gain_effectif = GAIN_ANGLE * 1.2  # +20% de braquage

            angle_cible = CENTRE - gain_effectif * pos
            angle_cible = max(40, min(154, angle_cible))  # plage élargie

            vitesse = VITESSE_MAX - abs(pos) * 18
            if compteur_virag >= SEUIL_ANTICIP:
                vitesse *= FACTEUR_ANTICIP   # ralentissement fort
            vitesse = max(VITESSE_MIN, min(VITESSE_MAX, vitesse))

        else:
            # ---- Ligne perdue (000) ----
            compteur_000 += 1

            if compteur_000 <= MAX_HOLD:
                # Mémoire : on continue sur la dernière trajectoire
                angle_cible = CENTRE - GAIN_ANGLE * erreur_connue
                angle_cible = max(40, min(154, angle_cible))
                vitesse = VITESSE_MAX - abs(erreur_connue) * 18
                vitesse = max(VITESSE_MIN, min(VITESSE_MAX, vitesse))
            else:
                # Recherche active
                if compteur_000 - MAX_HOLD <= MAINTIEN_AVANT_BALAYAGE:
                    # On reste dans la dernière direction
                    if dernier_sens == 1:
                        angle_cible = 145
                    elif dernier_sens == -1:
                        angle_cible = 49
                    else:
                        angle_cible = CENTRE
                else:
                    # Balayage alterné par phases longues
                    phase = (compteur_000 - MAX_HOLD - MAINTIEN_AVANT_BALAYAGE) // DUREE_RECHERCHE
                    if phase % 2 == 0:
                        if dernier_sens == 1:
                            angle_cible = 145
                        elif dernier_sens == -1:
                            angle_cible = 49
                        else:
                            angle_cible = CENTRE
                    else:
                        if dernier_sens == 1:
                            angle_cible = 49
                        elif dernier_sens == -1:
                            angle_cible = 145
                        else:
                            angle_cible = CENTRE
                vitesse = VITESSE_PERDU

        # ---- Application ----
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
