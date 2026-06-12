import time
from lineTracking import LineTracker
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic

#  Paramètres ajustables 
DISTANCE_ARRET = 200  # mm (20 cm par défaut)
ANGLE_CENTRE = 98
ANGLE_LEGER = 25      # à calibrer
ANGLE_FORT  = 45      # à calibrer

try:
    motor = RobotMotor()
    tracker = LineTracker()
    ultrasonic = Ultrasonic()
    servos = RobotServos()

    servos.set_angle(0, ANGLE_CENTRE)

    #  Calibration rapide au démarrage 
    print("=== Calibration des angles ===")
    print("Entre un angle de correction à tester (ex: 25), ou 'ok' pour démarrer")

    while True:
        val = input("Angle à tester (ou 'ok') : ")
        if val.lower() == 'ok':
            break
        try:
            angle = int(val)
            print(f"  → Test correction gauche : CENTRE + {angle}")
            servos.set_angle(0, ANGLE_CENTRE + angle)
            time.sleep(2)
            print(f"  → Test correction droite : CENTRE - {angle}")
            servos.set_angle(0, ANGLE_CENTRE - angle)
            time.sleep(2)
            servos.set_angle(0, ANGLE_CENTRE)
            print("  → Recentré")

            confirmer = input(f"  Utiliser {angle} comme ANGLE_FORT ? (o/n) : ")
            if confirmer.lower() == 'o':
                ANGLE_FORT = angle
                ANGLE_LEGER = max(10, angle // 2)
                print(f"  ✓ ANGLE_FORT={ANGLE_FORT}, ANGLE_LEGER={ANGLE_LEGER}")
        except ValueError:
            print("Entre un nombre entier ou 'ok'")

    # === Boucle principale de suivi de ligne ===
    while True:
        movement = input("\nAppuie sur M pour démarrer (A pour arrêter) : ")
        if movement not in ('M', 'm'):
            continue

        print("Démarrage du suivi de ligne...")

        while True:
            status = tracker.get_status()
            tracker.print_status()
            distance = ultrasonic.get_distance()

            l = status['left']
            m = status['middle']
            r = status['right']

            # --- Arrêt obstacle ---
            if distance < DISTANCE_ARRET:
                motor.stop()
                print(f"Obstacle détecté à {distance} mm, arrêt.")
                break

            # --- Suivi de ligne ---
            if l==0 and m==0 and r==0:
                servos.set_angle(0, ANGLE_CENTRE)
                motor.backward_slow()
                print("Aucune ligne, recule pour chercher")

            elif l==0 and m==1 and r==0:
                servos.set_angle(0, ANGLE_CENTRE)
                motor.forward_slow()
                print("Centre : avance droit")

            elif l==1 and m==0 and r==0:
                servos.set_angle(0, ANGLE_CENTRE + ANGLE_LEGER)
                motor.forward_slow()
                print("Gauche légère")

            elif l==0 and m==0 and r==1:
                servos.set_angle(0, ANGLE_CENTRE - ANGLE_LEGER)
                motor.forward_slow()
                print("Droite légère")

            elif l==1 and m==1 and r==0:
                servos.set_angle(0, ANGLE_CENTRE + ANGLE_FORT)
                motor.forward_slow()
                print("Virage gauche")

            elif l==0 and m==1 and r==1:
                servos.set_angle(0, ANGLE_CENTRE - ANGLE_FORT)
                motor.forward_slow()
                print("Virage droite")

            elif l==1 and m==0 and r==1:
                servos.set_angle(0, ANGLE_CENTRE)
                motor.forward_slow()
                print("Intersection, tout droit")

            elif l==1 and m==1 and r==1:
                motor.stop()
                servos.set_angle(0, ANGLE_CENTRE)
                print("Fin de ligne, arrêt")
                break

            else:
                servos.set_angle(0, ANGLE_CENTRE)
                motor.backward_slow()
                print("Situation inattendue, recule")

            time.sleep(0.05)


except KeyboardInterrupt:
    motor.stop()
    servos.set_angle(0, ANGLE_CENTRE)
    print("\nArrêt propre.")
           
