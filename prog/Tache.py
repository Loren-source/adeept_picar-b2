#!/usr/bin/env python3
import time
import smbus
import threading                          # CORRECTION 2 : ajout threading
from gpiozero import TonalBuzzer
from gpiozero import LED as GPIO_LED      # CORRECTION 3 : ajout phares RGB
from motor import RobotMotor
from ultra import Ultrasonic
from servo import RobotServos             # CORRECTION 4 : ajout servo

# ==========================================
# Constantes de configuration
# ==========================================
SEUIL_SUIVI    = 20
SEUIL_OBSTACLE = 200
DUREE_RECUL    = 1.5
VITESSE_AV     = 30
VITESSE_RECUL  = 20
RAMPE          = 1

# ==========================================
# Classes Matérielles (Drivers / Capteurs)
# ==========================================
class CapteurLumiere:
    def __init__(self):
        self.bus     = smbus.SMBus(1)
        self.adresse = 0x48
        self.cmd     = 0x84

    def lire(self, chn):
        return self.bus.read_byte_data(
            self.adresse,
            self.cmd | (((chn << 2 | chn >> 1) & 0x07) << 4)
        )

    def lire_gauche(self):
        return self.lire(1)

    def lire_droite(self):
        return self.lire(2)


class Buzzer:
    def __init__(self):
        self.tb = TonalBuzzer(18)

    def bip_bip(self):
        for _ in range(2):
            self.tb.play("A4")
            time.sleep(0.2)
            self.tb.stop()
            time.sleep(0.2)

    def stop(self):
        self.tb.stop()


class Phares:
    # CORRECTION 3 : classe Phares ajoutée
    def __init__(self):
        self.r_rouge = GPIO_LED(1)
        self.l_rouge = GPIO_LED(13)

    def rouge(self):
        self.r_rouge.off()   # logique inversée
        self.l_rouge.off()

    def off(self):
        self.r_rouge.on()    # logique inversée
        self.l_rouge.on()


# ==========================================
# Logique de comportement (Intelligence)
# ==========================================
class SuiviLumiere:
    def __init__(self, motor, servos, ultrasonic, capteur, buzzer, phares):  # CORRECTION 4 : ajout servos et phares
        self.motor      = motor
        self.servos     = servos          # CORRECTION 4
        self.ultrasonic = ultrasonic
        self.capteur    = capteur
        self.buzzer     = buzzer
        self.phares     = phares          # CORRECTION 3
        self._actif     = False           # CORRECTION 2 : flag d'arrêt

    def gerer_obstacle(self):
        self.motor.stop()                 # active WS2812 automatiquement
        self.phares.rouge()               # CORRECTION 3 : phares RGB
        time.sleep(1)
        self.motor.drive_with_ramp(VITESSE_RECUL, -1, RAMPE)
        self.buzzer.bip_bip()
        time.sleep(DUREE_RECUL)
        self.motor.stop()
        time.sleep(2)
        self.phares.off()                 # CORRECTION 3 : éteindre phares

    def suivre(self):
        ldr_g = self.capteur.lire_gauche()
        ldr_d = self.capteur.lire_droite()
        diff  = ldr_g - ldr_d
        print(f"LDR gauche={ldr_g:3d}  droite={ldr_d:3d}  diff={diff:+4d}")
        
        if abs(diff) < SEUIL_SUIVI:
            self.servos.set_angle(0, 98)                # CORRECTION 4 : tout droit
            self.motor.set_motor(1, VITESSE_AV)         # CORRECTION 5 : set_motor au lieu de drive_with_ramp
        elif diff > 0:
            self.servos.set_angle(0, 60)                # CORRECTION 4 : tourner gauche
            self.motor.set_motor(1, VITESSE_AV)
        else:
            self.servos.set_angle(0, 130)               # CORRECTION 4 : tourner droite
            self.motor.set_motor(1, VITESSE_AV)

    def boucle(self):
        self._actif = True                              # CORRECTION 2
        while self._actif:                              # CORRECTION 2 : while _actif au lieu de while True
            distance = self.ultrasonic.get_distance()
            print(f"Distance : {distance:.0f} mm")
            
            if distance < SEUIL_OBSTACLE:
                self.gerer_obstacle()
                if self._actif:                         # CORRECTION 2 : vérifier avant de reprendre
                    self.motor.drive_with_ramp(VITESSE_AV, 1, RAMPE)
            
            self.suivre()
            time.sleep(0.05)

    def arreter(self):
        self._actif = False                             # CORRECTION 2


# ==========================================
# Orchestrateur Principal (Robot)
# ==========================================
class Robot:
    def __init__(self):
        self.motor      = RobotMotor()
        self.servos     = RobotServos()                 # CORRECTION 4
        self.ultrasonic = Ultrasonic()
        self.capteur    = CapteurLumiere()
        self.buzzer     = Buzzer()
        self.phares     = Phares()                      # CORRECTION 3
        
        self.suivi      = SuiviLumiere(
            self.motor,
            self.servos,                                # CORRECTION 4
            self.ultrasonic,
            self.capteur,
            self.buzzer,
            self.phares                                 # CORRECTION 3
        )
        self.servos.set_angle(0, 98)                    # étalonnage direction
        self._thread = None

    def run(self):
        while True:
            cmd = input("M pour démarrer, A pour arrêter : ").strip().upper()
            if cmd == "M":
                print("[INFO] Démarrage suivi de lumière...")
                self.motor.drive_with_ramp(VITESSE_AV, 1, RAMPE)
                # CORRECTION 2 : boucle dans un thread
                self._thread = threading.Thread(target=self.suivi.boucle, daemon=True)
                self._thread.start()
            elif cmd in ("A", "a"):
                self.suivi.arreter()                    # CORRECTION 2 : stoppe via flag
                self.motor.stop()
                self.phares.off()                       # CORRECTION 3
                print("[INFO] Arrêt manuel.")
            else:
                print("[ERREUR] Commande inconnue.")

    def destroy(self):
        self.suivi.arreter()
        self.motor.stop()
        self.phares.off()                               # CORRECTION 3
        self.buzzer.stop()
        # CORRECTION 1 : supprimé ultrasonic.close()
        print("Nettoyage final réalisé.")


# ==========================================
# Point d'entrée
# ==========================================
if __name__ == "__main__":
    robot = Robot()
    try:
        robot.run()
    except KeyboardInterrupt:
        print("\nFin de programme.")
    finally:
        robot.destroy()
