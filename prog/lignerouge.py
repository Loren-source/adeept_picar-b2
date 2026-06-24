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
linePos_1     = 340     # Hauteur de la ligne d'analyse supérieure (pixels)
linePos_2     = 420     # Hauteur de la ligne d'analyse inférieure (pixels)
turn_speed    = 50      # Vitesse en virage (0-100) — augmenter si le robot ne tourne pas assez vite
forward_speed = 30      # Vitesse en ligne droite (0-100) — réduire si le robot rate les virages
CENTER_MIN    = 280     # Borne gauche de la zone centrale — rapprocher du centre = détecte les virages plus tôt
CENTER_MAX    = 360     # Borne droite de la zone centrale — rapprocher du centre = détecte les virages plus tôt
findLineMove  = 1       # 1 = ligne détectée, 0 = ligne perdue
reverse_speed    = 30   # Vitesse de marche arrière (0-100)
reverse_steer    = 50   # Angle de braquage après le recul (degrés)
reverse_duration = 0.3  # Durée du recul (secondes)

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
        self.last_turn   = 0     # Dernière direction connue : -1=gauche, 0=droit, 1=droite
        self.in_recovery = False # True pendant la séquence de récupération

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

    # --- Séquence de récupération quand la ligne est perdue ---
    def _recovery_sequence(self):
        """
        Séquence en 4 étapes quand la ligne est perdue :
          ETAPE 1 : Reculer roues droites (reverse_duration secondes)
          ETAPE 2 : S'arrêter et scanner l'image pour trouver la ligne
          ETAPE 3 : Braquer les roues dans la bonne direction (steer_duration secondes)
          ETAPE 4 : Avancer → retour au suivi normal
        """
        # ETAPE 1 : reculer roues droites
        move.motorStop()
        scGear.moveAngle(0, 0)
        time.sleep(0.1)
        move.video_Tracking_Move(reverse_speed, -1)
        time.sleep(reverse_duration)
        move.motorStop()
        time.sleep(0.2)  # Pause pour stabiliser la caméra

        # ETAPE 2 : scanner l'image — attendre une frame fraîche
        self._flag.clear()
        self._flag.wait(timeout=0.5)
        scan_center = self.center  # Centre détecté après recul

        # ETAPE 3 : braquer dans la bonne direction
        if scan_center is not None:
            # La ligne est visible → braquer vers elle
            if scan_center > 320:
                steer_angle = -reverse_steer   # Ligne à droite
            else:
                steer_angle = reverse_steer    # Ligne à gauche
        else:
            # Ligne toujours invisible → utiliser la dernière direction connue
            if self.last_turn == 1:
                steer_angle = -reverse_steer
            elif self.last_turn == -1:
                steer_angle = reverse_steer
            else:
                steer_angle = 0

        scGear.moveAngle(0, steer_angle)
        time.sleep(0.15)  # Laisse le servo se positionner

        # ETAPE 4 : avancer avec ce braquage
        move.video_Tracking_Move(forward_speed, 1)
        time.sleep(0.4)   # Avance braqué pour revenir sur la ligne
        move.motorStop()

        # Réinitialisation : retour au suivi normal
        self.in_recovery = False

    # --- Contrôle des moteurs selon la position ---
    def _control_motors(self):
        """
        Suivi normal de la ligne.
        Si la ligne est perdue, déclenche _recovery_sequence() dans un thread séparé.
        """
        if not CVRun:
            move.motorStop()
            return

        # Ligne perdue et pas déjà en récupération → lancer la séquence
        if (self.center is None or findLineMove == 0) and not self.in_recovery:
            self.in_recovery = True
            t = threading.Thread(target=self._recovery_sequence, daemon=True)
            t.start()
            return

        # Déjà en récupération → ne rien faire, laisser le thread finir
        if self.in_recovery:
            return

        # Suivi normal
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
