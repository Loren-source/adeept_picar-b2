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
CENTRE        = 97
GAIN_ANGLE    = 70.0          # très réactif
SERVO_ALPHA   = 0.7

VITESSE_MAX   = 34
VITESSE_MIN   = 18             # très lent dans les virages serrés
VITESSE_RECH  = 4
VITESSE_PERDU = 4

SEUIL_VIRAGE  = 0.3           # à partir de cette erreur, on ralentit

MAX_HOLD      = 60            # cycles de mémoire après perte
MAINTIEN_AVANT_BALAYAGE = 80
DUREE_RECHERCHE = 300

VITESSE_ALPHA = 0.3           # lissage de la vitesse

# ============================================================
# VARIABLES D'ÉTAT
# ============================================================
angle_actuel   = CENTRE
erreur_connue  = 0.0
compteur_000   = 0
dernier_sens   = 0
vitesse_actuelle = VITESSE_MAX

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

def vitesse_cible(pos):
    """Calcule la vitesse cible en fonction de l'erreur."""
    if pos is None:
        return VITESSE_PERDU
    abs_pos = abs(pos)
    if abs_pos < SEUIL_VIRAGE:
        return VITESSE_MAX
    else:
        # Interpolation linéaire entre VITESSE_MAX et VITESSE_MIN
        facteur = (abs_pos - SEUIL_VIRAGE) / (1.0 - SEUIL_VIRAGE)
        facteur = min(1.0, facteur)
        vitesse = VITESSE_MAX - facteur * (VITESSE_MAX - VITESSE_MIN)
        return max(VITESSE_MIN, vitesse)

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
            # ---- Ligne visible ----
            compteur_000 = 0
            erreur_connue = pos

            # Mémoriser la direction pour la recherche
            if pos < -0.3:
                dernier_sens = 1
            elif pos > 0.3:
                dernier_sens = -1
            # sinon on garde le dernier

            # Angle proportionnel avec gain fort
            angle_cible = CENTRE - GAIN_ANGLE * pos
            # Limiter pour éviter des angles impossibles (mais on laisse large)
            angle_cible = max(20, min(174, angle_cible))

            # Vitesse cible
            vitesse_target = vitesse_cible(pos)

        else:
            # ---- Ligne perdue (000) ----
            compteur_000 += 1

            if compteur_000 <= MAX_HOLD:
                # Mémoire : continuer avec la dernière erreur
                angle_cible = CENTRE - GAIN_ANGLE * erreur_connue
                angle_cible = max(20, min(174, angle_cible))
                vitesse_target = vitesse_cible(erreur_connue)
            else:
                # Perte réelle
                if compteur_000 - MAX_HOLD <= MAINTIEN_AVANT_BALAYAGE:
                    # On reste dans la dernière direction
                    if dernier_sens == 1:
                        angle_cible = 165
                    elif dernier_sens == -1:
                        angle_cible = 29
                    else:
                        angle_cible = CENTRE
                    vitesse_target = VITESSE_RECH
                else:
                    # Balayage alterné
                    phase = (compteur_000 - MAX_HOLD - MAINTIEN_AVANT_BALAYAGE) // DUREE_RECHERCHE
                    if phase % 2 == 0:
                        if dernier_sens == 1:
                            angle_cible = 165
                        elif dernier_sens == -1:
                            angle_cible = 29
                        else:
                            angle_cible = CENTRE
                    else:
                        if dernier_sens == 1:
                            angle_cible = 29
                        elif dernier_sens == -1:
                            angle_cible = 165
                        else:
                            angle_cible = CENTRE
                    vitesse_target = VITESSE_PERDU

        # ---- Lissage de la vitesse ----
        vitesse_actuelle = vitesse_actuelle * (1 - VITESSE_ALPHA) + vitesse_target * VITESSE_ALPHA
        vitesse_appliquee = int(round(vitesse_actuelle))

        # ---- Application ----
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
