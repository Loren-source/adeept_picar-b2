
import threading
import cv2
import numpy as np
import datetime
import time
import imutils
import sys
import os

# Forcer Python à regarder dans le dossier local du script pour trouver RPIservo et move
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Gestion des imports matériels réels (RPIservo, move, picamera2)
try:
    import RPIservo
    import move
    from picamera2 import Picamera2  # Version moderne pour Raspberry Pi OS (Bookworm/Bullseye)
    import libcamera
    print("Matériel détecté et initialisé avec succès.")
except ImportError as e:
    print(f"Mode simulation ou dépendance manquante : {e}")

# CLASSE VIRTUELLE POUR S'AFFRANCHIR DU FICHIER KALMAN_FILTER.PY MANQUANT
class DummyKalman:
    def __init__(self, *args): 
        pass
    def kalman(self, val): 
        return val

# Variables globales de configuration
APPMode = 'none'
colorUpper = np.array([10, 255, 255])
colorLower = np.array([0, 0, 0])
CVRun = 1
linePos_1 = 340      # Hauteur de la ligne d'analyse supérieure
linePos_2 = 420      # Hauteur de la ligne d'analyse inférieure
lineColorSet = 255   # Par défaut à 255 pour le masque blanc
frameRender = 1
Threshold = 80
findLineMove = 1
tracking_servo_status = 0
FLCV_Status = 0
turn_speed = 40
ImgIsNone = 0
hflip = False
vflip = False

class CVThread(threading.Thread):
    font = cv2.FONT_HERSHEY_SIMPLEX

    # Utilisation de la classe virtuelle pour stabiliser sans dépendance externe
    kalman_filter_X = DummyKalman()
    kalman_filter_Y = DummyKalman()
    P_direction = -1
    T_direction = -1
    P_servo = 1 
    T_servo = 2 
    P_anglePos = 0
    T_anglePos = 0
    cameraDiagonalW = 64
    cameraDiagonalH = 48
    videoW = 640
    videoH = 480
    Y_lock = 0
    X_lock = 0
    tor = 17

    # Initialisation sécurisée du matériel si disponible
    try:
        scGear = RPIservo.ServoCtrl()
        scGear.moveInit()
        move.setup()
        hardware_available = True
    except NameError:
        print("Avertissement : RPIservo ou move indisponible. Utilisation du mode virtuel.")
        hardware_available = False
        class DummyGear:
            def moveAngle(self, id, angle): pass
            def stopWiggle(self): pass
        scGear = DummyGear()

    def __init__(self, *args, **kwargs):
        self.CVThreading = 0
        self.CVMode = 'none'
        self.imgCV = None

        self.mov_x = None
        self.mov_y = None
        self.mov_w = None
        self.mov_h = None

        self.radius = 0
        self.box_x = None
        self.box_y = None
        self.drawing = 0

        self.findColorDetection = 0

        self.left_Pos1 = None
        self.right_Pos1 = None
        self.center_Pos1 = None

        self.left_Pos2 = None
        self.right_Pos2 = None
        self.center_Pos2 = None

        self.center = None
        
        self.tracking_servo_left = None
        self.tracking_servo_left_mark = 0
        self.tracking_servo_right_mark = 0
        self.servo_left_stop = 0
        self.servo_right_stop = 0

        super(CVThread, self).__init__(*args, **kwargs)
        self.__flag = threading.Event()
        self.__flag.clear()

        self.avg = None
        self.motionCounter = 0
        self.lastMovtionCaptured = datetime.datetime.now()
        self.frameDelta = None
        self.thresh = None
        self.cnts = None

    def mode(self, invar, imgInput):
        self.CVMode = invar
        self.imgCV = imgInput
        self.resume()

    def elementDraw(self, imgInput):
        if self.CVMode == 'none':
            pass

        elif self.CVMode == 'findColor':
            if self.findColorDetection:
                cv2.putText(imgInput, 'Target Detected', (40, 60), CVThread.font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                self.drawing = 1
            else:
                cv2.putText(imgInput, 'Target Detecting', (40, 60), CVThread.font, 0.5, (255, 255, 255), 1, cv2.LINE_AA)
                self.drawing = 0

            if self.radius > 10 and self.drawing:
                cv2.rectangle(imgInput, (int(self.box_x - self.radius), int(self.box_y + self.radius)),
                              (int(self.box_x + self.radius), int(self.box_y - self.radius)), (25
