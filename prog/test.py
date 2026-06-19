import time
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic
from lineTracking import LineTracker

robot = RobotMotor()
servos = RobotServos()
ultra = Ultrasonic()
tracker = LineTracker()

servos.set_angle(0, 127)

try:
    while True:
        distance = ultra.get_distance()
        capteurs = tracker.get_status()
        robot.set_motor(1, 30)
        time.sleep(0.05)
except KeyboardInterrupt:
    robot.stopper()
    servos.set_angle(0, 97)
