import threading
import time
from motor import RobotMotor
from ultra import Ultrasonic
from lineTracking import LineTracker
from servo import RobotServos

robot = RobotMotor()
ultra = Ultrasonic()
tracker = LineTracker()
servos = RobotServos()

# ==========================
# REGLAGES PARAMÉTRÉS
# ==========================
ANGLE_CENTRE = 97

# Vitesses adaptatives
VITESSE_LIGNE_DROITE = 30  # Vitesse nominale quand il est bien centré
VITESSE_VIRAGE_SERRE = 15  # Ralentissement automatique dans les courbes pour la stabilité
VITESSE_RECHERCHE = 12     # Vitesse prudente si la ligne balance

DISTANCE_STOP = 200

# ==========================
# VARIABLES D'ÉTAT
# ==========================
actif = False
angle_actuel = ANGLE_CENTRE
# Cette variable va stocker la dernière direction connue de la ligne (-1 pour gauche, +1 pour droite)
direction_memoire = 0  

# ==========================
# FONCTIONS DE PILOTAGE FLUIDES
# ==========================
def piloter(angle_cible, vitesse):
    """ Aligne le servo et gère la vitesse du moteur en douceur """
    global angle_actuel
    
    # Limitation de sécurité pour les servos du PiCar-B
    angle_cible = max(55, min(145, angle_cible))
    
    # Application de l'angle uniquement s'il change pour économiser les servos
    if angle_actuel != angle_cible:
        servos.set_angle(0, angle_cible)
        angle_actuel = angle_cible

    robot.set_motor(1, vitesse)

# ==========================
# CLAVIER
# ==========================
def clavier():
    global actif
    while True:
        c = input().strip().upper()
        if c == "M":
            actif = True
            print("START")
        elif c == "A":
            actif = False
            robot.stopper()
            print("STOP")

threading.Thread(target=clavier, daemon=True).start()

# ==========================
# PROGRAMME PRINCIPAL
# ==========================
print("Robot Prêt. Appuyez sur 'M' pour démarrer.")

try:
    while True:
        if not actif:
            time.sleep(0.02)
            continue

        # Sécurité Obstacle
        if ultra.get_distance() < DISTANCE_STOP:
            robot.stopper()
            actif = False
            continue

        # Lecture des capteurs
        s = tracker.get_status()
        cap = (s["left"], s["middle"], s["right"])

        # =================================================================
        # ANALYSE ET CORRECTION DYNAMIQUE
        # =================================================================
        
        # Cas 1 : Parfaitement centré ou sur la ligne droite (Tout droit)
        if cap == (1, 1, 1) or cap == (0, 1, 0):
            direction_memoire = 0 # Centré
            piloter(ANGLE_CENTRE, VITESSE_LIGNE_DROITE)

        # Cas 2 : Déviation légère à GAUCHE (La ligne s'échappe à gauche)
        elif cap == (0, 1, 1):
            direction_memoire = -1 # Mémoire : la ligne est à gauche
            # On applique un angle de correction doux (ex: 115° au lieu de 125°)
            piloter(115, VITESSE_LIGNE_DROITE - 5)

        # Cas 3 : Déviation forte à GAUCHE (Virage serré à gauche)
        elif cap == (0, 0, 1):
            direction_memoire = -2 # Mémoire : virage fort à gauche
            # Braquage fort mais vitesse réduite pour garder l'adhérence
            piloter(145, VITESSE_VIRAGE_SERRE)

        # Cas 4 : Déviation légère à DROITE (La ligne s'échappe à droite)
        elif cap == (1, 1, 0):
            direction_memoire = 1 # Mémoire : la ligne est à droite
            # Correction douce à droite (ex: 79° au lieu de 75°)
            piloter(79, VITESSE_LIGNE_DROITE - 5)

        # Cas 5 : Déviation forte à DROITE (Virage serré à droite)
        elif cap == (1, 0, 0):
            direction_memoire = 2 # Mémoire : virage fort à droite
            piloter(55, VITESSE_VIRAGE_SERRE)

        # Cas 6 : PERTE DE LIGNE (0, 0, 0) - GESTION INTELLIGENTE
        elif cap == (0, 0, 0):
            # Le robot adapte son comportement selon l'HISTORIQUE immédiat
            if direction_memoire == -2:
                # Il était dans un virage fort à gauche : on maintient le braquage max à gauche à basse vitesse
                piloter(145, VITESSE_RECHERCHE)
            elif direction_memoire == 2:
                # Il était dans un virage fort à droite : on maintient le braquage max à droite à basse vitesse
                piloter(55, VITESSE_RECHERCHE)
            elif direction_memoire == -1:
                # Petite perte à gauche : correction modérée
                piloter(125, VITESSE_RECHERCHE)
            elif direction_memoire == 1:
                # Petite perte à droite : correction modérée
                piloter(75, VITESSE_RECHERCHE)
            else:
                # Perte inconnue en ligne droite : on continue tout droit lentement pour retrouver la ligne
                piloter(ANGLE_CENTRE, VITESSE_RECHERCHE)

        time.sleep(0.015) # Échantillonnage un peu plus rapide pour capter les changements brusques

except KeyboardInterrupt:
    pass
finally:
    robot.stopper()
    servos.set_angle(0, ANGLE_CENTRE)
    print("FIN")
