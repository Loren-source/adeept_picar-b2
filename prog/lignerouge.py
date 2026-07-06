
import threading
import cv2
import numpy as np
import time
import sys
import os

# Forcer Python à chercher les modules locaux du robot
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)


try:
    import RPIservo
    import move
    from picamera2 import Picamera2
    import libcamera
    HARDWARE_AVAILABLE = True
    print("✅ Matériel détecté : RPIservo, move, Picamera2")
except ImportError as e:
    HARDWARE_AVAILABLE = False
    print(f"⚠️  Mode simulation (matériel absent) : {e}")


class DummyGear:
    def moveAngle(self, servo_id, angle):
        print(f"[SIM] Servo {servo_id} → {angle}°")
    def stopWiggle(self):
        pass
    def moveInit(self):
        pass

class DummyMove:
    @staticmethod
    def setup():
        pass
    @staticmethod
    def video_Tracking_Move(speed, direction):
        print(f"[SIM] Moteurs → vitesse={speed}, direction={direction}")
    @staticmethod
    def motorStop():
        print("[SIM] Moteurs arrêtés")
    @staticmethod
    def destroy():
        print("[SIM] Libération des ressources moteurs")


CVRun               = 1      # 1 = moteurs actifs, 0 = analyse sans bouger
linePos_1           = 330    # Hauteur de la ligne d'analyse supérieure (pixels)
linePos_2           = 410    # Hauteur de la ligne d'analyse inférieure (pixels)
turn_speed          = 80     # Vitesse en virage (0-100)
forward_speed       = 40     # Vitesse en ligne droite (0-100)
CENTER_MIN          = 270    # Borne gauche de la zone centrale
CENTER_MAX          = 370    # Borne droite de la zone centrale
findLineMove        = 1
reverse_speed       = 20     # Vitesse de marche arrière (0-100)
reverse_steer       = 39     # Angle de braquage en marche arrière (degrés)
reverse_duration    = 0.4    # Durée de la marche arrière (secondes)
END_OF_LINE_TIMEOUT = 2.0    # Secondes sans ligne avant arrêt définitif


if HARDWARE_AVAILABLE:
    scGear = RPIservo.ServoCtrl()
    scGear.moveInit()
    move.setup()
else:
    scGear = DummyGear()
    move = DummyMove()


