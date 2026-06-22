from servo import RobotServos
import time

servos=RobotServos()

print("Centre 97")
servos.set_angle(0,97)
time.sleep(3)

print("Test 125")
servos.set_angle(0,125)
time.sleep(5)

print("Test 70")
servos.set_angle(0,70)
time.sleep(5)

print("Retour centre")
servos.set_angle(0,97)
