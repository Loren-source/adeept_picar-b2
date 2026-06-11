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
        while movement == 'M' or 'm' :
            status = tracker.get_status()
            tracker.print_status()
            distance = ultrasonic.get_distance()
            angle = 98
            servos.set_angle(0, angle)  # réinitialise l'angle à chaque boucle
            if ((status['left']== 0) and (status['middle'] == 0) and (status['right'] == 0)):
                motor.forward_slow()
            elif ((status['left']== 1) and (status['middle'] == 0) and (status['right'] == 0)):
                servos.set_angle(0, angle + 25)
                motor.forward_slow()
            elif ((status['left']== 0) and (status['middle'] == 0) and (status['right'] == 1)):
                servos.set_angle(0, angle - 25)
                motor.forward_slow()
            elif ((status['left']== 0) and (status['middle'] == 1) and (status['right'] == 0)):
                motor.forward_slow()
            elif ((status['left']== 1) and (status['middle'] == 1) and (status['right'] == 0)):
                servos.set_angle(0, angle - 25)
                motor.backward_slow()
            elif ((status['left']== 0) and (status['middle'] == 1) and (status['right'] == 1)):
                servos.set_angle(0, angle + 25)
                motor.backward_slow()
            elif ((status['left']== 1) and (status['middle'] == 0) and (status['right'] == 1)):
                motor.forward_slow()
            elif ((status['left']== 1) and (status['middle'] == 1) and (status['right'] == 1)):
                angle = 98
                servos.set_angle(0, angle)
                motor.backward_slow()
            if distance < 200:
                motor.stop()
                movement = input("Envoie M pour redémarrer : ")
                break

except KeyboardInterrupt:
    ultrasonic.close()
    motor.stop()
    servos.centrer_servos(0)
    print("Nettoyage final réalisé")
    print("Fin du programme")
