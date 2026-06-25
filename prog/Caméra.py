#!/usr/bin/env python3
# coding: utf-8
"""
camera.py — Suivi de ligne ROUGE pour robot Raspberry Pi
Basé sur le fichier original du fabricant, adapté pour :
  - Ligne rouge (détection HSV)
  - Caméra à 11 cm du sol
  - Virage serré à ~70°
"""

import os
import cv2
import numpy as np
import datetime
import time
import imutils
import sys
import threading

script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

try:
    import RPIservo
    import move
    from picamera2 import Picamera2
    import libcamera
    import Kalman_filter
    print("Matériel détecté et initialisé avec succès.")
    HARDWARE = True
except ImportError as e:
    print(f"Mode simulation : {e}")
    HARDWARE = False


CVRun         = 1
linePos_1     = 420   # Ligne de scan haute  (proche du fabricant original : 440)
linePos_2     = 350   # Ligne de scan basse  (proche du fabricant original : 380)
lineColorSet  = 255
frameRender   = 1
Threshold     = 80
findLineMove  = 1
tracking_servo_status = 0
FLCV_Status   = 0
ImgIsNone     = 0
hflip         = False
vflip         = False

# Vitesses (valeurs du fabricant, qui fonctionnent)
turn_speed    = 45    # Vitesse en virage
forward_speed = 20    # Vitesse en ligne droite

# Seuils de virage (valeurs du fabricant)
TURN_RIGHT_THRESHOLD = 480   # Centre > 480 → virer à droite
TURN_LEFT_THRESHOLD  = 180   # Centre < 180 → virer à gauche

# Angle de braquage des roues pour le virage serré à 70°
WHEEL_ANGLE = 65

# Angle de la caméra vers le bas (adapté pour 11 cm de hauteur)
CAMERA_DOWN_ANGLE = -20



def detect_red_line(frame_bgr):
    """Retourne un masque binaire de la ligne rouge dans l'image."""
    hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)

    # Rouge occupe deux plages en HSV (autour de 0° et 180°)
    lower_red1 = np.array([0,   50, 40])
    upper_red1 = np.array([15, 255, 255])
    lower_red2 = np.array([165, 50, 40])
    upper_red2 = np.array([180, 255, 255])

    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask  = cv2.bitwise_or(mask1, mask2)

    mask = cv2.GaussianBlur(mask, (5, 5), 0)
    mask = cv2.erode(mask,  None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=3)
    return mask



class DummyKalman:
    def kalman(self, val): return val

class DummyGear:
    def moveAngle(self, id, angle): pass
    def stopWiggle(self): pass
    def moveInit(self): pass

class DummyMove:
    @staticmethod
    def video_Tracking_Move(speed, direction): pass
    @staticmethod
    def motorStop(): pass
    @staticmethod
    def setup(): pass



