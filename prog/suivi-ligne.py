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
            last_angle = angle
            angle = 98
            servos.set_angle(0, angle)
            if ((status['left']== 0) and (status['middle'] == 0) and (status['right'] == 0)):
                servos.set_angle(0, last_angle)
                servos.set_angle(1, last_angle)
                motor.backward_slow()
                print("pas de ligne -> tout droit")
            elif ((status['left']== 1) and (status['middle'] == 0) and (status['right'] == 0)):
                servos.set_angle(0, angle + 60)
                servos.set_angle(1, angle + 60)
                motor.forward_slow()
                print("blanc a gauche -> tourne a droite")
            elif ((status['left']== 0) and (status['middle'] == 0) and (status['right'] == 1)):
                servos.set_angle(0, angle - 60)
                servos.set_angle(1, angle - 60)
                motor.forward_slow()
                print("blanc a droite tourne a gauche")
            elif ((status['left']== 0) and (status['middle'] == 1) and (status['right'] == 0)):
                motor.forward_slow()
                print("imporbable -> tout droit")
            elif ((status['left']== 1) and (status['middle'] == 1) and (status['right'] == 0)):
                servos.set_angle(0, angle - 60)
                servos.set_angle(1, angle - 60)
                motor.forward_slow()
                print("blanc a gauche et au centre -> tourne a droite")
            elif ((status['left']== 0) and (status['middle'] == 1) and (status['right'] == 1)):
                servos.set_angle(0, angle + 60)
                servos.set_angle(1, angle + 60)
                motor.forward_slow()
                print("blacn a droite et au centre -> tourne a gauche")
            elif ((status['left']== 1) and (status['middle'] == 0) and (status['right'] == 1)):
                motor.forward_slow()
                print("gauche et droite -> tout droit")
            elif ((status['left']== 1) and (status['middle'] == 1) and (status['right'] == 1)):
                motor.stop()
                motor.forward_slow()
                print("ligne -> recul")
            else :
                motor.backward_slow()
                print("Situation inattendue, recule lentement")
            if distance < 200:
                motor.stop()
                movement = input("Envoie M pour redémarrer : ")
                break

except KeyboardInterrupt:
    motor.stop()
    servos.fermer(0)
    print("Nettoyage final réalisé")
    print("Fin du programme")
