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
    angle = 90
    while True :
        movement = input("Appuie sur M pour démarrer : ")
        if movement == "M":
            while True :
                motor.drive_with_ramp(20, 1, 5)
                status = tracker.get_status()
                distance = ultrasonic.get_distance()
                tracker.print_status()
                time.sleep(0.05)
                if status['right'] == 0:
                    servos.set_angle(0,angle - 20)
                if status['left'] == 0:
                    servos.set_angle(0,angle + 20)
                if distance < 200:
                    motor.stop()
                    movement = input("Envoie M pour redémarrer : ")
                    break  # sort de la surveillance
except :
    print("Fin de programme par Ctrl-C")

finally:
    ultrasonic.close()  # libère GPIO24
    motor.stop()
    servos.centrer_servos(0)
    print("Nettoyage final réalisé")






