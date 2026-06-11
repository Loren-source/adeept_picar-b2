#!/usr/bin/env python3

import time
import smbus
from gpiozero import TonalBuzzer
from motor import RobotMotor
from ultra import Ultrasonic


SEUIL_SUIVI    = 20
SEUIL_OBSTACLE = 200
DUREE_RECUL    = 1.5
VITESSE_AV     = 30
VITESSE_RECUL  = 20
RAMPE          = 1


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


class SuiviLumiere:
    def __init__(self, motor, ultrasonic, capteur, buzzer):
        self.motor      = motor
        self.ultrasonic = ultrasonic
        self.capteur    = capteur
        self.buzzer     = buzzer

    def gerer_obstacle(self):
        self.motor.stop()
        time.sleep(1)
        self.motor.drive_with_ramp(VITESSE_RECUL, -1, RAMPE)
        self.buzzer.bip_bip()
        time.sleep(DUREE_RECUL)
        self.motor.stop()
        time.sleep(2)

    def suivre(self):
        ldr_g = self.capteur.lire_gauche()
        ldr_d = self.capteur.lire_droite()
        diff  = ldr_g - ldr_d
        print(f"LDR gauche={ldr_g:3d}  droite={ldr_d:3d}  diff={diff:+4d}")

        if abs(diff) < SEUIL_SUIVI:
            self.motor.drive_with_ramp(VITESSE_AV, 1, RAMPE)
        elif diff > 0:
            self.motor.set_motor(1, VITESSE_AV // 2)
        else:
            self.motor.set_motor(1, VITESSE_AV)

    def boucle(self):
        while True:
            distance = self.ultrasonic.get_distance()
            print(f"Distance : {distance:.0f} mm")

            if distance < SEUIL_OBSTACLE:
                self.gerer_obstacle()
                self.motor.drive_with_ramp(VITESSE_AV, 1, RAMPE)

            self.suivre()
            time.sleep(0.05)


class Robot:
    def __init__(self):
        self.motor      = RobotMotor()
        self.ultrasonic = Ultrasonic()
        self.capteur    = CapteurLumiere()
        self.buzzer     = Buzzer()
        self.suivi      = SuiviLumiere(
            self.motor,
            self.ultrasonic,
            self.capteur,
            self.buzzer
        )

    def run(self):
        while True:
            cmd = input("M pour démarrer, A pour arrêter : ").strip().upper()

            if cmd == "M":
                print("[INFO] Démarrage suivi de lumière...")
                self.motor.drive_with_ramp(VITESSE_AV, 1, RAMPE)
                self.suivi.boucle()

            elif cmd in ("A", "a"):
                self.motor.stop()
                print("[INFO] Arrêt manuel.")

            else:
                print("[ERREUR] Commande inconnue.")

    def destroy(self):
        self.motor.stop()
        self.ultrasonic.close()
        self.buzzer.stop()
        print("Nettoyage final réalisé.")


if __name__ == "__main__":
    robot = Robot()
    try:
        robot.run()
    except KeyboardInterrupt:
        print("\nFin de programme.")
    finally:
        robot.destroy()
