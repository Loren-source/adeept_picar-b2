from servo import RobotServos
import time

servos = RobotServos()

servos.set_angle(1, 150)
time.sleep(2)

servos.set_angle(1, 97)
time.sleep(2)

servos.set_angle(1, 40)
time.sleep(2)
