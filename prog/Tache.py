#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tâche 11 : Suivi de ligne (ligne noire sur fond blanc)
Robot Adeept PiCar-B2

Protocole série :
  'M' ou 'm' -> Départ (marche avant + suivi de ligne)
  'A' ou 'a' -> Arrêt immédiat manuel

Comportement :
  - Suit une ligne noire (~2-3 cm) sur fond blanc
  - Arrêt si obstacle détecté à moins de DISTANCE_OBSTACLE cm (défaut 20 cm)
  - Arrêt si 'A'/'a' reçu sur le port série
"""

import serial
import time
import RPi.GPIO as GPIO

# ──────────────────────────────────────────────
# CONFIGURATION MATÉRIELLE
# ──────────────────────────────────────────────

# Moteurs (L298N ou similaire)
# Moteur gauche
MOTOR_LEFT_IN1  = 20   # GPIO BCM
MOTOR_LEFT_IN2  = 21
MOTOR_LEFT_ENA  = 16   # PWM

# Moteur droit
MOTOR_RIGHT_IN1 = 19
MOTOR_RIGHT_IN2 = 26
MOTOR_RIGHT_ENB = 13   # PWM

# Capteurs de ligne infrarouge (3 capteurs : gauche, centre, droit)
# Sortie digitale : 0 = ligne noire détectée, 1 = fond blanc
IR_LEFT   = 12   # GPIO BCM
IR_CENTER = 11
IR_RIGHT  = 10

# Capteur ultrasonique HC-SR04
TRIG_PIN = 24
ECHO_PIN = 25

# ──────────────────────────────────────────────
# PARAMÈTRES
# ──────────────────────────────────────────────

DISTANCE_OBSTACLE = 20      # cm — arrêt si obstacle plus proche
VITESSE_NORMALE   = 60      # % PWM (0-100) vitesse de base
VITESSE_VIRAGE    = 40      # % PWM pour la roue intérieure en virage
PORT_SERIE        = '/dev/ttyUSB0'
BAUD_RATE         = 9600
FREQUENCE_PWM     = 1000    # Hz

# ──────────────────────────────────────────────
# INITIALISATION GPIO
# ──────────────────────────────────────────────

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Moteurs
GPIO.setup(MOTOR_LEFT_IN1,  GPIO.OUT)
GPIO.setup(MOTOR_LEFT_IN2,  GPIO.OUT)
GPIO.setup(MOTOR_LEFT_ENA,  GPIO.OUT)
GPIO.setup(MOTOR_RIGHT_IN1, GPIO.OUT)
GPIO.setup(MOTOR_RIGHT_IN2, GPIO.OUT)
GPIO.setup(MOTOR_RIGHT_ENB, GPIO.OUT)

pwm_left  = GPIO.PWM(MOTOR_LEFT_ENA,  FREQUENCE_PWM)
pwm_right = GPIO.PWM(MOTOR_RIGHT_ENB, FREQUENCE_PWM)
pwm_left.start(0)
pwm_right.start(0)

# Capteurs IR
GPIO.setup(IR_LEFT,   GPIO.IN)
GPIO.setup(IR_CENTER, GPIO.IN)
GPIO.setup(IR_RIGHT,  GPIO.IN)

# Ultrason
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)
GPIO.output(TRIG_PIN, False)
time.sleep(0.05)  # stabilisation


# ──────────────────────────────────────────────
# FONCTIONS MOTEURS
# ──────────────────────────────────────────────

def moteur_gauche(vitesse, avant=True):
    """Pilote le moteur gauche. vitesse : 0-100."""
    GPIO.output(MOTOR_LEFT_IN1, GPIO.HIGH if avant else GPIO.LOW)
    GPIO.output(MOTOR_LEFT_IN2, GPIO.LOW  if avant else GPIO.HIGH)
    pwm_left.ChangeDutyCycle(vitesse)

def moteur_droit(vitesse, avant=True):
    """Pilote le moteur droit. vitesse : 0-100."""
    GPIO.output(MOTOR_RIGHT_IN1, GPIO.HIGH if avant else GPIO.LOW)
    GPIO.output(MOTOR_RIGHT_IN2, GPIO.LOW  if avant else GPIO.HIGH)
    pwm_right.ChangeDutyCycle(vitesse)

def avancer(vitesse=VITESSE_NORMALE):
    moteur_gauche(vitesse, avant=True)
    moteur_droit(vitesse,  avant=True)

def virer_gauche():
    """Virage gauche : ralentir (ou stopper) roue gauche."""
    moteur_gauche(VITESSE_VIRAGE, avant=True)
    moteur_droit(VITESSE_NORMALE, avant=True)

def virer_droite():
    """Virage droit : ralentir (ou stopper) roue droite."""
    moteur_gauche(VITESSE_NORMALE, avant=True)
    moteur_droit(VITESSE_VIRAGE,   avant=True)

def arreter():
    moteur_gauche(0)
    moteur_droit(0)


# ──────────────────────────────────────────────
# CAPTEUR ULTRASONIQUE
# ──────────────────────────────────────────────

def mesurer_distance():
    """Retourne la distance en cm mesurée par le HC-SR04."""
    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)   # impulsion 10 µs
    GPIO.output(TRIG_PIN, False)

    debut  = time.time()
    fin    = time.time()

    timeout = time.time() + 0.04  # 40 ms max
    while GPIO.input(ECHO_PIN) == 0:
        debut = time.time()
        if debut > timeout:
            return 999  # pas d'écho → obstacle absent ou erreur

    timeout = time.time() + 0.04
    while GPIO.input(ECHO_PIN) == 1:
        fin = time.time()
        if fin > timeout:
            return 999

    duree    = fin - debut
    distance = (duree * 34300) / 2   # vitesse son 343 m/s → cm
    return round(distance, 1)


# ──────────────────────────────────────────────
# CAPTEURS DE LIGNE
# ──────────────────────────────────────────────

def lire_capteurs_ligne():
    """
    Retourne un tuple (gauche, centre, droit).
    True  = ligne noire détectée sous ce capteur.
    False = fond blanc.
    (Logique inversée : GPIO.LOW = noir pour la plupart des modules IR)
    """
    g = (GPIO.input(IR_LEFT)   == GPIO.LOW)
    c = (GPIO.input(IR_CENTER) == GPIO.LOW)
    d = (GPIO.input(IR_RIGHT)  == GPIO.LOW)
    return g, c, d


# ──────────────────────────────────────────────
# LOGIQUE DE SUIVI DE LIGNE
# ──────────────────────────────────────────────

def suivre_ligne():
    """
    Algorithme de suivi basé sur 3 capteurs IR.

    Table de décision :
    ┌───────┬────────┬───────┬──────────────────────────┐
    │ Gche  │ Centre │ Droite│ Action                   │
    ├───────┼────────┼───────┼──────────────────────────┤
    │   0   │   1    │   0   │ Tout droit               │
    │   0   │   1    │   1   │ Virer légèrement à droite│
    │   0   │   0    │   1   │ Virer fort à droite      │
    │   1   │   1    │   0   │ Virer légèrement à gauche│
    │   1   │   0    │   0   │ Virer fort à gauche      │
    │   1   │   1    │   1   │ Tout droit (intersection)│
    │   0   │   0    │   0   │ Tout droit (hors ligne→  │
    │       │        │       │ conserver cap)           │
    └───────┴────────┴───────┴──────────────────────────┘
    """
    g, c, d = lire_capteurs_ligne()

    if not g and c and not d:
        # Ligne bien centrée
        avancer()
    elif not g and c and d:
        # Ligne légèrement à droite
        virer_droite()
    elif not g and not c and d:
        # Ligne fortement à droite
        moteur_gauche(VITESSE_NORMALE, avant=True)
        moteur_droit(0)
    elif g and c and not d:
        # Ligne légèrement à gauche
        virer_gauche()
    elif g and not c and not d:
        # Ligne fortement à gauche
        moteur_gauche(0)
        moteur_droit(VITESSE_NORMALE, avant=True)
    elif g and c and d:
        # Intersection ou fin de ligne — continuer tout droit
        avancer()
    else:
        # Aucun capteur actif (entre deux corrections) — maintenir cap
        avancer()


# ──────────────────────────────────────────────
# BOUCLE PRINCIPALE
# ──────────────────────────────────────────────

def main():
    print("Tâche 11 – Suivi de ligne")
    print(f"  Distance d'arrêt obstacle : {DISTANCE_OBSTACLE} cm")
    print(f"  Port série : {PORT_SERIE} @ {BAUD_RATE} baud")
    print("Envoyez 'M' pour démarrer, 'A' pour arrêter.")

    try:
        ser = serial.Serial(PORT_SERIE, BAUD_RATE, timeout=0)
    except serial.SerialException as e:
        print(f"[ERREUR] Impossible d'ouvrir {PORT_SERIE} : {e}")
        GPIO.cleanup()
        return

    en_marche = False

    try:
        while True:
            # ── Lecture commande série (non bloquant) ──
            if ser.in_waiting > 0:
                commande = ser.read(1).decode('ascii', errors='ignore').strip()
                if commande in ('M', 'm'):
                    print("[INFO] Départ reçu → suivi de ligne activé")
                    en_marche = True
                elif commande in ('A', 'a'):
                    print("[INFO] Arrêt manuel reçu")
                    en_marche = False
                    arreter()

            # ── Comportement robot ──
            if en_marche:
                # 1. Vérification obstacle
                distance = mesurer_distance()
                if distance <= DISTANCE_OBSTACLE:
                    print(f"[INFO] Obstacle à {distance} cm → arrêt")
                    arreter()
                    en_marche = False
                else:
                    # 2. Suivi de ligne
                    suivre_ligne()

            time.sleep(0.02)   # 50 Hz — laisse le temps aux capteurs

    except KeyboardInterrupt:
        print("\n[INFO] Interruption clavier")

    finally:
        arreter()
        ser.close()
        pwm_left.stop()
        pwm_right.stop()
        GPIO.cleanup()
        print("[INFO] Nettoyage GPIO effectué. Fin du programme.")


if __name__ == '__main__':
    main()
