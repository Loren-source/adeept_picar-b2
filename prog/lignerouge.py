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
CVRun         = 1       # 1 = moteurs actifs, 0 = analyse sans bouger
linePos_1     = 330     # Hauteur de la ligne d'analyse supérieure (pixels)
linePos_2     = 410     # Hauteur de la ligne d'analyse inférieure (pixels)
turn_speed    = 70      # Vitesse en virage (0-100) — augmenter si le robot ne tourne pas assez vite
forward_speed = 50      # Vitesse en ligne droite (0-100) — réduire si le robot rate les virages
CENTER_MIN    = 290     # Borne gauche de la zone centrale — rapprocher du centre = détecte les virages plus tôt
CENTER_MAX    = 360     # Borne droite de la zone centrale — rapprocher du centre = détecte les virages plus tôt
findLineMove  = 1       # 1 = ligne détectée, 0 = ligne perdue
reverse_speed    = 40   # Vitesse de marche arrière (0-100)
reverse_steer    = 39   # Angle de braquage en marche arrière (degrés)
reverse_duration = 0.4 # Durée de la marche arrière (secondes) avant de reprendre

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
# THREAD DE VISION : DÉTECTION LIGNE ROUGE
# ==========================================
class CVThread(threading.Thread):

    def __init__(self):
        super().__init__(daemon=True)
        self._flag    = threading.Event()
        self._flag.clear()

        self.img_input   = None
        self.threading   = False

        # Positions détectées sur les deux lignes d'analyse
        self.left_1  = None
        self.right_1 = None
        self.left_2  = None
        self.right_2 = None
        self.center  = None  # Centre global de la ligne rouge
        self.last_turn    = 0    # Dernière direction connue : -1=gauche, 0=droit, 1=droite
        self.reverse_until = 0   # Timestamp jusqu'auquel on reste en marche arrière

    # --- Interface publique ---
    def send_frame(self, frame):
        """Envoie une nouvelle image à analyser."""
        self.img_input = frame
        self._flag.set()

    def pause(self):
        self._flag.clear()

    # --- Dessin des éléments sur l'image ---
    def draw(self, frame):
        """Superpose les indicateurs visuels sur l'image."""
        try:
            # Lignes d'analyse horizontales
            cv2.line(frame, (0, linePos_1), (640, linePos_1), (255, 128, 64), 1)
            cv2.line(frame, (0, linePos_2), (640, linePos_2), (64, 128, 255), 1)

            # Marqueurs gauche/droite sur ligne 1
            if self.left_1 is not None:
                cv2.line(frame, (self.left_1,  linePos_1 - 20), (self.left_1,  linePos_1 + 20), (0, 255, 0), 2)
                cv2.line(frame, (self.right_1, linePos_1 - 20), (self.right_1, linePos_1 + 20), (0, 0, 255), 2)

            # Marqueurs gauche/droite sur ligne 2
            if self.left_2 is not None:
                cv2.line(frame, (self.left_2,  linePos_2 - 20), (self.left_2,  linePos_2 + 20), (0, 255, 0), 2)
                cv2.line(frame, (self.right_2, linePos_2 - 20), (self.right_2, linePos_2 + 20), (0, 0, 255), 2)

            # Croix sur le centre détecté
            if self.center is not None:
                cy = (linePos_1 + linePos_2) // 2
                cv2.line(frame, (self.center - 15, cy), (self.center + 15, cy), (0, 0, 0), 2)
                cv2.line(frame, (self.center, cy - 15), (self.center, cy + 15), (0, 0, 0), 2)
                # Affichage de la position
                cv2.putText(frame, f'Centre: {self.center}px', (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            status = "Ligne detectee" if self.center is not None else "Ligne perdue - MARCHE ARRIERE"
            cv2.putText(frame, status, (10, 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        except Exception:
            pass
        return frame

    # --- Détection de la ligne rouge ---
    def _detect_line(self, frame):
        """
        Convertit en HSV et crée un masque pour le rouge.
        Le rouge occupe deux plages dans l'espace HSV :
          - Plage basse : 0–10°
          - Plage haute : 170–180°
        """
        global findLineMove

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        mask1 = cv2.inRange(hsv, np.array([0,   70, 50]), np.array([10,  255, 255]))
        mask2 = cv2.inRange(hsv, np.array([170, 70, 50]), np.array([180, 255, 255]))
        mask  = cv2.bitwise_or(mask1, mask2)

        # Nettoyage morphologique (supprime le bruit)
        mask = cv2.erode(mask,  None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        # Extraction des pixels rouges sur les deux lignes d'analyse
        row1 = mask[linePos_1]
        row2 = mask[linePos_2]

        idx1 = np.where(row1 == 255)[0]
        idx2 = np.where(row2 == 255)[0]

        # Vérification que la ligne n'est pas trop large (= ligne perdue / intersection)
        def line_valid(idx):
            if idx.size == 0:
                return False
            if abs(int(idx[-1]) - int(idx[0])) > 500:
                return False  # Trop large → probablement une intersection
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

        # Calcul des centres sur chaque ligne
        centers = []
        if valid1 and idx1.size > 0:
            self.left_1  = int(idx1[0])
            self.right_1 = int(idx1[-1])
            centers.append((self.left_1 + self.right_1) // 2)
        else:
            self.left_1 = self.right_1 = None

        if valid2 and idx2.size > 0:
            self.left_2  = int(idx2[0])
            self.right_2 = int(idx2[-1])
            centers.append((self.left_2 + self.right_2) // 2)
        else:
            self.left_2 = self.right_2 = None

        self.center = sum(centers) // len(centers)

    # --- Contrôle des moteurs selon la position ---
    def _control_motors(self):
        """
        Oriente et avance le robot selon 3 cas :
          CAS 1 : Timer de marche arrière actif  → on continue de reculer
          CAS 2 : Ligne perdue, timer non armé   → on arme le timer et on recule
          CAS 3 : Ligne retrouvée                → suivi normal avant
        """
        if not CVRun:
            move.motorStop()
            return

        now = time.time()

        # CAS 1 : marche arrière en cours (timer actif)
        if now < self.reverse_until:
            if self.last_turn == 1:
                scGear.moveAngle(0, -reverse_steer)
            elif self.last_turn == -1:
                scGear.moveAngle(0, reverse_steer)
            else:
                scGear.moveAngle(0, 0)
            move.video_Tracking_Move(reverse_speed, -1)
            return

        # CAS 2 : ligne perdue, armer le timer et démarrer la marche arrière
        if self.center is None or findLineMove == 0:
            self.reverse_until = now + reverse_duration
            if self.last_turn == 1:
                scGear.moveAngle(0, -reverse_steer)
            elif self.last_turn == -1:
                scGear.moveAngle(0, reverse_steer)
            else:
                scGear.moveAngle(0, 0)
            move.video_Tracking_Move(reverse_speed, -1)
            return

        # CAS 3 : ligne retrouvée → suivi normal
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

    # --- Boucle principale du thread ---
    def run(self):
        while True:
            self._flag.wait()          # Attente d'une nouvelle image
            if self.img_input is None:
                continue
            self.threading = True
            self._detect_line(self.img_input)
            self._control_motors()
            self.threading = False
            self.pause()               # Attend la prochaine image

# ==========================================
# GESTION DE LA CAMÉRA
# ==========================================
def init_camera():
    """Initialise et configure la Picamera2."""
    picam2 = Picamera2()
    config = picam2.create_preview_configuration(
        main={"size": (640, 480), "format": "RGB888"}
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(1)  # Laisse la caméra se stabiliser
    print("✅ Caméra démarrée.")
    return picam2

def frames(picam2, cv_thread):
    """Générateur : capture les images et les envoie au thread CV."""
    while True:
        img = picam2.capture_array()
        if img is None:
            continue

        # Envoyer l'image au thread de vision s'il est disponible
        if not cv_thread.threading:
            cv_thread.send_frame(img.copy())

        # Dessiner les indicateurs sur l'image
        img = cv_thread.draw(img)

        # Encodage JPEG pour le flux
        success, encoded = cv2.imencode('.jpg', img)
        if success:
            yield encoded.tobytes()

# ==========================================
# PROGRAMME PRINCIPAL
# ==========================================
if __name__ == '__main__':
    print("=== Suivi de ligne rouge — PiCar-B ===")

    # Orientation de la caméra vers le sol
    if HARDWARE_AVAILABLE:
        scGear.moveAngle(2, -15)
        time.sleep(0.5)

    # Lancement du thread de vision
    cv_thread = CVThread()
    cv_thread.start()
    print("✅ Thread de vision démarré.")

    # Initialisation caméra
    if HARDWARE_AVAILABLE:
        picam2 = init_camera()
    else:
        print("⚠️  Pas de caméra physique. Utilise une source vidéo de test.")
        picam2 = cv2.VideoCapture(0)  # Webcam USB pour les tests

    print("🚗 Démarrage du suivi de ligne rouge. Ctrl+C pour arrêter.\n")

    try:
        if HARDWARE_AVAILABLE:
            for frame in frames(picam2, cv_thread):
                time.sleep(0.03)  # ~30 fps
        else:
            # Mode test avec webcam USB
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
        print("\n🛑 Arrêt demandé par l'utilisateur.")

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
        print("✅ Arrêt propre effectué.")
