#!/usr/bin/env python3
import time
import sys
import os

# Forcer Python à regarder dans le dossier local pour trouver les modules du robot
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Import des modules spécifiques au robot Adeept
try:
    import move
    import RPIservo
    import ultra
    print("Matériel initialisé avec succès pour l'évitement d'obstacles.")
except ImportError as e:
    print(f"Erreur d'importation. Assurez-vous que move.py, RPIservo.py et ultra.py sont dans le même dossier : {e}")
    sys.exit(1)

# Initialisation des composants moteurs et servos
move.setup()
scGear = RPIservo.ServoCtrl()
scGear.start()

def obtenir_distance_stable():
    """
    Cette fonction sécurise la lecture de la distance (issue de distRedress).
    Elle filtre les fausses mesures aberrantes du capteur à ultrasons.
    """
    essais_poubelle = 0
    distance = ultra.checkdist()
    while True:
        distance = ultra.checkdist()
        if distance > 200:
            essais_poubelle += 1
        elif essais_poubelle > 5 or distance < 200:
            break
    return round(distance, 2)

def mode_evitement_obstacles():
    print("\n--- Mode Évitement d'Obstacles Activé ---")
    
    # Position initiale : Roues droites (Servo 0) et tête centrée (Servo 1)
    scGear.moveAngle(0, 0)
    scGear.moveAngle(1, 0)
    time.sleep(0.5)

    try:
        while True:
            # 1. Mesure de la distance droit devant
            distance_devant = obtenir_distance_stable()
            print(f"Distance devant : {distance_devant} cm")

            # Cas 1 : La voie est libre (Plus de 55 cm) -> On avance tout droit
            if distance_devant > 55:
                scGear.moveAngle(0, 0)       # Roues de direction droites
                move.move(45, 1, "mid")      # Vitesse 45, Marche avant
                print(">> Voie libre : Avancer tout droit")
                time.sleep(0.2)

            # Cas 2 : Obstacle en approche (Entre 35 cm et 55 cm) -> On analyse les côtés
            elif 35 <= distance_devant <= 55:
                print("!! Obstacle détecté : Analyse des côtés...")
                move.motorStop()             # Arrêt des moteurs pour scanner en toute sécurité
                
                # Regarder à GAUCHE (Servo 1 à 60°)
                scGear.moveAngle(1, 60)
                time.sleep(0.5)
                distance_gauche = obtenir_distance_stable()
                print(f"   [Scan] Distance Gauche : {distance_gauche} cm")

                # Regarder à DROITE (Servo 1 à -60°)
                scGear.moveAngle(1, -60)
                time.sleep(0.5)
                distance_droite = obtenir_distance_stable()
                print(f"   [Scan] Distance Droite : {distance_droite} cm")

                # Replacer la tête bien au centre
                scGear.moveAngle(1, 0)
                time.sleep(0.2)

                # Prise de décision : On va là où il y a le plus de place
                if distance_gauche >= distance_droite:
                    print("<< Décision : Tourner à GAUCHE")
                    scGear.moveAngle(0, 40)       # Braquage des roues à gauche
                    move.move(50, 1, "left")      # En avant toute pour tourner
                    time.sleep(0.7)               # Temps accordé pour effectuer la manoeuvre
                else:
                    print(">> Décision : Tourner à DROITE")
                    scGear.moveAngle(0, -40)      # Braquage des roues à droite
                    move.move(50, 1, "right")     # En avant toute pour tourner
                    time.sleep(0.7)               # Temps accordé pour effectuer la manoeuvre
                
                # Remettre les roues droites après le virage
                scGear.moveAngle(0, 0)

            # Cas 3 : Danger immédiat (Moins de 35 cm) -> On recule
            else:
                print("⚡ DANGER : Obstacle trop proche ! Marche arrière.")
                scGear.moveAngle(0, 0)            # Roues droites
                move.move(50, -1, "mid")          # Vitesse 50, Marche arrière
                time.sleep(0.4)
                move.motorStop()

    except KeyboardInterrupt:
        # Arrêt propre en cas d'interruption par l'utilisateur (Ctrl+C)
        print("\nArrêt du mode évitement d'obstacles.")
        move.motorStop()
        scGear.moveAngle(0, 0)
        scGear.moveAngle(1, 0)

if __name__ == '__main__':
    # Lancement de la boucle d'évitement
    mode_evitement_obstacles()
