#!/usr/bin/env python3
import time
from motor import RobotMotor
from servo import RobotServos
from lineTracking import LineTracker

robot = RobotMotor()
servos = RobotServos()
tracker = LineTracker()

# ==========================
# PARAMÈTRES (ajustables)
# ==========================
CENTRE = 97
GAIN_ANGLE = 30.0          # degrés par unité d'erreur (à régler)
SERVO_ALPHA = 0.6          # lissage du servo (0 = lent, 1 = rapide)

VITESSE_LIGNE = 45
VITESSE_VIRAGE = 24
VITESSE_RECHERCHE = 18     # vitesse en mode perte
VITESSE_ARRET = 0

# Pointillés : durée de la mémoire (en cycles)
MEMOIRE_POINTILLE = 25     # 25 * 25 ms = 625 ms
# Perte maximale avant arrêt (fin de piste)
PERDU_MAX = 100            # 2.5 secondes

# ==========================
# VARIABLES D'ÉTAT
# ==========================
angle_actuel = CENTRE
erreur_connue = 0.0
derniere_vitesse = VITESSE_LIGNE
compteur_perdu = 0
dernier_sens = 0           # 1=gauche, -1=droite, 0=inconnu

def position_depuis_etat(etat):
    """Calcule une erreur continue (-1..1) à partir des 3 capteurs."""
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

# ==========================
# DÉMARRAGE
# ==========================
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
            # ---- LIGNE VISIBLE ----
            compteur_perdu = 0
            erreur_connue = pos
            dernier_sens = 1 if pos < -0.3 else (-1 if pos > 0.3 else dernier_sens)
            
            # Angle proportionnel à l'erreur
            angle_cible = CENTRE - GAIN_ANGLE * pos
            angle_cible = max(65, min(128, angle_cible))  # bornes mécaniques
            
            # Vitesse adaptative : plus l'erreur est grande, plus on ralentit
            vitesse = VITESSE_LIGNE - abs(pos) * (VITESSE_LIGNE - VITESSE_VIRAGE)
            vitesse = max(VITESSE_VIRAGE, min(VITESSE_LIGNE, vitesse))
            derniere_vitesse = vitesse

        else:
            # ---- LIGNE PERDUE (000) ----
            compteur_perdu += 1

            # 1) Pointillés : on garde la dernière trajectoire
            if compteur_perdu <= MEMOIRE_POINTILLE:
                angle_cible = CENTRE - GAIN_ANGLE * erreur_connue
                angle_cible = max(65, min(128, angle_cible))
                vitesse = derniere_vitesse

            # 2) Perte réelle : on cherche en balayant
            elif compteur_perdu < PERDU_MAX:
                # Alternance gauche / droite toutes les 30 cycles (0.75s)
                phase = (compteur_perdu - MEMOIRE_POINTILLE) // 30
                if phase % 2 == 0:
                    angle_cible = 128   # braquage gauche
                else:
                    angle_cible = 65    # braquage droite
                vitesse = VITESSE_RECHERCHE

            # 3) Perte trop longue → fin de parcours
            else:
                print("--- Fin de piste détectée, arrêt ---")
                angle_cible = CENTRE
                vitesse = VITESSE_ARRET
                # On pourrait sortir de la boucle ou rester à l'arrêt
                # break

        # ---- Application ----
        tourner(angle_cible)
        robot.set_motor(1, int(round(vitesse)))

        # Debug (optionnel)
        if compteur_perdu % 10 == 0:
            print(f"{etat}  pos={pos if pos is not None else '---'}  "
                  f"perdu={compteur_perdu}  angle={round(angle_actuel,1)}  vit={int(vitesse)}")

        time.sleep(0.025)

except KeyboardInterrupt:
    print("STOP")
    robot.stopper()
    servos.set_angle(0, CENTRE)
    robot.destroy()
    servos.fermer()
