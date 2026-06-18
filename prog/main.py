"""
Tâche 7 — Intégration des fonctions
Robot Adeept PiCar-B2 — MasterCamp Systèmes Embarqués

But : vérifier le fonctionnement simultané des modules logiciels précédents.
Ajouter un par un les modules, vérifier le fonctionnement, corriger si nécessaire.

Utilisation :
    python3 tache7_integration.py
    Puis entrer le numéro d'étape souhaité (1 à 7), ou 'all' pour tout enchaîner.
"""

import time


def etape_1_led_phares():
    """Tâche 1 — LEDs HAL + RGB des feux avant."""
    print("\n--- Étape 1 : LEDs phares (Tâche 1) ---")
    import switch
    switch.switchSetup()
    switch.led_rgb()
    print("Test : allumage LED1 (HAL)")
    # Adapter selon les fonctions réelles de ton switch.py (led1.on(), etc.)
    print("OK : module switch chargé sans erreur.")


def etape_2_ws2812():
    """Tâche 2 — LED WS2812."""
    print("\n--- Étape 2 : WS2812 (Tâche 2) ---")
    from Spi_WS2812 import LED
    led = LED()
    print("Test : LED 0 en rouge")
    # Adapter selon la méthode réelle de pilotage (ex: led.piloter(0, 'R', 100))
    print("OK : module Spi_WS2812 chargé et initialisé.")
    return led


def etape_3_servos():
    """Tâche 3 — Servomoteurs."""
    print("\n--- Étape 3 : Servomoteurs (Tâche 3) ---")
    from servo import RobotServos
    servos = RobotServos()
    servos.set_angle(0, 90)
    time.sleep(0.5)
    print("OK : servo canal 0 positionné à 90°.")
    return servos


def etape_4_moteur():
    """Tâche 4 — Moteur DC."""
    print("\n--- Étape 4 : Moteur DC (Tâche 4) ---")
    from motor import RobotMotor
    motor = RobotMotor()
    print("Test : avance brève à faible vitesse")
    motor.drive_with_ramp(20, 1, 0.5)
    time.sleep(0.5)
    motor.set_motor(1, 0)
    print("OK : module motor fonctionnel.")
    return motor


def etape_5_ultrason():
    """Tâche 5 — Capteur ultrason."""
    print("\n--- Étape 5 : Capteur ultrason (Tâche 5) ---")
    from ultra import Ultrasonic
    ultrasonic = Ultrasonic()
    distance = ultrasonic.get_distance()
    print(f"Distance mesurée : {distance:.0f} mm")
    print("OK : module ultra fonctionnel.")
    return ultrasonic


def etape_6_ligne():
    """Tâche 6 — Suivi de ligne."""
    print("\n--- Étape 6 : Suivi de ligne (Tâche 6) ---")
    from lineTracking import LineTracker
    tracker = LineTracker()
    tracker.print_status()
    print("OK : module lineTracking fonctionnel.")
    return tracker


def etape_7_lumiere():
    """Tâche 8 (lumière) — intégrée ici car liée aux LDR avant le suivi complet."""
    print("\n--- Étape 7 : Capteurs de lumière LDR ---")
    # ATTENTION : adapte le nom du fichier/module selon ce que tu as réellement
    # enregistré (le code source ADS7830 que tu as ne précise pas de nom de fichier).
    from ldr import ADS7830   # <-- renomme si ton fichier s'appelle différemment
    adc = ADS7830()
    g = adc.analogRead(1)
    d = adc.analogRead(2)
    print(f"LDR gauche={g}  droite={d}")
    print("OK : module ldr fonctionnel.")
    return adc


def integration_complete():
    """
    Vérifie le fonctionnement SIMULTANÉ de tous les modules :
    avance + lecture distance + lecture LDR + direction servo, en boucle courte.
    """
    print("\n=== INTÉGRATION COMPLÈTE : tous les modules ensemble ===")

    from motor import RobotMotor
    from servo import RobotServos
    from ultra import Ultrasonic
    from ldr import ADS7830          # adapte le nom si besoin
    from lineTracking import LineTracker
    from Spi_WS2812 import LED

    motor      = RobotMotor()
    servos     = RobotServos()
    ultrasonic = Ultrasonic()
    adc        = ADS7830()
    tracker    = LineTracker()
    led        = LED()

    servos.set_angle(0, 90)
    motor.drive_with_ramp(20, 1, 0.5)

    for i in range(10):
        distance = ultrasonic.get_distance()
        ldr_g    = adc.analogRead(1)
        ldr_d    = adc.analogRead(2)
        ligne    = tracker.get_status()

        print(f"[{i}] dist={distance:.0f}mm | LDR G={ldr_g} D={ldr_d} | ligne={ligne}")

        if distance < 200:
            print("    -> Obstacle détecté pendant l'intégration !")
            motor.stop()
            break

        time.sleep(0.2)

    motor.set_motor(1, 0)
    motor.stop_feux()
    servos.set_angle(0, 90)
    print("\nOK : tous les modules ont fonctionné simultanément sans erreur.")


ETAPES = {
    "1": etape_1_led_phares,
    "2": etape_2_ws2812,
    "3": etape_3_servos,
    "4": etape_4_moteur,
    "5": etape_5_ultrason,
    "6": etape_6_ligne,
    "7": etape_7_lumiere,
}


if __name__ == "__main__":
    choix = input("\nÉtape à tester : ").strip().lower()

    try:
        if choix == "all":
            for num in sorted(ETAPES.keys()):
                ETAPES[num]()
                input("  -> Entrée pour passer à l'étape suivante...")
            integration_complete()
        elif choix in ETAPES:
            ETAPES[choix]()
        else:
            print("Choix invalide.")

    except KeyboardInterrupt:
        print("\nInterrompu par l'utilisateur.")
    except Exception as e:
        print(f"\nERREUR pendant l'intégration : {e}")
        print("-> Corrige le module concerné avant de continuer.")
