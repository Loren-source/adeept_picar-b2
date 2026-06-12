import time
import sys
import select
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic
from ldr import ADS7830

DISTANCE_OBSTACLE = 200  
ANGLE_CENTRE         = 90 

def lire_clavier():
    rlist, _, _ = select.select([sys.stdin], [], [], 0)
    if rlist:
        return sys.stdin.readline().strip()
    return None

try:
    motor      = RobotMotor()
    servos     = RobotServos()
    ultrasonic = Ultrasonic()
    adc        = ADS7830()
    servos.set_angle(0, ANGLE_CENTRE)
    en_marche = False

    print("M pour démarrer | A pour arrêter")

    while True:
        if en_marche:
            cmd = lire_clavier()
        else:
            cmd = input("\nCommande (M / A) : ").strip()

        if cmd == "M":
            print("Départ en marche avant...")
            motor.stop_feux()
            motor.drive_with_ramp(25, 1, 1)
            en_marche = True

        elif cmd in ("A", "a"):
            print("Arrêt manuel.")
            motor.set_motor(1, 0)
            motor.stop_feux()
            en_marche = False

        if en_marche:
            distance   = ultrasonic.get_distance()
            ldr_gauche = adc.analogRead(1)
            ldr_droite = adc.analogRead(2)
            print(f"Distance : {distance:.0f} mm | LDR G={ldr_gauche} D={ldr_droite}")

            if distance < DISTANCE_OBSTACLE:
                motor.stop()                         
                print(f"Obstacle à {distance:.0f} mm ! Arrêt + feux de détresse.")
                en_marche = False

                time.sleep(1)                        

                print("Recul avec bips.")
                motor.drive_with_ramp(20, -1, 0.5)   # recul avec rampe
                time.sleep(1)                        
                for _ in range(3):                    # bips
                    motor.set_motor(-1, 10)
                    time.sleep(0.2)
                    motor.set_motor(-1, 0)
                    time.sleep(0.2)

                motor.set_motor(-1, 0)
                motor.stop_feux()

                print("Pause 2 s avant reprise.")
                time.sleep(2)

                print("Reprise du suivi de lumière.")
                motor.drive_with_ramp(25, 1, 1)
                en_marche = True

            else:
                diff = ldr_gauche - ldr_droite
                if diff > 20:
                    servos.set_angle(0, ANGLE_CENTRE + 45)
                    print("Tourne gauche")
                elif diff < -20:
                    servos.set_angle(0, ANGLE_CENTRE - 45)
                    print("Tourne droite")
                else:
                    servos.set_angle(0, ANGLE_CENTRE)
                    print("Tout droit")

                motor.set_motor(1, 25)

        time.sleep(0.05)

except KeyboardInterrupt:
    print("\nFin de programme ")

finally:
    motor.set_motor(1, 0)
    motor.stop_feux()
    servos.set_angle(0, ANGLE_CENTRE)
    print("Nettoyage final réalisé")
