from motor import RobotMotor
from servo import RobotServos
import time

robot = RobotMotor()
servos = RobotServos()

servos.set_angle(0, 127)
time.sleep(0.5)

robot.set_motor(1, 50)
time.sleep(2)
robot.stopper()
