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
# PARAMÈTRES (vos valeurs conservées)
# ============================================================
CENTRE            = 97
SERVO_ALPHA       = 0.7

# Angles extrêmes (vos limites)
ANGLE_GAUCHE_MAX  = 128
ANGLE_DROITE_MAX  = 65

# VITESSES (vos valeurs conservées)
VITESSE_DROITE    = 34
VITESSE_VIRAGE_GAUCHE = 20
VITESSE_VIRAGE_DROITE = 18
VITESSE_PERDU     = 2
VITESSE_RECH      = 2

# LISSAGE
VITESSE_ALPHA     = 0.3

# Gestion des pertes (vous pouvez ajuster)
MAX_HOLD          = 60
MAINTIEN_AVANT_BALAYAGE = 100
DUREE_RECHERCHE   = 100   # réduit pour alterner plus vite si nécessaire

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

def angle_cible_depuis_pos(pos):
    """
    Calcule l'angle de manière proportionnelle à l'erreur pos,
    avec saturation aux bornes ANGLE_DROITE_MAX et ANGLE_GAUCHE_MAX.
    """
    if pos is None:
        return CENTRE
    # pos est entre -1 (tout à gauche) et 1 (tout à droite)
    # On mappe pos sur l'intervalle [ANGLE_GAUCHE_MAX, ANGLE_DROITE_MAX]
    # ANGLE_GAUCHE_MAX > CENTRE, ANGLE_DROITE_MAX < CENTRE
    if pos <= 0:
        # à gauche : de CENTRE à ANGLE_GAUCHE_MAX
        facteur = -pos  # 0 à 1
        angle = CENTRE + (ANGLE_GAUCHE_MAX - CENTRE) * facteur
    else:
        # à droite : de CENTRE à ANGLE_DROITE_MAX
        facteur = pos    # 0 à 1
        angle = CENTRE - (CENTRE - ANGLE_DROITE_MAX) * facteur
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
            compteur_000 = 0
            erreur_connue = pos
            dernier_etat_non_nul = etat

            if etat in [(1,1,0), (1,0,0)]:
                dernier_sens = 1
            elif etat in [(0,1,1), (0,0,1)]:
                dernier_sens = -1

            angle_cible = angle_cible_depuis_pos(pos)

            # Vitesse différenciée (vos valeurs)
            if etat in [(1,1,0), (1,0,0)]:
                vitesse_target = VITESSE_VIRAGE_GAUCHE
            elif etat in [(0,1,1), (0,0,1)]:
                vitesse_target = VITESSE_VIRAGE_DROITE
            else:
                vitesse_target = VITESSE_DROITE

        else:
            compteur_000 += 1

            if compteur_000 <= MAX_HOLD:
                # Mémoire : on continue avec la dernière position connue
                angle_cible = angle_cible_depuis_pos(erreur_connue)
                if dernier_etat_non_nul in [(1,1,0), (1,0,0)]:
                    vitesse_target = VITESSE_VIRAGE_GAUCHE
                elif dernier_etat_non_nul in [(0,1,1), (0,0,1)]:
                    vitesse_target = VITESSE_VIRAGE_DROITE
                else:
                    vitesse_target = VITESSE_DROITE
            else:
                # Perte réelle
                if compteur_000 - MAX_HOLD <= MAINTIEN_AVANT_BALAYAGE:
                    # On reste dans la dernière direction avec l'angle extrême
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
