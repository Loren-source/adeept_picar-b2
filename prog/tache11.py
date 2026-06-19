from motor import RobotMotor
from ultra import Ultrasonic
from lineTracking import LineTracker
from servo import RobotServos

robot  = RobotMotor()
ultra  = Ultrasonic()
tracker = LineTracker()
servos = RobotServos()

def braquer(angle):
    servos.set_angle(0, angle)
def corriger_gauche():
    braquer(60)
    robot.set_motor(1, 30) 
def corriger_droite():
    braquer(120)
    robot.set_motor(1, 30)
def corriger_centrer():
    braquer(90)
    robot.set_motor(1, 50)

actif = False
try:
    while True:
        commande = input()
        if commande == 'M':
            actif = True
            robot.avancer()
        elif commande == 'A':
            actif = False
            robot.stopper()
        
        if actif:
            distance = ultra.get_distance()
            if distance < 200:
                robot.stop()
                actif = False
            else:
                capteurs = tracker.get_status()
                l = capteurs['left']
                m = capteurs['middle']
                r = capteurs['right']

                if l == 1 and m == 0 and r == 1:
                    corriger_centrer()
                elif l == 1 and m == 1 and r == 0:
                    corriger_droite()
                elif l == 0 and m == 1 and r == 1:
                    corriger_gauche()
                elif l == 0 and m == 0 and r == 0:
                    corriger_centrer()
                elif l == 1 and m == 1 and r == 1:
                    robot.stopper()

except KeyboardInterrupt:
    print('Fin de programme')

finally:
    robot.stopper()
    servos.set_angle(0, 90)
    print('Nettoyage final réalisé')