class CVThread(threading.Thread):
    font = cv2.FONT_HERSHEY_SIMPLEX

    if HARDWARE:
        kalman_filter_X = Kalman_filter.Kalman_filter(0.01, 0.1)
        kalman_filter_Y = Kalman_filter.Kalman_filter(0.01, 0.1)
    else:
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

    if HARDWARE:
        scGear = RPIservo.ServoCtrl()
        scGear.moveInit()
        move.setup()
    else:
        scGear = DummyGear()

    def __init__(self, *args, **kwargs):
        self.CVThreading = 0
        self.CVMode = 'none'
        self.imgCV = None
        self.mov_x = self.mov_y = self.mov_w = self.mov_h = None
        self.radius = 0
        self.box_x = self.box_y = None
        self.drawing = 0
        self.findColorDetection = 0
        self.left_Pos1 = self.right_Pos1 = self.center_Pos1 = None
        self.left_Pos2 = self.right_Pos2 = self.center_Pos2 = None
        self.center = None
        self.tracking_servo_left_mark = 0
        self.tracking_servo_right_mark = 0

        super(CVThread, self).__init__(*args, **kwargs)
        self.__flag = threading.Event()
        self.__flag.clear()

        self.avg = None
        self.motionCounter = 0
        self.lastMovtionCaptured = datetime.datetime.now()
        self.frameDelta = self.thresh = self.cnts = None

    def mode(self, invar, imgInput):
        self.CVMode = invar
        self.imgCV = imgInput
        self.resume()

    
    def elementDraw(self, imgInput):
        if self.CVMode == 'none':
            pass

        elif self.CVMode == 'findColor':
            label = 'Target Detected' if self.findColorDetection else 'Target Detecting'
            cv2.putText(imgInput, label, (40, 60), CVThread.font, 0.5, (255,255,255), 1, cv2.LINE_AA)
            if self.radius > 10 and self.drawing:
                cv2.rectangle(imgInput,
                    (int(self.box_x - self.radius), int(self.box_y + self.radius)),
                    (int(self.box_x + self.radius), int(self.box_y - self.radius)),
                    (255,255,255), 1)

        elif self.CVMode == 'findlineCV':
            # NE PAS appeler moveAngle ici — c'est fait dans findLineCtrl
            try:
                cv2.putText(imgInput, 'Following Red Line', (30, 50),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

                if self.left_Pos1 is not None:
                    cv2.line(imgInput, (self.left_Pos1,  linePos_1+30), (self.left_Pos1,  linePos_1-30), (255,128,64), 2)
                    cv2.line(imgInput, (self.right_Pos1, linePos_1+30), (self.right_Pos1, linePos_1-30), (64,128,255), 2)
                cv2.line(imgInput, (0, linePos_1), (640, linePos_1), (255,128,64), 1)

                if self.left_Pos2 is not None:
                    cv2.line(imgInput, (self.left_Pos2,  linePos_2+30), (self.left_Pos2,  linePos_2-30), (64,128,255), 2)
                    cv2.line(imgInput, (self.right_Pos2, linePos_2+30), (self.right_Pos2, linePos_2-30), (64,128,255), 2)
                cv2.line(imgInput, (0, linePos_2), (640, linePos_2), (64,128,255), 1)

                if self.center is not None:
                    cy = int((linePos_1 + linePos_2) / 2)
                    cv2.line(imgInput, (self.center-20, cy), (self.center+20, cy), (0,0,0), 1)
                    cv2.line(imgInput, (self.center, cy+20), (self.center, cy-20), (0,0,0), 1)
            except Exception:
                pass

        elif self.CVMode == 'watchDog':
            if self.drawing:
                cv2.rectangle(imgInput,
                    (self.mov_x, self.mov_y),
                    (self.mov_x + self.mov_w, self.mov_y + self.mov_h),
                    (128, 255, 0), 1)

        return imgInput

    
    def findLineCtrl(self, posInput):
        global findLineMove, tracking_servo_status, FLCV_Status

        if not HARDWARE:
            return

        # Initialisation une seule fois au démarrage
        if FLCV_Status == 0:
            CVThread.scGear.moveAngle(0, 0)               # Roues centrées
            CVThread.scGear.moveAngle(1, 0)               # Caméra centrée horizontalement
            CVThread.scGear.moveAngle(2, CAMERA_DOWN_ANGLE)  # Caméra inclinée vers le bas
            FLCV_Status = 1

        if posInput is not None and findLineMove == 1:
            if FLCV_Status == -1:
                CVThread.scGear.stopWiggle()
                self.tracking_servo_left_mark  = 0
                self.tracking_servo_right_mark = 0
                FLCV_Status = 1

            if posInput > TURN_RIGHT_THRESHOLD:          # Virage à DROITE
                tracking_servo_status = 1
                if CVRun:
                    CVThread.scGear.moveAngle(0, -WHEEL_ANGLE)
                    move.video_Tracking_Move(turn_speed, 1)
                else:
                    CVThread.scGear.moveAngle(0, 0)
                    move.motorStop()

            elif posInput < TURN_LEFT_THRESHOLD:         # Virage à GAUCHE
                tracking_servo_status = -1
                if CVRun:
                    CVThread.scGear.moveAngle(0, WHEEL_ANGLE)
                    move.video_Tracking_Move(turn_speed, 1)
                else:
                    CVThread.scGear.moveAngle(0, 0)
                    move.motorStop()

            else:                                        # Ligne droite
                tracking_servo_status = 0
                if CVRun:
                    CVThread.scGear.moveAngle(0, 0)
                    move.video_Tracking_Move(forward_speed, 1)
                else:
                    move.motorStop()

        else:
            # Ligne perdue — continuer dans la dernière direction connue
            # (comportement identique à l'original)
            FLCV_Status = -1
            if tracking_servo_status == -1:
                CVThread.scGear.moveAngle(0, WHEEL_ANGLE)
                move.video_Tracking_Move(turn_speed, 1)
            elif tracking_servo_status == 1:
                CVThread.scGear.moveAngle(0, -WHEEL_ANGLE)
                move.video_Tracking_Move(turn_speed, 1)
            else:
                move.motorStop()

    
    def findlineCV(self, frame_image):
        global findLineMove

        frame_findline = detect_red_line(frame_image)

        colorPos_1 = frame_findline[linePos_1]
        colorPos_2 = frame_findline[linePos_2]

        try:
            lineColorCount_Pos1 = np.sum(colorPos_1 == lineColorSet)
            lineColorCount_Pos2 = np.sum(colorPos_2 == lineColorSet)

            lineIndex_Pos1 = np.where(colorPos_1 == lineColorSet)
            lineIndex_Pos2 = np.where(colorPos_2 == lineColorSet)

            # Arrêt si la "ligne" occupe presque toute la largeur (carrefour / fin)
            if lineIndex_Pos1[0].size > 0:
                findLineMove = 0 if abs(lineIndex_Pos1[0][-1] - lineIndex_Pos1[0][0]) > 500 else 1
            elif lineIndex_Pos2[0].size > 0:
                findLineMove = 0 if abs(lineIndex_Pos2[0][-1] - lineIndex_Pos2[0][0]) > 500 else 1
            else:
                findLineMove = 0

            if lineColorCount_Pos1 == 0: lineColorCount_Pos1 = 1
            if lineColorCount_Pos2 == 0: lineColorCount_Pos2 = 1

            self.left_Pos1   = lineIndex_Pos1[0][1] if lineIndex_Pos1[0].size > 1 else lineIndex_Pos1[0][0]
            self.right_Pos1  = lineIndex_Pos1[0][lineColorCount_Pos1 - 2] if lineIndex_Pos1[0].size > 1 else lineIndex_Pos1[0][0]
            self.center_Pos1 = int((self.left_Pos1 + self.right_Pos1) / 2)

            self.left_Pos2   = lineIndex_Pos2[0][1] if lineIndex_Pos2[0].size > 1 else lineIndex_Pos2[0][0]
            self.right_Pos2  = lineIndex_Pos2[0][lineColorCount_Pos2 - 2] if lineIndex_Pos2[0].size > 1 else lineIndex_Pos2[0][0]
            self.center_Pos2 = int((self.left_Pos2 + self.right_Pos2) / 2)

            self.center = int((self.center_Pos1 + self.center_Pos2) / 2)

        except Exception:
            self.center = None

        self.findLineCtrl(self.center)
        self.pause()

    
    def watchDog(self, imgInput):
        gray = cv2.cvtColor(imgInput, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        if self.avg is None:
            self.avg = gray.copy().astype("float")
            return
        cv2.accumulateWeighted(gray, self.avg, 0.5)
        self.frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(self.avg))
        self.thresh = cv2.threshold(self.frameDelta, 5, 255, cv2.THRESH_BINARY)[1]
        self.thresh = cv2.dilate(self.thresh, None, iterations=2)
        self.cnts   = imutils.grab_contours(
            cv2.findContours(self.thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE))
        for c in self.cnts:
            if cv2.contourArea(c) < 5000:
                continue
            (self.mov_x, self.mov_y, self.mov_w, self.mov_h) = cv2.boundingRect(c)
            self.drawing = 1
            self.motionCounter += 1
            self.lastMovtionCaptured = datetime.datetime.now()
        if (datetime.datetime.now() - self.lastMovtionCaptured).seconds >= 1:
            self.drawing = 0
        self.pause()

    
    def servoMove(ID, Dir, errorInput):
        if not HARDWARE:
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
        hsv  = cv2.cvtColor(frame_image, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, np.array([24,100,100]), np.array([44,255,255]))
        mask = cv2.erode(mask,  None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
        if len(cnts) > 0:
            self.findColorDetection = 1
            c = max(cnts, key=cv2.contourArea)
            ((self.box_x, self.box_y), self.radius) = cv2.minEnclosingCircle(c)
            CVThread.servoMove(CVThread.P_servo, CVThread.P_direction, -(320 - int(self.box_x)))
            CVThread.servoMove(CVThread.T_servo, CVThread.T_direction, -(240 - int(self.box_y)))
        else:
            self.findColorDetection = 0
        self.pause()

    
    def pause(self):  self.__flag.clear()
    def resume(self): self.__flag.set()

    def run(self):
        while True:
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
    modeSelect   = 'none'

    @staticmethod
    def colorFindSet(invarH, invarS, invarV):
        pass  # non utilisé en mode ligne

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
    def set_video_source(source):
        Camera.video_source = source

    @staticmethod
    def frames():
        global ImgIsNone, hflip, vflip

        picam2 = Picamera2()
        preview_config = picam2.preview_configuration
        preview_config.size         = (640, 480)
        preview_config.format       = 'RGB888'
        preview_config.transform    = libcamera.Transform(hflip=hflip, vflip=vflip)
        preview_config.colour_space = libcamera.ColorSpace.Sycc()
        preview_config.buffer_count = 4
        preview_config.queue        = True

        if not picam2.is_open:
            raise RuntimeError('Could not start camera.')

        try:
            picam2.start()
        except Exception as e:
            print(f"Erreur démarrage caméra : {e}")

        cvt = CVThread()
        cvt.start()

        while True:
            try:
                request = picam2.capture_request()
                img = request.make_array('main')
                request.release()
            except Exception:
                time.sleep(0.01)
                continue

            if img is None:
                continue

            if Camera.modeSelect == 'none':
                cvt.pause()
            else:
                if not cvt.CVThreading:
                    cvt.mode(Camera.modeSelect, img)
                    cvt.resume()
                try:
                    img = cvt.elementDraw(img)
                except Exception:
                    pass

            ok, buf = cv2.imencode('.jpg', img)
            if ok:
                yield buf.tobytes()



if __name__ == '__main__':
    Camera.modeSet('findlineCV')
    Camera.CVRunSet(1)
    print("Démarrage du suivi de ligne rouge...")
    print(f"  Caméra à 11 cm du sol | angle caméra : {CAMERA_DOWN_ANGLE}°")
    print(f"  Scan lignes : y={linePos_1} (haut) et y={linePos_2} (bas)")
    print(f"  Seuils virage : droite>{TURN_RIGHT_THRESHOLD} | gauche<{TURN_LEFT_THRESHOLD}")
    print(f"  Angle roues : ±{WHEEL_ANGLE}° | vitesse virage : {turn_speed}")

    try:
        for frame in Camera.frames():
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("\nArrêt.")
        if HARDWARE:
            move.motorStop()
