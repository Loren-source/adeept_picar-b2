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
            motor.drive_with_ramp(20, 1, 5)
            distance1 = ultrasonic.get_distance()
            print(f"Distance : {distance1:.2f} mm")
            time.sleep(0.05)

            status = tracker.get_status()
            if status['right'] == 0:
                motor.stop()
                servos.set_angle(0,angle - 10)
                motor.drive_with_ramp(20,1, 1)
            if status['left'] == 0:
                motor.stop()
                servos.set_angle(0,angle + 10)
                motor.drive_with_ramp(20,1, 1)

        while True:  # surveillance continue
            distance = ultrasonic.get_distance()
            print(f"Distance : {distance:.2f} mm")
            time.sleep(0.05)

            if distance < 200:
                motor.stop()
                movement = input("Envoie M pour redémarrer : ")
                break  # sort de la surveillance
except :
    print("Fin de programme par Ctrl-C")

finally:
    ultrasonic.close()  # libère GPIO24
    motor.stop()
    print("Nettoyage final réalisé")






