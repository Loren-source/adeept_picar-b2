import time
from lineTracking import LineTracker
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic

try:
    motor = RobotMotor()
    tracker = LineTracker()
    ultrasonic = Ultrasonic()
    servos = RobotServos()
    angle = 98
    servos.set_angle(0, angle)

    while True:
        movement = input("Appuie sur M pour démarrer : ")

        if movement == 'M' or movement == 'm':
            motor.drive_with_ramp(30, 1, 5)

        while movement == 'M' or movement == 'm':
            status = tracker.get_status()
            distance = ultrasonic.get_distance()
            tracker.print_status()

            if ((status['right'] == 1) and (status['left'] == 1) and (status['middle'] == 1)):
                angle = 98
                servos.set_angle(0, angle)
                motor.drive_with_ramp(30, 1, 0)
                status = tracker.get_status()

            elif ((status['right'] == 1) and (status['left'] == 0) and (status['middle'] == 1)):
                servos.set_angle(0, angle + 20)
                while ((status['right'] == 1) and (status['middle'] == 1)):
                    motor.drive_with_ramp(20, 1, 0)
                    status = tracker.get_status()

            elif ((status['right'] == 1) and (status['left'] == 0) and (status['middle'] == 0)):
                servos.set_angle(0, angle - 20)
                while ((status['right'] == 1)):
                    motor.drive_with_ramp(30, -1, 0)
                    status = tracker.get_status()

            elif ((status['right'] == 0) and (status['left'] == 1) and (status['middle'] == 1)):
                servos.set_angle(0, angle + 20)
                while ((status['left'] == 1) and (status['middle'] == 1)):
                    motor.drive_with_ramp(30, 1, 0)
                    status = tracker.get_status()

            elif ((status['right'] == 0) and (status['left'] == 1) and (status['middle'] == 0)):
                servos.set_angle(0, angle - 20)
                while status['right'] == 1:
                    motor.stop()
                    motor.drive_with_ramp(30, -1, 0)
                    status = tracker.get_status()

            elif ((status['right'] == 0) and (status['left'] == 0) and (status['middle'] == 1)):
                servos.set_angle(0, angle)
                while ((status['right'] != 0) or (status['left'] != 0) or (status['middle'] != 0)):
                    angle = 98
                    motor.stop()
                    motor.drive_with_ramp(30, -1, 0)
                    status = tracker.get_status()

            if distance < 200:
                motor.stop()
                movement = input("Envoie M pour redémarrer : ")
                break  # sort de la surveillance

except KeyboardInterrupt:
    print("Fin du programme")

finally:
    ultrasonic.close()
    motor.stop()
    servos.centrer_servos(0)
    print("Nettoyage final réalisé")