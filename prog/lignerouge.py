import threading
import cv2
import numpy as np
import time
import sys
import os
from flask import Flask, Response

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


CVRun            = 1     # 1 = moteurs actifs, 0 = analyse sans bouger
linePos_1        = 330   # Hauteur de la ligne d'analyse supérieure (pixels)
linePos_2        = 410   # Hauteur de la ligne d'analyse inférieure (pixels)
turn_speed       = 80    # Vitesse en virage (0-100)
forward_speed    = 40    # Vitesse en ligne droite (0-100)
CENTER_MIN       = 270   # Borne gauche de la zone centrale
CENTER_MAX       = 370   # Borne droite de la zone centrale
findLineMove     = 1
reverse_speed    = 20    # Vitesse de marche arrière (0-100)
reverse_steer    = 39    # Angle de braquage en marche arrière (degrés)
reverse_duration = 0.4   # Durée de la marche arrière (secondes)
END_OF_LINE_TIMEOUT = 2.0  # Secondes sans ligne avant arrêt définitif


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
        self.last_turn     = 0
        self.reverse_until = 0

        # Fin de ligne
        self.line_lost_since = None   # Timestamp quand la ligne a été perdue
        self.stopped = False          # True quand le robot s'est arrêté définitivement

    def send_frame(self, frame):
        self.img_input = frame
        self._flag.set()

    def pause(self):
        self._flag.clear()

    def draw(self, frame):
        try:
            cv2.line(frame, (0, linePos_1), (640, linePos_1), (255, 128, 64), 1)
            cv2.line(frame, (0, linePos_2), (640, linePos_2), (64, 128, 255), 1)

            if self.left_1 is not None:
                cv2.line(frame, (self.left_1,  linePos_1 - 20), (self.left_1,  linePos_1 + 20), (0, 255, 0), 2)
                cv2.line(frame, (self.right_1, linePos_1 - 20), (self.right_1, linePos_1 + 20), (0, 0, 255), 2)

            if self.left_2 is not None:
                cv2.line(frame, (self.left_2,  linePos_2 - 20), (self.left_2,  linePos_2 + 20), (0, 255, 0), 2)
                cv2.line(frame, (self.right_2, linePos_2 - 20), (self.right_2, linePos_2 + 20), (0, 0, 255), 2)

            if self.center is not None:
                cy = (linePos_1 + linePos_2) // 2
                cv2.line(frame, (self.center - 15, cy), (self.center + 15, cy), (0, 0, 0), 2)
                cv2.line(frame, (self.center, cy - 15), (self.center, cy + 15), (0, 0, 0), 2)
                cv2.putText(frame, f'Centre: {self.center}px', (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            if self.stopped:
                status = "FIN DE LIGNE — ARRET"
                color = (0, 0, 255)
            elif self.center is not None:
                status = "Ligne detectee"
                color = (255, 255, 255)
            else:
                status = "Ligne perdue - MARCHE ARRIERE"
                color = (0, 165, 255)

            cv2.putText(frame, status, (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        except Exception:
            pass
        return frame

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
        # Si arrêt définitif déclenché, ne rien faire
        if self.stopped:
            move.motorStop()
            return

        if not CVRun:
            move.motorStop()
            return

        now = time.time()

        # Gestion du timeout de fin de ligne
        if self.center is None or findLineMove == 0:
            if self.line_lost_since is None:
                self.line_lost_since = now  # Démarre le chrono

            elapsed = now - self.line_lost_since

            # Fin de ligne confirmée après END_OF_LINE_TIMEOUT secondes
            if elapsed >= END_OF_LINE_TIMEOUT:
                print("🏁 Fin de ligne détectée — arrêt définitif.")
                move.motorStop()
                try:
                    scGear.moveAngle(0, 0)
                except Exception:
                    pass
                self.stopped = True
                return

            # Pendant le timeout : marche arrière
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

        elif self.center < CENTER_MIN:
            self.last_turn = -1
            scGear.moveAngle(0, 30)
            move.video_Tracking_Move(turn_speed, 1)

        else:
            self.last_turn = 0
            scGear.moveAngle(0, 0)
            move.video_Tracking_Move(forward_speed, 1)

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


# ==========================================
# GESTION DE LA CAMÉRA
# ==========================================
def init_camera():
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (640, 480), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(1)
    print("✅ Caméra démarrée.")
    return picam2

cv_thread = CVThread()

def generate():
    if HARDWARE_AVAILABLE:
        picam2 = init_camera()
    else:
        return

    cv_thread.start()

    while True:
        img = picam2.capture_array()
        if img is None:
            continue
        if not cv_thread.threading:
            cv_thread.send_frame(img.copy())
        img = cv_thread.draw(img)
        success, encoded = cv2.imencode('.jpg', img)
        if success:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + encoded.tobytes() + b'\r\n')


# ==========================================
# SERVEUR FLASK
# ==========================================
app = Flask(__name__)

@app.route('/video')
def video():
    return Response(
        generate(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/')
def index():
    return '''
    <html>
    <body style="background:black; text-align:center">
        <h2 style="color:white">Robot Camera — Suivi ligne rouge</h2>
        <img src="/video" width="640" height="480">
    </body>
    </html>
    '''


# ==========================================
# PROGRAMME PRINCIPAL
# ==========================================
if __name__ == '__main__':
    print("=== Suivi de ligne rouge — PiCar-B ===")

    if HARDWARE_AVAILABLE:
        scGear.moveAngle(2, -25)
        time.sleep(0.5)

    print("Serveur démarré sur http://10.101.2.84:5001")
    try:
        app.run(host='0.0.0.0', port=5001, threaded=True)
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
            move.destroy()
        except Exception:
            pass
        print("✅ Arrêt propre effectué.")
