import time
from lineTracking import LineTracker
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic
from threading import Thread

try:
    motor = RobotMotor()
    tracker = LineTracker()
    ultrasonic = Ultrasonic()
    servos = RobotServos()
    angle = 90
    servos.set_angle(0, angle)  # position initiale du servo
    while True :
        movement = input("Appuie sur M pour démarrer : ")
        while movement=='M' or movement=='m' :
                status = tracker.get_status()
                distance = ultrasonic.get_distance()
                tracker.print_status()
                if status['right'] == 0 and status['left'] == 0  and status['middle'] == 0:
                    angle = 90
                    servos.set_angle(0, angle)
                    motor.drive_with_ramp(30, 1, 1)
                    status = tracker.get_status()


                elif status['right'] == 0 and status['left'] == 1 and status['middle'] == 0:
                    while status['left'] != 0:
                        t1=Thread(target=servos.set_angle, args=(0, angle + 20), daemon=True)
                        t2=Thread(target=motor.drive_with_ramp, args=(20, 1, 1), daemon=True)
                        t1.start()
                        t2.start()
                        status = tracker.get_status()

                elif status['right'] == 0 and status['left'] == 1 and status['middle'] == 1:
                    t3=Thread(target=servos.set_angle, args=(0, angle - 20),daemon=True)
                    t4=Thread(target=motor.drive_with_ramp,args=(20, -1, 1),daemon=True)
                    t3.start()
                    t4.start()
                    status = tracker.get_status()


                elif status['right'] == 1 and status['left'] == 0 and status['middle'] == 0:
                    while status['left'] != 0:
                        t5=Thread(target=servos.set_angle,args=(0, angle - 20),daemon=True)
                        t6=Thread(target=motor.drive_with_ramp, args=(20, 1, 1),daemon=True)
                        t5.start()
                        t6.start()
                        status = tracker.get_status()


                elif status['right'] == 1 and status['left'] == 0 and status['middle'] == 1:
                    t7=Thread(target=servos.set_angle, args=(0, angle + 20), daemon=True)
                    t8=Thread(target=motor.drive_with_ramp, args=(20, -1, 1), daemon=True)
                    t7.start()
                    t8.start()
                    status = tracker.get_status()


                elif status['right'] == 1 and status['left'] == 1 and status['middle'] == 0:
                    while status['left'] != 0:
                        t9=Thread(target=servos.set_angle, args=(0, angle + 20), daemon=True)
                        t10=Thread(target=motor.drive_with_ramp, args=(20, 1, 1), daemon=True)
                        t9.start()
                        t10.start()
                        status = tracker.get_status()


                elif status['right'] == 1 and status['left'] == 1 and status['middle'] == 1:
                    while status['right'] != 0 or status['left'] != 0 or status['middle'] != 0:
                        angle = 90
                        servos.set_angle(0, angle)
                        motor.drive_with_ramp(20, -1, 1)
                        status = tracker.get_status()


                elif status['right'] == 0 and status['left'] == 0 and status['middle'] == 1:
                    while status['right'] != 0 or status['left'] != 0 or status['middle'] != 0:
                        angle = 90
                        servos.set_angle(0, angle)
                        motor.drive_with_ramp(20, -1, 1)
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






