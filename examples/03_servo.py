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

# Dictionnaire : canal → objet Servo  (créés à la demande)
_servos: dict[int, servo.Servo] = {}

# Mémorisation des derniers angles positionnés
_angles: dict[int, float] = {}


def get_servo(canal: int) -> servo.Servo:
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


def test_servo_libre(canal: int = CANAL_TEST):
    """
    Test aller-retour sur le servo du canal donné (défaut : CH15, libre de toute mécanique).
    À utiliser en premier pour valider le câblage sans risque.
    """
    print(f"[TEST] Canal {canal} – aller-retour 0°→179°→0°")
    s = get_servo(canal)
    for i in range(180):
        s.angle = i
        time.sleep(0.01)
    time.sleep(0.5)
    for i in range(180):
        s.angle = 180 - i
        time.sleep(0.01)
    time.sleep(0.5)
    print("[TEST] Terminé.")


#  SOUS-TÂCHE 2 – Fonction set_angle(canal, angle)


def set_angle(canal: int, angle: float):
    """
    Positionne le servomoteur du canal à l'angle demandé.
    Sécurité : l'angle est automatiquement limité à [ANGLE_MIN, ANGLE_MAX].
    """
    angle_safe = max(ANGLE_MIN, min(ANGLE_MAX, angle))

    if angle_safe != angle:
        print(f"[SECURITE] Angle {angle}° corrigé → {angle_safe}° (hors plage)")

    s = get_servo(canal)
    s.angle = angle_safe
    _angles[canal] = angle_safe
    print(f"[CH{canal:02d}] → {angle_safe}°")


#  COMMANDES COMPOSÉES


def centrer_servos():
    """Ramène progressivement les 3 servos du robot en position centrale (90°)."""
    print("[INFO] Centrage progressif CH0, CH1, CH2 → 90°...")
    for canal in CANAUX_ROBOT:
        angle_actuel = _angles.get(canal, 90)
        cible = 90
        pas = 1 if cible > angle_actuel else -1
        for a in range(int(angle_actuel), cible + pas, pas):
            get_servo(canal).angle = a
            _angles[canal] = a
            time.sleep(0.01)
    print("[INFO] Servos centrés.")


def reset_canal(cible):
    """Remet un canal spécifique à 90°, ou tous les canaux robot si cible='all'."""
    if str(cible).lower() == 'all':
        centrer_servos()
    elif isinstance(cible, int) and cible in range(16):
        print(f"[RESET] Canal {cible} → 90°")
        set_angle(cible, 90)
    else:
        print("[ERREUR] Canal invalide. Usage : reset <0-15> ou reset all")


def afficher_info():
    """Affiche l'état de tous les servos actuellement initialisés."""
    if not _angles:
        print("[INFO] Aucun servo commandé depuis le démarrage.")
        return
    print("[INFO] État des servos :")
    for canal in sorted(_angles):
        tag = "(robot)" if canal in CANAUX_ROBOT else "(test) " if canal == CANAL_TEST else "       "
        print(f"  CH{canal:02d} {tag}  {_angles[canal]:6.1f}°")


def scan_canaux():
    """Liste les canaux ayant un objet Servo initialisé."""
    if not _servos:
        print("[SCAN] Aucun canal initialisé.")
        return
    print(f"[SCAN] Canaux initialisés : {sorted(_servos.keys())}")


def demo_robot():
    """
    Enchaîne une séquence de mouvements sur CH0, CH1, CH2 :
    chaque servo fait un balayage 45°→135°→90° avec pause entre les passes.
    """
    print("[DEMO] Début de la démonstration sur CH0, CH1, CH2...")
    positions = [45, 90, 135, 90]
    for canal in CANAUX_ROBOT:
        print(f"  [DEMO] Canal {canal}")
        for angle in positions:
            set_angle(canal, angle)
            time.sleep(0.4)
        time.sleep(0.3)
    print("[DEMO] Terminée. Servos repositionnés à 90°.")


#  BOUCLE PRINCIPALE


def main():
    centrer_servos()

    try:
        while True:
            try:
                commande = input("\ncommande> ").strip()
            except EOFError:
                break

            if not commande:
                continue

            tokens = commande.lower().split()
            cmd = tokens[0]

            try:
                # ── Quitter 
                if cmd in ('q', 'quit', 'exit'):
                    break


                # ── Test servo libre CH15 
                elif cmd == 'test':
                    test_servo_libre()

                # ── Centrage CH0/CH1/CH2 
                elif cmd == 'centre':
                    centrer_servos()

                # ── Positionnement : set <canal> <angle> 
                elif cmd == 'set':
                    if len(tokens) < 3:
                        print("[ERREUR] Usage : set <canal> <angle>")
                        print("         Exemple : set 0 90")
                        continue
                    canal = int(tokens[1])
                    angle = float(tokens[2])
                    if canal not in range(16):
                        print("[ERREUR] Canal invalide (0 à 15).")
                        continue
                    set_angle(canal, angle)

                # ── Informations sur les angles courants 
                elif cmd == 'info':
                    afficher_info()

                # ── Scan des canaux initialisés 
                elif cmd == 'scan':
                    scan_canaux()

                # ── Reset d'un canal (ou tous) à 90° 
                elif cmd == 'reset':
                    if len(tokens) < 2:
                        print("[ERREUR] Usage : reset <canal> ou reset all")
                        continue
                    arg = tokens[1]
                    cible = arg if arg == 'all' else int(arg)
                    reset_canal(cible)

                # ── Démonstration de mouvements sur CH0-CH2 
                elif cmd == 'demo':
                    demo_robot()

                else:
                    print(f"[ERREUR] Commande inconnue : '{cmd}'")

            except (ValueError, IndexError) as e:
                print(f"[ERREUR] Paramètre invalide : {e}")

    finally:
        centrer_servos()
        pca.deinit()
        print("\nAu revoir.")


if __name__ == "__main__":
    for channel in CANAUX_ROBOT:
        test_servo_libre(channel)
    main()
