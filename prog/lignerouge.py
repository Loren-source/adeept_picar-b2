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

# ==========================================
# IMPORT DU MATÉRIEL (avec fallback simulation)
# ==========================================
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

# ==========================================
# CLASSES DE SIMULATION (si pas de matériel)
# ==========================================
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

# ==========================================
# PARAMÈTRES GLOBAUX
# ==========================================
CVRun         = 1    # 1 = moteurs actifs, 0 = analyse sans bouger

# -- Vitesses --
forward_speed = 30   # Vitesse en ligne droite (0-100) | ↓ si rate les virages
turn_speed    = 50   # Vitesse en virage      (0-100) | ↑ si tourne pas assez vite

# -- Détection --
linePos_1  = 280     # Ligne d'analyse haute (pixels) | ↓ = regarde plus loin = anticipe mieux
linePos_2  = 420     # Ligne d'analyse basse (pixels)
CENTER_MIN = 280     # Seuil gauche (pixels)  | ↑ = réagit plus tôt en virage
CENTER_MAX = 360     # Seuil droit  (pixels)  | ↓ = réagit plus tôt en virage

# -- Braquage --
steer_angle  = 30    # Angle de braquage en virage (degrés) | ↑ si tourne pas assez

findLineMove = 1

# ==========================================
# INITIALISATION DU MATÉRIEL
# ==========================================
if HARDWARE_AVAILABLE:
    scGear = RPIservo.ServoCtrl()
    scGear.moveInit()
    move.setup()
else:
    scGear = DummyGear()
    move = DummyMove()