class CVThread(threading.Thread):

    def __init__(self):
        super().__init__(daemon=True)
        self._flag = threading.Event()
        self._flag.clear()

        self.img_input = None
        self.threading = False

        self.left_1  = None
        self.right_1 = None
        self.left_2  = None
        self.right_2 = None
        self.center  = None
        self.last_turn      = 0
        self.reverse_until  = 0
        self.line_lost_since = None
        self.stopped        = False

    def send_frame(self, frame):
        self.img_input = frame
        self._flag.set()

    def pause(self):
        self._flag.clear()

    def _detect_line(self, frame):
        global findLineMove

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0,   70, 50]), np.array([10,  255, 255]))
        mask2 = cv2.inRange(hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
        mask  = cv2.bitwise_or(mask1, mask2)
        mask  = cv2.erode(mask,  None, iterations=2)
        mask  = cv2.dilate(mask, None, iterations=2)

        row1 = mask[linePos_1]
        row2 = mask[linePos_2]
        idx1 = np.where(row1 == 255)[0]
        idx2 = np.where(row2 == 255)[0]

        def line_valid(idx):
            if idx.size == 0:
                return False
            if abs(int(idx[-1]) - int(idx[0])) > 500:
                return False
            return True

        valid1 = line_valid(idx1)
        valid2 = line_valid(idx2)

        if not valid1 and not valid2:
            findLineMove = 0
            self.left_1 = self.right_1 = None
            self.left_2 = self.right_2 = None
            self.center = None
            return

        findLineMove = 1
        centers = []

        if valid1:
            self.left_1  = int(idx1[0])
            self.right_1 = int(idx1[-1])
            centers.append((self.left_1 + self.right_1) // 2)
        else:
            self.left_1 = self.right_1 = None

        if valid2:
            self.left_2  = int(idx2[0])
            self.right_2 = int(idx2[-1])
            centers.append((self.left_2 + self.right_2) // 2)
        else:
            self.left_2 = self.right_2 = None

        self.center = sum(centers) // len(centers)

    def _control_motors(self):
        if self.stopped:
            move.motorStop()
            return

        if not CVRun:
            move.motorStop()
            return

        now = time.time()

        if self.center is None or findLineMove == 0:
            if self.line_lost_since is None:
                self.line_lost_since = now

            elapsed = now - self.line_lost_since

            # Fin de ligne confirmée
            if elapsed >= END_OF_LINE_TIMEOUT:
                print("🏁 Fin de ligne détectée — arrêt définitif.")
                move.motorStop()
                try:
                    scGear.moveAngle(0, 0)
                except Exception:
                    pass
                self.stopped = True
                return

            # Marche arrière pendant le timeout
            if now < self.reverse_until:
                if self.last_turn == 1:
                    scGear.moveAngle(0, -reverse_steer)
                elif self.last_turn == -1:
                    scGear.moveAngle(0, reverse_steer)
                else:
                    scGear.moveAngle(0, 0)
                move.video_Tracking_Move(reverse_speed, -1)
                return

            self.reverse_until = now + reverse_duration
            if self.last_turn == 1:
                scGear.moveAngle(0, -reverse_steer)
            elif self.last_turn == -1:
                scGear.moveAngle(0, reverse_steer)
            else:
                scGear.moveAngle(0, 0)
            move.video_Tracking_Move(reverse_speed, -1)
            return

        # Ligne retrouvée — reset du chrono
        self.line_lost_since = None
        self.reverse_until = 0

        if self.center > CENTER_MAX:
            self.last_turn = 1
            scGear.moveAngle(0, -30)
            move.video_Tracking_Move(turn_speed, 1)
            print(f"➡️  Tourne droite (centre={self.center})")

        elif self.center < CENTER_MIN:
            self.last_turn = -1
            scGear.moveAngle(0, 30)
            move.video_Tracking_Move(turn_speed, 1)
            print(f"⬅️  Tourne gauche (centre={self.center})")

        else:
            self.last_turn = 0
            scGear.moveAngle(0, 0)
            move.video_Tracking_Move(forward_speed, 1)
            print(f"⬆️  Tout droit (centre={self.center})")

    def run(self):
        while True:
            self._flag.wait()
            if self.img_input is None:
                continue
            self.threading = True
            self._detect_line(self.img_input)
            self._control_motors()
            self.threading = False
            self.pause()
    def stop(self):
    self.stopped = True


# ==========================================
# PROGRAMME PRINCIPAL
# ==========================================
if __name__ == '__main__':
    print("=== Suivi de ligne rouge — PiCar-B ===")

    if HARDWARE_AVAILABLE:
        scGear.moveAngle(2, -25)
        time.sleep(0.5)

    cv_thread = CVThread()
    cv_thread.start()
    print("✅ Thread de vision démarré.")

    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (640, 480), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(1)
    print("✅ Caméra démarrée.")
    print("🚗 Suivi en cours... Ctrl+C pour arrêter.\n")

    try:
        while not cv_thread.stopped:
            img = picam2.capture_array()
            if img is None:
                continue
            if not cv_thread.threading:
                cv_thread.send_frame(img.copy())
            time.sleep(0.03)

        print("🏁 Robot arrêté en fin de ligne.")

    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé par l'utilisateur.")

    finally:
        try:
            move.motorStop()
        except Exception:
            pass
        try:
            scGear.moveAngle(0, 0)
        except Exception:
            pass
        try:
            picam2.stop()
        except Exception:
            pass
        try:
            move.destroy()
        except Exception:
            pass
        print("✅ Arrêt propre effectué.")
