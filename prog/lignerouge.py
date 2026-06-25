import threading
import cv2
import numpy as np
import datetime
import time
import imutils
import sys
import os

# Forcer Python à regarder dans le dossier local du script
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

# Gestion des imports matériels réels
hardware_available = False
try:
    import RPIservo
    import move
    from picamera2 import Picamera2  # Version moderne pour Raspberry Pi OS
    print("Matériel détecté et initialisé avec succès.")
    hardware_available = True
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

    # Utilisation de la classe virtuelle
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
    
    # Rendre la variable accessible à la classe
    hardware_is_ready = hardware_available

    if hardware_available:
        try:
            scGear = RPIservo.ServoCtrl()
            scGear.moveInit()
            move.setup()
        except Exception as e:
            print(f"Erreur initialisation matériel : {e}")
            hardware_is_ready = False

    if not hardware_available or not hardware_is_ready:
        print("Avertissement : Utilisation du mode virtuel pour les moteurs/servos.")
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
                              (int(self.box_x + self.radius), int(self.box_y - self.radius)), (255, 255, 255), 1)

        elif self.CVMode == 'findlineCV':
            if CVThread.hardware_is_ready:
                CVThread.scGear.moveAngle(2, -15) # Oriente la caméra vers le sol

            try:
                cv2.putText(imgInput, 'Following Red Line', (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
                
                if self.left_Pos1 is not None:
                    cv2.line(imgInput, (self.left_Pos1, (linePos_1 + 30)), (self.left_Pos1, (linePos_1 - 30)), (255, 128, 64), 2)
                    cv2.line(imgInput, (self.right_Pos1, (linePos_1 + 30)), (self.right_Pos1, (linePos_1 - 30)), (64, 128, 255), 2)
                cv2.line(imgInput, (0, linePos_1), (640, linePos_1), (255, 128, 64), 1)

                if self.left_Pos2 is not None:
                    cv2.line(imgInput, (self.left_Pos2, (linePos_2 + 30)), (self.left_Pos2, (linePos_2 - 30)), (64, 128, 255), 2)
                    cv2.line(imgInput, (self.right_Pos2, (linePos_2 + 30)), (self.right_Pos2, (linePos_2 - 30)), (64, 128, 255), 2)
                cv2.line(imgInput, (0, linePos_2), (640, linePos_2), (64, 128, 255), 1)

                if self.center is not None:
                    center_y = int((linePos_1 + linePos_2) / 2)
                    cv2.line(imgInput, ((self.center - 20), center_y), ((self.center + 20), center_y), (0, 0, 0), 1)
                    cv2.line(imgInput, ((self.center), center_y + 20), ((self.center), center_y - 20), (0, 0, 0), 1)
            except Exception as e:
                print(f"Erreur d'affichage elementDraw: {e}")

        elif self.CVMode == 'watchDog':
            if self.drawing:
                cv2.rectangle(imgInput, (self.mov_x, self.mov_y), (self.mov_x + self.mov_w, self.mov_y + self.mov_h), (128, 255, 0), 1)

        return imgInput

    def watchDog(self, imgInput):
        gray = cv2.cvtColor(imgInput, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.avg is None:
            self.avg = gray.copy().astype("float")
            self.pause()
            return

        cv2.accumulateWeighted(gray, self.avg, 0.5)
        self.frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(self.avg))

        self.thresh = cv2.threshold(self.frameDelta, 5, 255, cv2.THRESH_BINARY)[1]
        self.thresh = cv2.dilate(self.thresh, None, iterations=2)
        self.cnts = cv2.findContours(self.thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.cnts = imutils.grab_contours(self.cnts)
        
        for c in self.cnts:
            if cv2.contourArea(c) < 5000:
                continue
     
            (self.mov_x, self.mov_y, self.mov_w, self.mov_h) = cv2.boundingRect(c)
            self.drawing = 1
            self.motionCounter += 1
            self.lastMovtionCaptured = datetime.datetime.now()

        if (datetime.datetime.now() - self.lastMovtionCaptured).total_seconds() >= 0.5:
            self.drawing = 0
        self.pause()

    def findLineCtrl(self, posInput):
        global findLineMove, tracking_servo_status, FLCV_Status
        if not CVThread.hardware_is_ready:
            return

        if FLCV_Status == 0:    
            CVThread.scGear.moveAngle(0, 0)
            CVThread.scGear.moveAngle(1, 0)
            CVThread.scGear.moveAngle(2, 0)
            FLCV_Status = 1
            
        if posInput is not None and findLineMove == 1:
            if FLCV_Status == -1:
                CVThread.scGear.stopWiggle()
                self.tracking_servo_left_mark = 0
                self.tracking_servo_right_mark = 0
                FLCV_Status = 1
                
            if posInput > 480: # Déviation à droite
                tracking_servo_status = 1 
                if CVRun:
                    CVThread.scGear.moveAngle(0, -30) 
                    move.video_Tracking_Move(turn_speed, 1) 
                else:
                    CVThread.scGear.moveAngle(0, 0)
                    move.motorStop()

            elif posInput < 180: # Déviation à gauche
                tracking_servo_status = -1 
                if CVRun:
                    CVThread.scGear.moveAngle(0, 30) 
                    move.video_Tracking_Move(turn_speed, 1) 
                else:
                    CVThread.scGear.moveAngle(0, 0)
                    move.motorStop()
                        
            else: # Centré
                tracking_servo_status = 0 
                if CVRun:
                    CVThread.scGear.moveAngle(0, 0) 
                    move.video_Tracking_Move(turn_speed, 1) 
                else: 
                    move.motorStop()
        else: 
            move.motorStop() 
            FLCV_Status = -1
            if tracking_servo_status == -1: 
                CVThread.scGear.moveAngle(0, 30) 
                move.video_Tracking_Move(turn_speed, 1) 
            elif tracking_servo_status == 1: 
                CVThread.scGear.moveAngle(0, -30) 
                move.video_Tracking_Move(turn_speed, 1) 

    def findlineCV(self, frame_image):
        global findLineMove
        lineColorSet = 255 
        
        # Correction : Picamera2 capture en RGB, conversion RGB -> HSV
        frame_hsv = cv2.cvtColor(frame_image, cv2.COLOR_RGB2HSV)
        
        # Plages de couleurs pour le Rouge en HSV
        lower_red1 = np.array([0, 70, 50])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([170, 70, 50])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(frame_hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(frame_hsv, lower_red2, upper_red2)
        frame_findline = cv2.bitwise_or(mask1, mask2)
        
        frame_findline = cv2.erode(frame_findline, None, iterations=2)
        frame_findline = cv2.dilate(frame_findline, None, iterations=2)
        
        colorPos_1 = frame_findline[linePos_1]
        colorPos_2 = frame_findline[linePos_2]
        
        try:
            lineColorCount_Pos1 = np.sum(colorPos_1 == lineColorSet)
            lineColorCount_Pos2 = np.sum(colorPos_2 == lineColorSet)

            lineIndex_Pos1 = np.where(colorPos_1 == lineColorSet)
            lineIndex_Pos2 = np.where(colorPos_2 == lineColorSet)

            if lineIndex_Pos1[0].size > 0:
                if abs(lineIndex_Pos1[0][-1] - lineIndex_Pos1[0][0]) > 500:
                    findLineMove = 0    
                else:
                    findLineMove = 1
            elif lineIndex_Pos2[0].size > 0:
                if abs(lineIndex_Pos2[0][-1] - lineIndex_Pos2[0][0]) > 500:
                    findLineMove = 0
                else:
                    findLineMove = 1
            else:
                findLineMove = 0

            if lineColorCount_Pos1 == 0: lineColorCount_Pos1 = 1
            if lineColorCount_Pos2 == 0: lineColorCount_Pos2 = 1

            self.left_Pos1 = lineIndex_Pos1[0][1] if lineIndex_Pos1[0].size > 1 else lineIndex_Pos1[0][0]
            self.right_Pos1 = lineIndex_Pos1[0][lineColorCount_Pos1-2] if lineIndex_Pos1[0].size > 1 else lineIndex_Pos1[0][0]
            self.center_Pos1 = int((self.left_Pos1 + self.right_Pos1) / 2)

            self.left_Pos2 = lineIndex_Pos2[0][1] if lineIndex_Pos2[0].size > 1 else lineIndex_Pos2[0][0]
            self.right_Pos2 = lineIndex_Pos2[0][lineColorCount_Pos2-2] if lineIndex_Pos2[0].size > 1 else lineIndex_Pos2[0][0]
            self.center_Pos2 = int((self.left_Pos2 + self.right_Pos2) / 2)

            self.center = int((self.center_Pos1 + self.center_Pos2) / 2)
            
        except Exception as e:
            self.center = None

        self.findLineCtrl(self.center)
        self.pause()

    # AJOUT IMPÉRATIF DU DÉCORATEUR @staticmethod
    @staticmethod
    def servoMove(ID, Dir, errorInput):
        if not CVThread.hardware_is_ready:
            return
        if ID == 1:
            errorGenOut = CVThread.kalman_filter_X.kalman(errorInput)
            CVThread.P_anglePos += 0.15 * (errorGenOut * Dir) * CVThread.cameraDiagonalW / CVThread.videoW
            if abs(errorInput) > CVThread.tor:
                CVThread.scGear.moveAngle(ID, CVThread.P_anglePos)
                CVThread.X_lock = 0
            else:
                CVThread.X_lock = 1
        elif ID == 2:
            errorGenOut = CVThread.kalman_filter_Y.kalman(errorInput)
            CVThread.T_anglePos += 0.1 * (errorGenOut * Dir) * CVThread.cameraDiagonalH / CVThread.videoH
            if abs(errorInput) > CVThread.tor:
                CVThread.scGear.moveAngle(ID, CVThread.T_anglePos)
                CVThread.Y_lock = 0
            else:
                CVThread.Y_lock = 1
        time.sleep(0.1)

    def findColor(self, frame_image):
        global APPMode
        if APPMode == 'APP':
            hsv = cv2.cvtColor(frame_image, cv2.COLOR_RGB2HSV) # Corrigé pour Picamera2 (RGB)
        else:
            hsv = cv2.cvtColor(frame_image, cv2.COLOR_RGB2HSV) # Corrigé pour Picamera2 (RGB)
        mask = cv2.inRange(hsv, colorLower, colorUpper)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
        
        if len(cnts) > 0:
            self.findColorDetection = 1
            c = max(cnts, key=cv2.contourArea)
            ((self.box_x, self.box_y), self.radius) = cv2.minEnclosingCircle(c)
            X = int(self.box_x)
            Y = int(self.box_y)
            error_Y = 240 - Y
            error_X = 320 - X
            CVThread.servoMove(CVThread.P_servo, CVThread.P_direction, -error_X)
            CVThread.servoMove(CVThread.T_servo, CVThread.T_direction, -error_Y)
        else:
            self.findColorDetection = 0
        self.pause()

    def pause(self):
        self.__flag.clear()

    def resume(self):
        self.__flag.set()

    def run(self):
        while 1:
            self.__flag.wait()
            if self.CVMode == 'none':
                continue
            elif self.CVMode == 'findColor':
                self.CVThreading = 1
                self.findColor(self.imgCV)
                self.CVThreading = 0
            elif self.CVMode == 'findlineCV':
                self.CVThreading = 1
                self.findlineCV(self.imgCV)
                self.CVThreading = 0
            elif self.CVMode == 'watchDog':
                self.CVThreading = 1
                self.watchDog(self.imgCV)
                self.CVThreading = 0


class Camera(object): 
    video_source = 0
    modeSelect = 'none'

    @staticmethod
    def colorFindSet(invarH, invarS, invarV):
        global colorUpper, colorLower
        HUE_1, HUE_2 = min(invarH + 15, 180), max(invarH - 15, 0)
        SAT_1, SAT_2 = min(invarS + 150, 255), max(invarS - 150, 0)
        VAL_1, VAL_2 = min(invarV + 150, 255), max(invarV - 150, 0)
        colorUpper = np.array([HUE_1, SAT_1, VAL_1])
        colorLower = np.array([HUE_2, SAT_2, VAL_2])

    @staticmethod
    def modeSet(invar):
        Camera.modeSelect = invar

    @staticmethod
    def CVRunSet(invar):
        global CVRun
        CVRun = invar

    @staticmethod
    def linePosSet_1(invar):
        global linePos_1
        linePos_1 = invar

    @staticmethod
    def linePosSet_2(invar):
        global linePos_2
        linePos_2 = invar

    @staticmethod
    def Threshold(value):
        global Threshold
        Threshold = value

    @staticmethod
    def set_video_source(source):
        Camera.video_source = source

    @staticmethod
    def frames():
        global ImgIsNone, hflip, vflip
        
        if not hardware_available:
            print("Erreur : Picamera2 non disponible en mode simulation.")
            return

        picam2 = Picamera2() 
        
        # Configuration correcte et moderne pour Picamera2
        config = picam2.create_preview_configuration()
        config["main"]["size"] = (640, 480)
        config["main"]["format"] = "RGB888"
        
        # Gestion optionnelle des flips selon les fonctionnalités de la version installée
        picam2.configure(config)

        try:
            picam2.start()
        except Exception as e:
            print(f"Error starting Picamera2: {e}")
            return

        cvt = CVThread()
        cvt.daemon = True # Évite de bloquer le script à la fermeture
        cvt.start()

        while True:
            img = picam2.capture_array()

            if img is None:
                continue
            
            if Camera.modeSelect == 'none':
                cvt.pause()
            else:
                if not cvt.CVThreading:
                    cvt.mode(Camera.modeSelect, img.copy()) # .copy() évite les conflits d'accès mémoire entre threads
                    cvt.resume()
                try:
                    img = cvt.elementDraw(img)
                except Exception as e:
                    pass

            # Conversion RGB (Picam) -> BGR (OpenCV s'attend à du BGR pour imencode)
            img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
            if cv2.imencode('.jpg', img_bgr)[0]:
                yield cv2.imencode('.jpg', img_bgr)[1].tobytes()


# ==========================================
# BOUCLE PRINCIPALE D'ACTIVATION DU ROBOT
# ==========================================
if __name__ == '__main__':
    Camera.modeSet('findlineCV')
    Camera.CVRunSet(1)
    
    print("Démarrage du flux vidéo et du suivi de la ligne rouge...")
    
    try:
        if hardware_available:
            for frame in Camera.frames():
                time.sleep(0.01)
        else:
            print("Exécution en mode virtuel (Simulation PC). Aucun flux Picamera2.")
            # Mode simulation : On simule l'activité du thread pour le test syntaxique
            cvt = CVThread()
            cvt.start()
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\nArrêt du robot demandé par l'utilisateur.")
        if hardware_available:
            try:
                import move
                move.motorStop()
            except:
                pass