# ==========================================
# THREAD DE VISION
# ==========================================
class CVThread(threading.Thread):

    def __init__(self):
        super().__init__(daemon=True)
        self._flag   = threading.Event()
        self._flag.clear()

        self.img_input = None
        self.threading = False

        self.left_1  = None
        self.right_1 = None
        self.left_2  = None
        self.right_2 = None
        self.center  = None

    def send_frame(self, frame):
        self.img_input = frame
        self._flag.set()

    def pause(self):
        self._flag.clear()

    # --- Dessin des indicateurs visuels ---
    def draw(self, frame):
        try:
            # Lignes d'analyse horizontales
            cv2.line(frame, (0, linePos_1), (640, linePos_1), (255, 128, 64), 1)
            cv2.line(frame, (0, linePos_2), (640, linePos_2), (64, 128, 255), 1)

            # Marqueurs bords de ligne
            if self.left_1 is not None:
                cv2.line(frame, (self.left_1,  linePos_1 - 20), (self.left_1,  linePos_1 + 20), (0, 255, 0), 2)
                cv2.line(frame, (self.right_1, linePos_1 - 20), (self.right_1, linePos_1 + 20), (0, 0, 255), 2)
            if self.left_2 is not None:
                cv2.line(frame, (self.left_2,  linePos_2 - 20), (self.left_2,  linePos_2 + 20), (0, 255, 0), 2)
                cv2.line(frame, (self.right_2, linePos_2 - 20), (self.right_2, linePos_2 + 20), (0, 0, 255), 2)

            # Croix sur le centre
            if self.center is not None:
                cy = (linePos_1 + linePos_2) // 2
                cv2.line(frame, (self.center - 15, cy), (self.center + 15, cy), (0, 0, 0), 2)
                cv2.line(frame, (self.center, cy - 15), (self.center, cy + 15), (0, 0, 0), 2)
                cv2.putText(frame, f'Centre: {self.center}px', (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            # Zones de décision
            cv2.line(frame, (CENTER_MIN, 0), (CENTER_MIN, 480), (0, 200, 0), 1)
            cv2.line(frame, (CENTER_MAX, 0), (CENTER_MAX, 480), (0, 200, 0), 1)

            status = "Suivi OK" if self.center is not None else "Ligne perdue - STOP"
            color  = (0, 255, 0) if self.center is not None else (0, 0, 255)
            cv2.putText(frame, status, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        except Exception:
            pass
        return frame

    # --- Détection de la ligne rouge ---
    def _detect_line(self, frame):
        global findLineMove

        hsv   = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, np.array([0,   70, 50]), np.array([10,  255, 255]))
        mask2 = cv2.inRange(hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
        mask  = cv2.bitwise_or(mask1, mask2)
        mask  = cv2.erode(mask,  None, iterations=2)
        mask  = cv2.dilate(mask, None, iterations=2)

        row1 = mask[linePos_1]
        row2 = mask[linePos_2]
        idx1 = np.where(row1 == 255)[0]
        idx2 = np.where(row2 == 255)[0]

        def valid(idx):
            return idx.size > 0 and abs(int(idx[-1]) - int(idx[0])) <= 500

        v1, v2 = valid(idx1), valid(idx2)

        if not v1 and not v2:
            findLineMove = 0
            self.left_1 = self.right_1 = None
            self.left_2 = self.right_2 = None
            self.center = None
            return

        findLineMove = 1
        centers = []

        if v1:
            self.left_1  = int(idx1[0])
            self.right_1 = int(idx1[-1])
            centers.append((self.left_1 + self.right_1) // 2)
        else:
            self.left_1 = self.right_1 = None

        if v2:
            self.left_2  = int(idx2[0])
            self.right_2 = int(idx2[-1])
            centers.append((self.left_2 + self.right_2) // 2)
        else:
            self.left_2 = self.right_2 = None

        self.center = sum(centers) // len(centers)

    # --- Contrôle des moteurs ---
    def _control_motors(self):
        if not CVRun:
            move.motorStop()
            return

        if self.center is None or findLineMove == 0:
            # Ligne perdue → arrêt
            move.motorStop()
            return

        if self.center > CENTER_MAX:
            # Ligne à droite → tourner à droite
            scGear.moveAngle(0, -steer_angle)
            move.video_Tracking_Move(turn_speed, 1)

        elif self.center < CENTER_MIN:
            # Ligne à gauche → tourner à gauche
            scGear.moveAngle(0, steer_angle)
            move.video_Tracking_Move(turn_speed, 1)

        else:
            # Ligne centrée → avancer tout droit
            scGear.moveAngle(0, 0)
            move.video_Tracking_Move(forward_speed, 1)

    # --- Boucle principale ---
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

def frames(picam2, cv_thread):
    while True:
        img = picam2.capture_array()
        if img is None:
            continue
        if not cv_thread.threading:
            cv_thread.send_frame(img.copy())
        img = cv_thread.draw(img)
        success, encoded = cv2.imencode('.jpg', img)
        if success:
            yield encoded.tobytes()

# ==========================================
# PROGRAMME PRINCIPAL
# ==========================================
if __name__ == '__main__':
    print("=== Suivi de ligne rouge — PiCar-B ===")

    if HARDWARE_AVAILABLE:
        scGear.moveAngle(2, -15)  # Caméra vers le sol
        time.sleep(0.5)

    cv_thread = CVThread()
    cv_thread.start()
    print("✅ Thread de vision démarré.")

    if HARDWARE_AVAILABLE:
        picam2 = init_camera()
    else:
        print("⚠️  Mode simulation — webcam USB utilisée.")
        picam2 = cv2.VideoCapture(0)

    print("🚗 Démarrage. Ctrl+C pour arrêter.\n")

    try:
        if HARDWARE_AVAILABLE:
            for frame in frames(picam2, cv_thread):
                time.sleep(0.03)
        else:
            while True:
                ret, img = picam2.read()
                if not ret:
                    break
                if not cv_thread.threading:
                    cv_thread.send_frame(img.copy())
                img = cv_thread.draw(img)
                cv2.imshow("Suivi ligne rouge [SIMULATION]", img)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                time.sleep(0.03)

    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé.")

    finally:
        try:
            move.motorStop()
        except Exception:
            pass
        if HARDWARE_AVAILABLE:
            picam2.stop()
        else:
            picam2.release()
            cv2.destroyAllWindows()
        print("✅ Arrêt propre.")
