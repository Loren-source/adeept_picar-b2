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
GAIN_ANGLE    = 50.0
SERVO_ALPHA   = 0.7

# VITESSES
VITESSE_DROITE = 34
VITESSE_VIRAGE = 6              # très lent pour bien négocier les courbes
VITESSE_PERDU  = 4
VITESSE_RECH   = 4

# LISSAGE DE LA VITESSE (pour des transitions fluides)
VITESSE_ALPHA  = 0.3            # plus petit = transition plus douce

# Seuils de détection de virage (erreur absolue)
SEUIL_VIRAGE   = 0.3            # si |pos| > ce seuil, on considère qu'on est en virage

# Gestion des pertes
MAX_HOLD       = 50             # cycles de mémoire après perte
MAINTIEN_AVANT_BALAYAGE = 80    # cycles avant de balayer
DUREE_RECHERCHE = 300           # cycles par phase de balayage

# ============================================================
# VARIABLES D'ÉTAT
# ============================================================
angle_actuel   = CENTRE
erreur_connue  = 0.0
compteur_000   = 0
dernier_sens   = 0              # 1=gauche, -1=droite
vitesse_actuelle = VITESSE_DROITE  # pour le lissage

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
    """Calcule la vitesse cible en fonction de l'erreur pos."""
    if pos is None:
        return VITESSE_PERDU  # perte, on sera géré ailleurs
    abs_pos = abs(pos)
    if abs_pos < SEUIL_VIRAGE:
        return VITESSE_DROITE
    else:
        # Plus l'erreur est grande, plus on ralentit
        facteur = 1.0 - (abs_pos - SEUIL_VIRAGE) / (1.0 - SEUIL_VIRAGE)
        facteur = max(0.1, facteur)  # ne pas descendre en dessous de 10% de la vitesse virage
        return VITESSE_VIRAGE + (VITESSE_DROITE - VITESSE_VIRAGE) * facteur

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
            if etat in [(1,1,0), (1,0,0)]:
                dernier_sens = 1
            elif etat in [(0,1,1), (0,0,1)]:
                dernier_sens = -1

            # Commande angulaire
            angle_cible = CENTRE - GAIN_ANGLE * pos
            angle_cible = max(30, min(164, angle_cible))

            # Vitesse cible basée sur l'erreur
            vitesse_target = vitesse_cible(pos)

        else:
            # ---- Ligne perdue (000) ----
            compteur_000 += 1

            if compteur_000 <= MAX_HOLD:
                # Mémoire : on continue avec la dernière trajectoire
                angle_cible = CENTRE - GAIN_ANGLE * erreur_connue
                angle_cible = max(30, min(164, angle_cible))
                vitesse_target = vitesse_cible(erreur_connue)
            else:
                # Perte réelle
                if compteur_000 - MAX_HOLD <= MAINTIEN_AVANT_BALAYAGE:
                    # On reste braqué dans la dernière direction
                    if dernier_sens == 1:
                        angle_cible = 155
                    elif dernier_sens == -1:
                        angle_cible = 39
                    else:
                        angle_cible = CENTRE
                    vitesse_target = VITESSE_RECH
                else:
                    # Balayage alterné
                    phase = (compteur_000 - MAX_HOLD - MAINTIEN_AVANT_BALAYAGE) // DUREE_RECHERCHE
                    if phase % 2 == 0:
                        if dernier_sens == 1:
                            angle_cible = 155
                        elif dernier_sens == -1:
                            angle_cible = 39
                        else:
                            angle_cible = CENTRE
                    else:
                        if dernier_sens == 1:
                            angle_cible = 39
                        elif dernier_sens == -1:
                            angle_cible = 155
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
