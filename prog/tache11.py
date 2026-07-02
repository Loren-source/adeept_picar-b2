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
GAIN_ANGLE    = 60.0          # gain très élevé pour les virages serrés
SERVO_ALPHA   = 0.7           # réactivité normale
ALPHA_VIRAGE  = 0.9           # réactivité renforcée en cas d'erreur forte

VITESSE_MAX   = 34
VITESSE_MIN   = 7             # un peu plus élevé qu'avant (4) pour garder de l'élan
VITESSE_RECH  = 5
VITESSE_PERDU = 5

SEUIL_GAUCHE  = -0.3
SEUIL_DROITE  =  0.3

# Anticipation : détection de virage serré
SEUIL_ANTICIP = 2
FACTEUR_ANTICIP = 0.5          # ralentissement modéré (pas trop fort)

# Recherche
MAX_HOLD      = 40            # mémoire plus longue
DUREE_RECHERCHE = 200          # phases de 5 secondes
MAINTIEN_AVANT_BALAYAGE = 50

# ============================================================
# VARIABLES D'ÉTAT
# ============================================================
angle_actuel   = CENTRE
erreur_connue  = 0.0
compteur_000   = 0
dernier_sens   = 0
compteur_virag = 0

# Historique pour anticiper
historique_etats = []

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

def tourner(cible, alpha=SERVO_ALPHA):
    global angle_actuel
    # Si l'écart est grand, on peut utiliser un alpha plus fort
    if abs(cible - angle_actuel) > 20:
        alpha = max(alpha, 0.85)
    angle_actuel = angle_actuel * (1 - alpha) + cible * alpha
    servos.set_angle(0, round(angle_actuel, 1))

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

        # Mise à jour de l'historique
        historique_etats.append(etat)
        if len(historique_etats) > 5:
            historique_etats.pop(0)

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

            # Détection d'un virage serré imminent (transition rapide)
            virage_serre = False
            if len(historique_etats) >= 3:
                # Si on voit (1,1,0) puis (1,0,0) rapidement
                if (historique_etats[-3] == (1,1,0) or historique_etats[-3] == (1,1,1)) and \
                   (historique_etats[-2] == (1,1,0)) and (historique_etats[-1] == (1,0,0)):
                    virage_serre = True
                # Symétrique pour droite
                if (historique_etats[-3] == (0,1,1) or historique_etats[-3] == (1,1,1)) and \
                   (historique_etats[-2] == (0,1,1)) and (historique_etats[-1] == (0,0,1)):
                    virage_serre = True

            # Calcul de l'angle avec gain dynamique
            gain_effectif = GAIN_ANGLE
            if compteur_virag >= SEUIL_ANTICIP or virage_serre:
                gain_effectif = GAIN_ANGLE * 1.3   # +30%
                # Si c'est un virage serré, on applique directement l'angle max
                if virage_serre:
                    if pos < 0:
                        angle_cible = 155
                    else:
                        angle_cible = 39
                    # On sort de la logique normale
                    vitesse = VITESSE_MIN * 1.2  # un peu plus rapide pour le virage
                    tourner(angle_cible, alpha=ALPHA_VIRAGE)
                    robot.set_motor(1, int(round(vitesse)))
                    continue

            angle_cible = CENTRE - gain_effectif * pos
            angle_cible = max(30, min(164, angle_cible))  # plage étendue

            # Vitesse adaptative
            vitesse = VITESSE_MAX - abs(pos) * 18
            if compteur_virag >= SEUIL_ANTICIP or virage_serre:
                vitesse *= FACTEUR_ANTICIP
            vitesse = max(VITESSE_MIN, min(VITESSE_MAX, vitesse))

        else:
            # ---- Ligne perdue (000) ----
            compteur_000 += 1

            if compteur_000 <= MAX_HOLD:
                # Mémoire : continuer sur la dernière trajectoire
                angle_cible = CENTRE - GAIN_ANGLE * erreur_connue
                angle_cible = max(30, min(164, angle_cible))
                vitesse = VITESSE_MAX - abs(erreur_connue) * 18
                vitesse = max(VITESSE_MIN, min(VITESSE_MAX, vitesse))
            else:
                # Recherche active
                if compteur_000 - MAX_HOLD <= MAINTIEN_AVANT_BALAYAGE:
                    # On reste dans la dernière direction
                    if dernier_sens == 1:
                        angle_cible = 155
                    elif dernier_sens == -1:
                        angle_cible = 39
                    else:
                        angle_cible = CENTRE
                else:
                    # Balayage alterné par phases longues
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
                vitesse = VITESSE_PERDU

        # ---- Application ----
        # Déterminer l'alpha en fonction de l'urgence
        alpha_use = SERVO_ALPHA
        if abs(angle_cible - CENTRE) > 40:
            alpha_use = ALPHA_VIRAGE
        tourner(angle_cible, alpha=alpha_use)
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
