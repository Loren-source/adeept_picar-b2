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
SERVO_ALPHA       = 0.8

ANGLE_GAUCHE_MAX  = 128
ANGLE_DROITE_MAX  = 65

VITESSE_DROITE    = 34
VITESSE_VIRAGE_GAUCHE = 20
VITESSE_VIRAGE_DROITE = 18
VITESSE_RECUL     = -15          # marche arrière un peu plus rapide
VITESSE_ARRET     = 0

VITESSE_ALPHA     = 0.3

# Seuils pour la recovery
SEUIL_PERDU       = 5            # cycles de 000 avant recovery
MAX_RECUL_TIME    = 2.0          # temps max de recul en secondes

# ============================================================
# VARIABLES D'ÉTAT
# ============================================================
angle_actuel      = CENTRE
erreur_connue     = 0.0
dernier_angle_cible = CENTRE    # NOUVEAU : stocke le dernier angle calculé
compteur_000      = 0
dernier_sens      = 0
dernier_etat_non_nul = (1,1,1)
vitesse_actuelle  = VITESSE_DROITE

mode_recovery     = False
debut_recul       = 0.0

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
    if etat in [(1,1,0), (1,0,0)]:
        return ANGLE_GAUCHE_MAX
    elif etat in [(0,1,1), (0,0,1)]:
        return ANGLE_DROITE_MAX
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

        # ---- Si ligne visible ----
        if pos is not None:
            compteur_000 = 0
            erreur_connue = pos
            dernier_etat_non_nul = etat

            if etat in [(1,1,0), (1,0,0)]:
                dernier_sens = 1
            elif etat in [(0,1,1), (0,0,1)]:
                dernier_sens = -1

            # Sortie du mode recovery
            if mode_recovery:
                mode_recovery = False
                print("--- Ligne retrouvée, reprise en avant ---")
                robot.set_motor(1, 0)
                time.sleep(0.2)

            # Calcul de l'angle cible
            angle_cible = angle_cible_depuis_etat(etat)
            dernier_angle_cible = angle_cible  # on mémorise

            # Vitesse
            if etat in [(1,1,0), (1,0,0)]:
                vitesse_target = VITESSE_VIRAGE_GAUCHE
            elif etat in [(0,1,1), (0,0,1)]:
                vitesse_target = VITESSE_VIRAGE_DROITE
            else:
                vitesse_target = VITESSE_DROITE

        # ---- Ligne perdue (000) ----
        else:
            compteur_000 += 1

            # Déclenchement recovery si seuil atteint et pas déjà en recovery
            if not mode_recovery and compteur_000 >= SEUIL_PERDU:
                print("--- Ligne perdue, déclenchement recovery ---")
                mode_recovery = True
                robot.set_motor(1, 0)
                time.sleep(0.2)
                debut_recul = time.time()
                # On utilise le dernier angle cible mémorisé
                angle_cible = dernier_angle_cible

            if mode_recovery:
                # On recule en gardant le dernier angle cible
                vitesse_target = VITESSE_RECUL
                # On limite le temps de recul
                if time.time() - debut_recul > MAX_RECUL_TIME:
                    print("--- Temps de recul maximal atteint, arrêt ---")
                    mode_recovery = False
                    robot.set_motor(1, 0)
                    vitesse_target = 0
                    angle_cible = CENTRE
                # Sinon, on continue de reculer avec le dernier angle

        # ---- Application ----
        vitesse_actuelle = vitesse_actuelle * (1 - VITESSE_ALPHA) + vitesse_target * VITESSE_ALPHA
        vitesse_appliquee = int(round(vitesse_actuelle))

        tourner(angle_cible)
        robot.set_motor(1, vitesse_appliquee)

        if compteur_000 % 10 == 0:
            print(f"{etat}  pos={pos if pos is not None else '---'}  "
                  f"perdu={compteur_000}  angle={round(angle_actuel,1)}  vit={vitesse_appliquee}  recovery={mode_recovery}")

        time.sleep(0.025)

except KeyboardInterrupt:
    print("\nSTOP")
    robot.stopper()
    servos.set_angle(0, CENTRE)
    robot.destroy()
    servos.fermer()
