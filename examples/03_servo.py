#!/usr/bin/env python3


import time
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

#  CONSTANTES DE CONFIGURATION

PCA_ADDRESS   = 0x5f       # Adresse I²C de la carte Adeept
PWM_FREQ      = 50         # Hz – fréquence standard servomoteur

MIN_PULSE     = 500        # µs – impulsion mini (0°)
MAX_PULSE     = 2400       # µs – impulsion maxi (180°)
ACTUATION     = 180        # degrés – plage totale du servo

ANGLE_MIN     = 0          # limite basse de sécurité
ANGLE_MAX     = 180        # limite haute de sécurité

# Canaux des servos sur le robot
CANAL_TEST    = 15         # servo libre, sans mécanique
CANAUX_ROBOT  = [0, 1, 2]  # servos montés sur le robot


#  INITIALISATION

i2c = busio.I2C(SCL, SDA)
pca = PCA9685(i2c, address=PCA_ADDRESS)
pca.frequency = PWM_FREQ

# Création des objets servo UNE SEULE FOIS (optimisation)
# Dictionnaire : canal → objet Servo
_servos = {}

def get_servo(canal: int):
    """Retourne l'objet Servo du canal, en le créant si besoin."""
    if canal not in _servos:
        _servos[canal] = servo.Servo(
            pca.channels[canal],
            min_pulse=MIN_PULSE,
            max_pulse=MAX_PULSE,
            actuation_range=ACTUATION
        )
    return _servos[canal]



#  SOUS-TÂCHE 1 – Test sur servo libre (CH15)


def test_servo_libre():
    """
    Test aller-retour sur le servo CH15 (libre de toute mécanique).
    À utiliser en premier pour valider le câblage sans risque.
    """
    print(f"[TEST] Servo libre canal {CANAL_TEST} – aller-retour 0°→179°→0°")
    s = get_servo(CANAL_TEST)
    for i in range(180):
        s.angle = i
        time.sleep(0.01)
    time.sleep(0.5)
    for i in range(180):
        s.angle = 180 - i
        time.sleep(0.01)
    time.sleep(0.5)
    print("[TEST] Terminé.")



#  SOUS-TÂCHE 2 – Fonction set_angle(n°servo, angle)


def set_angle(numero_servo: int, angle: float):
    """
    Positionne le servomoteur numéro_servo à l'angle demandé.

   
    Sécurité : l'angle est automatiquement limité à [ANGLE_MIN, ANGLE_MAX]
    pour éviter la mise en butée et la surchauffe.
    """
    # Clamp de sécurité
    angle_safe = max(ANGLE_MIN, min(ANGLE_MAX, angle))

    if angle_safe != angle:
        print(f"[SECURITE] Angle {angle}° corrigé → {angle_safe}° (hors plage)")

    s = get_servo(numero_servo)
    s.angle = angle_safe
    print(f"[SERVO {numero_servo}] → {angle_safe}°")


#  COMMANDE MANUELLE – Validation des 3 servos robot



def centrer_servos():
    """Met les 3 servos du robot en position centrale (90°)."""
    print("[INFO] Centrage des servos CH0, CH1, CH2 à 90°...")
    for canal in CANAUX_ROBOT:
        set_angle(canal, 90)
    print("[INFO] Servos centrés.")


def main():
    print(AIDE)
    # Centrage de sécurité au démarrage
    centrer_servos()

    try:
        while True:
            try:
                commande = input("commande> ").strip().lower()
            except EOFError:
                break

            if not commande:
                continue

            tokens = commande.split()
            cmd = tokens[0]

            try:
                if cmd in ('q', 'quit', 'exit'):
                    break

                elif cmd == 'test':
                    test_servo_libre()

                elif cmd == 'centre':
                    centrer_servos()

                elif cmd == 'set':
                    if len(tokens) < 3:
                        print("[ERREUR] Usage : set <canal> <angle>")
                        continue
                    canal = int(tokens[1])
                    angle = float(tokens[2])
                    if canal not in range(16):
                        print("[ERREUR] Canal invalide (0 à 15).")
                        continue
                    set_angle(canal, angle)

                else:
                    print(f"[ERREUR] Commande inconnue : '{cmd}'")

            except (ValueError, IndexError) as e:
                print(f"[ERREUR] Paramètre invalide : {e}")

    finally:
        # Retour au centre avant de quitter
        centrer_servos()
        pca.deinit()
        print("Au revoir.")


if __name__ == "__main__":
    main()

