#!/usr/bin/env python3

import time
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685


class RobotServos:

    PCA_ADDRESS  = 0x5f
    PWM_FREQ     = 50
    MIN_PULSE    = 500
    MAX_PULSE    = 2400
    ACTUATION    = 180
    ANGLE_MIN    = 0
    ANGLE_MAX    = 180
    CANAL_TEST   = 15
    CANAUX_ROBOT = [0, 1, 2]

    def __init__(self):
        i2c = busio.I2C(SCL, SDA)
        self.pca = PCA9685(i2c, address=self.PCA_ADDRESS)
        self.pca.frequency = self.PWM_FREQ
        self._servos: dict[int, servo.Servo] = {}
        self._angles: dict[int, float] = {}

    # ── Accès aux objets servo 

    def get_servo(self, canal: int) -> servo.Servo:
        """Retourne l'objet Servo du canal, en le créant si besoin."""
        if canal not in self._servos:
            self._servos[canal] = servo.Servo(
                self.pca.channels[canal],
                min_pulse=self.MIN_PULSE,
                max_pulse=self.MAX_PULSE,
                actuation_range=self.ACTUATION
            )
        return self._servos[canal]

    # ── Commandes de base 

    def set_angle(self, canal: int, angle: float):
        """Positionne le servo du canal à l'angle demandé (clampé à [0°, 180°])."""
        angle_safe = max(self.ANGLE_MIN, min(self.ANGLE_MAX, angle))
        if angle_safe != angle:
            print(f"[SECURITE] Angle {angle}° corrigé → {angle_safe}°")
        self.get_servo(canal).angle = angle_safe
        self._angles[canal] = angle_safe
        print(f"[CH{canal:02d}] → {angle_safe}°")

    def test_servo_libre(self, canal: int = None):
        """Aller-retour 0°→179°→0° sur le canal donné (défaut : CH15)."""
        if canal is None:
            canal = self.CANAL_TEST
        print(f"[TEST] Canal {canal} – aller-retour 0°→179°→0°")
        s = self.get_servo(canal)
        for i in range(180):
            s.angle = i
            time.sleep(0.01)
        time.sleep(0.5)
        for i in range(180):
            s.angle = 180 - i
            time.sleep(0.01)
        time.sleep(0.5)
        print("[TEST] Terminé.")

    # ── Commandes composées 

    def centrer_servos(self):
        """Ramène progressivement CH0, CH1, CH2 à 90°."""
        print("[INFO] Centrage progressif CH0, CH1, CH2 → 90°...")
        for canal in self.CANAUX_ROBOT:
            angle_actuel = self._angles.get(canal, 90)
            cible = 90
            pas = 1 if cible > angle_actuel else -1
            for a in range(int(angle_actuel), cible + pas, pas):
                self.get_servo(canal).angle = a
                self._angles[canal] = a
                time.sleep(0.02)
        print("[INFO] Servos centrés.")

    def reset_canal(self, cible):
        """Remet un canal à 90°, ou tous les canaux robot si cible='all'."""
        if str(cible).lower() == 'all':
            self.centrer_servos()
        elif isinstance(cible, int) and cible in range(16):
            print(f"[RESET] Canal {cible} → 90°")
            self.set_angle(cible, 90)
        else:
            print("[ERREUR] Canal invalide. Usage : reset <0-15> ou reset all")

    def afficher_info(self):
        """Affiche l'angle actuel de chaque servo commandé."""
        if not self._angles:
            print("[INFO] Aucun servo commandé depuis le démarrage.")
            return
        print("[INFO] État des servos :")
        for canal in sorted(self._angles):
            tag = "(robot)" if canal in self.CANAUX_ROBOT else "(test) " if canal == self.CANAL_TEST else "       "
            print(f"  CH{canal:02d} {tag}  {self._angles[canal]:6.1f}°")

    def scan_canaux(self):
        """Liste les canaux ayant un objet Servo initialisé."""
        if not self._servos:
            print("[SCAN] Aucun canal initialisé.")
            return
        print(f"[SCAN] Canaux initialisés : {sorted(self._servos.keys())}")

    def demo_robot(self):
        """Séquence de mouvements 45°→90°→135°→90° sur CH0, CH1, CH2."""
        print("[DEMO] Début de la démonstration sur CH0, CH1, CH2...")
        positions = [45, 90, 135, 90]
        for canal in self.CANAUX_ROBOT:
            print(f"  [DEMO] Canal {canal}")
            for angle in positions:
                self.set_angle(canal, angle)
                time.sleep(0.4)
            time.sleep(0.3)
        print("[DEMO] Terminée. Servos repositionnés à 90°.")

    def fermer(self):
        """Centrage de sécurité et libération de la carte."""
        self.centrer_servos()
        self.pca.deinit()
        print("\nAu revoir.")

    

    def run(self):
        """Lance la boucle de commandes interactive."""
        self.centrer_servos()
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
                    if cmd in ('q', 'quit', 'exit'):
                        break

                    elif cmd == 'test':
                        self.test_servo_libre()

                    elif cmd == 'centre':
                        self.centrer_servos()

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
                        self.set_angle(canal, angle)

                    elif cmd == 'info':
                        self.afficher_info()

                    elif cmd == 'scan':
                        self.scan_canaux()

                    elif cmd == 'reset':
                        if len(tokens) < 2:
                            print("[ERREUR] Usage : reset <canal> ou reset all")
                            continue
                        arg = tokens[1]
                        cible = arg if arg == 'all' else int(arg)
                        self.reset_canal(cible)

                    elif cmd == 'demo':
                        self.demo_robot()

                    else:
                        print(f"[ERREUR] Commande inconnue : '{cmd}'")

                except (ValueError, IndexError) as e:
                    print(f"[ERREUR] Paramètre invalide : {e}")

        finally:
            self.fermer()


if __name__ == "__main__":
    robot = RobotServos()
    for channel in robot.CANAUX_ROBOT:
        robot.test_servo_libre(channel)
    robot.run()
