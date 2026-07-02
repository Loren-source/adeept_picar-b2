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
GAIN_ANGLE        = 50.0
SERVO_ALPHA       = 0.7

# Angles extrêmes (ajustez selon les capacités physiques du servo)
ANGLE_GAUCHE_MAX  = 169          # braquage max à gauche (proche de 180)
ANGLE_DROITE_MAX  = 25           # braquage max à droite (proche de 0)

# VITESSES
VITESSE_DROITE    = 34
VITESSE_VIRAGE    = 4            # très lent pour les virages serrés
VITESSE_PERDU     = 4
VITESSE_RECH      = 4

# LISSAGE DE LA VITESSE
VITESSE_ALPHA     = 0.3

# Seuil pour considérer qu'on est en virage (erreur absolue)
SEUIL_VIRAGE      = 0.3

# Gestion des pertes
MAX_HOLD          = 50
MAINTIEN_AVANT_BALAYAGE = 80
DUREE_RECHERCHE   = 300

# ============================================================
# VARIABLES D'ÉTAT
# ============================================================
angle_actuel      = CENTRE
erreur_connue     = 0.0
compteur_000      = 0
dernier_sens      = 0
vitesse_actuelle  = VITESSE_DROITE

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

def vitesse_cible(pos, etat):
    """Calcule la vitesse cible en fonction de l'erreur et de l'état."""
    if pos is None:
        return VITESSE_PERDU
    abs_pos = abs(pos)
    # Si on est en virage (état asymétrique), on force la vitesse virage
    if etat in [(1,1,0), (1,0,0), (0,1,1), (0,0,1)]:
        return VITESSE_VIRAGE
    # Sinon, variation progressive
    if abs_pos < SEUIL_VIRAGE:
        return VITESSE_DROITE
    else:
        facteur = 1.0 - (abs_pos - SEUIL_VIRAGE) / (1.0 - SEUIL_VIRAGE)
        facteur = max(0.1, facteur)
        return VITESSE_VIRAGE + (VITESSE_DROITE - VITESSE_VIRAGE) * facteur

def angle_cible_depuis_pos(pos, etat):
    """Détermine l'angle cible en fonction de l'erreur et de l'état."""
    if pos is None:
        return CENTRE  # sera remplacé en cas de perte
    
    # Si on est en virage serré (seul capteur extérieur), on force l'angle extrême
    if etat == (1,0,0):
        return ANGLE_GAUCHE_MAX
    elif etat == (0,0,1):
        return ANGLE_DROITE_MAX
    elif etat == (1,1,0):
        # virage à gauche modéré, on peut utiliser le gain
        angle = CENTRE - GAIN_ANGLE * pos
        # mais on limite à ANGLE_GAUCHE_MAX
        return min(angle, ANGLE_GAUCHE_MAX)
    elif etat == (0,1,1):
        angle = CENTRE - GAIN_ANGLE * pos
        return max(angle, ANGLE_DROITE_MAX)
    else:
        # cas centré ou autres
        angle = CENTRE - GAIN_ANGLE * pos
        # on limite aux extrêmes
        return max(ANGLE_DROITE_MAX, min(ANGLE_GAUCHE_MAX, angle))

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

            # Angle cible
            angle_cible = angle_cible_depuis_pos(pos, etat)

            # Vitesse cible
            vitesse_target = vitesse_cible(pos, etat)

        else:
            # ---- Ligne perdue (000) ----
            compteur_000 += 1

            if compteur_000 <= MAX_HOLD:
                # Mémoire : on continue avec la dernière trajectoire
                angle_cible = angle_cible_depuis_pos(erreur_connue, dernier_etat_non_nul)
                vitesse_target = vitesse_cible(erreur_connue, dernier_etat_non_nul)
            else:
                # Perte réelle
                if compteur_000 - MAX_HOLD <= MAINTIEN_AVANT_BALAYAGE:
                    # On reste braqué dans la dernière direction
                    if dernier_sens == 1:
                        angle_cible = ANGLE_GAUCHE_MAX
                    elif dernier_sens == -1:
                        angle_cible = ANGLE_DROITE_MAX
                    else:
                        angle_cible = CENTRE
                    vitesse_target = VITESSE_RECH
                else:
                    # Balayage alterné
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

        # ---- Lissage de la vitesse ----
        vitesse_actuelle = vitesse_actuelle * (1 - VITESSE_ALPHA) + vitesse_target * VITESSE_ALPHA
        vitesse_appliquee = int(round(vitesse_actuelle))

        # ---- Application ----
        tourner(angle_cible)
        robot.set_motor(1, vitesse_appliquee)

        # Mémoriser le dernier état non nul pour la perte
        if pos is not None:
            dernier_etat_non_nul = etat

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
