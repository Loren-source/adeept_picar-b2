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
# PARAMÈTRES (réglables sur le terrain)
# ============================================================
CENTRE        = 97
GAIN_ANGLE    = 30.0          # braquage proportionnel
SERVO_ALPHA   = 0.7           # lissage du servo (0.7 = réactif)
MAX_HOLD      = 12            # cycles de mémoire en 000 (12 × 25 ms = 300 ms)

VITESSE_MAX   = 34
VITESSE_MIN   = 16
VITESSE_RECH  = 14

# Seuils pour la mémorisation de direction
SEUIL_GAUCHE  = -0.3
SEUIL_DROITE  =  0.3

# Balayage après perte prolongée
SEUIL_BALAYAGE = 50           # après 50 cycles (1,25 s) de perte, on cherche
DUREE_PHASE    = 30           # chaque phase dure 30 cycles (0,75 s)

# ============================================================
# VARIABLES D'ÉTAT
# ============================================================
angle_actuel   = CENTRE
erreur_connue  = 0.0
compteur_000   = 0
dernier_sens   = 0            # 1=gauche, -1=droite, 0=inconnu

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

            # Mémorisation de la direction (uniquement si nettement décentré)
            if pos < SEUIL_GAUCHE:
                dernier_sens = 1
            elif pos > SEUIL_DROITE:
                dernier_sens = -1
            # sinon on ne change rien

            # Commande proportionnelle
            angle_cible = CENTRE - GAIN_ANGLE * pos
            angle_cible = max(60, min(134, angle_cible))

            # Vitesse adaptative
            vitesse = VITESSE_MAX - abs(pos) * 18
            vitesse = max(VITESSE_MIN, min(VITESSE_MAX, vitesse))

        else:
            # ---- Ligne perdue (000) ----
            compteur_000 += 1

            if compteur_000 <= MAX_HOLD:
                # Pendant la mémoire courte, on suit la dernière trajectoire connue
                angle_cible = CENTRE - GAIN_ANGLE * erreur_connue
                angle_cible = max(60, min(134, angle_cible))
                vitesse = VITESSE_MAX - abs(erreur_connue) * 18
                vitesse = max(VITESSE_MIN, min(VITESSE_MAX, vitesse))

            else:
                # Perte réelle : on cherche la ligne
                if compteur_000 < SEUIL_BALAYAGE:
                    # On braque dans la dernière direction connue
                    if dernier_sens == 1:
                        angle_cible = 128
                    elif dernier_sens == -1:
                        angle_cible = 65
                    else:
                        angle_cible = CENTRE
                    vitesse = VITESSE_RECH
                else:
                    # Balayage alterné par phases (évite l'oscillation rapide)
                    phase = (compteur_000 - SEUIL_BALAYAGE) // DUREE_PHASE
                    if phase % 2 == 0:
                        angle_cible = 128
                    else:
                        angle_cible = 65
                    vitesse = VITESSE_RECH
                    # Optionnel : si on cherche trop longtemps, on peut réinitialiser
                    # pour recommencer le cycle (mais ce n'est pas obligatoire)

        # ---- Application ----
        tourner(angle_cible)
        robot.set_motor(1, int(round(vitesse)))

        # Debug
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
