#!/usr/bin/env python3
import threading
import cv2
import numpy as np
import datetime
import time
import imutils
import sys
import os

# Imports Adafruit pour les servomoteurs (Votre Code)
from board import SCL, SDA
import busio
from adafruit_motor import servo
from adafruit_pca9685 import PCA9685

# Imports moteurs de déplacement (roues motrices) et caméra
try:
    import move
    from picamera2 import Picamera2  
    import libcamera
    hardware_available = True
    print("[MATÉRIEL] Caméra et moteurs de propulsion détectés.")
except ImportError as e:
    print(f"[REMARQUE] Mode simulation ou dépendance manquante : {e}")
    hardware_available = False

# ====================================================================
# CONFIGURATION MATÉRIELLE DES SERVOMOTEURS (VOTRE CONFIGURATION)
# ====================================================================
PCA_ADDRESS   = 0x5f        # Adresse I²C de la carte Adeept
PWM_FREQ      = 50          # Hz – fréquence standard servomoteur

MIN_PULSE     = 500         # µs – impulsion mini (0°)
MAX_PULSE     = 2400        # µs – impulsion maxi (180°)
ACTUATION     = 180         # degrés – plage totale du servo

ANGLE_MIN     = 0           # limite basse de sécurité
ANGLE_MAX     = 180         # limite haute de sécurité

# Canaux des servos sur le robot
CANAL_DIRECTION = 0         # CH0 : Direction des roues avant
CANAL_TETE_H    = 1         # CH1 : Rotation horizontale de la tête (Gauche/Droite)
CANAL_TETE_V    = 2         # CH2 : Inclinaison verticale de la tête (Haut/Bas)
CANAUX_ROBOT    = [CANAL_DIRECTION, CANAL_TETE_H, CANAL_TETE_V]

# INITIALISATION DU BUS I2C ET PCA9685
try:
    i2c = busio.I2C(SCL, SDA)
    pca = PCA9685(i2c, address=PCA_ADDRESS)
    pca.frequency = PWM_FREQ
    pca_available = True
except Exception as e:
    print(f"[ERREUR] Impossible d'initialiser le PCA9685 : {e}. Mode virtuel activé.")
    pca_available = False

# Dictionnaires de suivi de l'état des servos
_servos: dict[int, servo.Servo] = {}
_angles: dict[int, float] = {}

def get_servo(canal: int) -> servo.Servo:
    """Retourne l'objet Servo du canal, en le créant si besoin."""
    if canal not in _servos:
        _servos[canal] = servo.Servo(
            pca.channels[canal],
            min_pulse=MIN_PULSE,
            max_pulse=MAX_PULSE,
            actuation_range=ACTUATION
        )
    return _servos[canal]

def set_angle(canal: int, angle: float):
    """Positionne le servomoteur du canal avec limitation de sécurité."""
    if not pca_available:
        return
    angle_safe = max(ANGLE_MIN, min(ANGLE_MAX, angle))
    s = get_servo(canal)
    s.angle = angle_safe
    _angles[canal] = angle_safe

def centrer_servos():
    """Ramène les servos du robot en position initiale stable pour la ligne."""
    print("[INFO] Positionnement initial des servos...")
    # CH0 (Direction) -> 90° (Tout droit)
    # CH1 (Tête Gauche/Droite) -> 90° (Bien en face)
    # CH2 (Tête Haut/Bas) -> 115° (Inclinée vers le sol pour cibler la ligne rouge)
    set_angle(CANAL_DIRECTION, 90)
    set_angle(CANAL_TETE_H, 90)
    set_angle(CANAL_TETE_V, 115) 
    time.sleep(0.5)

# ====================================================================
# CONFIGURATION DE LA LOGIQUE VISION ET SUIVI DE LIGNE
# ====================================================================
APPMode = 'none'
CVRun = 1
linePos_1 = 320      
linePos_2 = 420      
lineColorSet = 255   
findLineMove = 1
tracking_servo_status = 0 # -1: Gauche, 1: Droite, 0: Centré
FLCV_Status = 0
turn_speed = 28      
hflip = False
vflip = False

class CVThread(threading.Thread):
    font = cv2.FONT_HERSHEY_SIMPLEX

    def __init__(self, *args, **kwargs):
        self.CVThreading = 0
        self.CVMode = 'none'
        self.imgCV = None
        self.findColorDetection = 0

        self.left_Pos1 = None
        self.right_Pos1 = None
        self.center_Pos1 = None
        self.left_Pos2 = None
        self.right_Pos2 = None
        self.center_Pos2 = None
        self.center = None

        super(CVThread, self).__init__(*args, **kwargs)
        self.__flag = threading.Event()
        self.__flag.clear()

    def mode(self, invar, imgInput):
        self.CVMode = invar
        self.imgCV = imgInput
        self.resume()

    def elementDraw(self, imgInput):
        if self.CVMode == 'findlineCV':
            try:
                cv2.putText(imgInput, 'Suivi de ligne rouge actif', (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)
                if self.left_Pos1 is not None:
                    cv2.line(imgInput, (self.left_Pos1, (linePos_1 + 30)), (self.left_Pos1, (linePos_1 - 30)), (255, 128, 64), 2)
                    cv2.line(imgInput, (self.right_Pos1, (linePos_1 + 30)), (self.right_Pos1, (linePos_1 - 30)), (64, 128, 255), 2)
                cv2.line(imgInput, (0, linePos_1), (640, linePos_1), (255, 128, 64), 1)
                
                if self.center is not None:
                    center_y = int((linePos_1 + linePos_2) / 2)
                    cv2.line(imgInput, ((self.center - 20), center_y), ((self.center + 20), center_y), (0, 255, 0), 2)
            except:
                pass
        return imgInput

    def findLineCtrl(self, posInput):
        """Contrôle les servomoteurs et moteurs de propulsion selon la position de la ligne."""
        global findLineMove, tracking_servo_status, FLCV_Status
        if not pca_available:
            return

        if FLCV_Status == 0:    
            centrer_servos()
            FLCV_Status = 1
            
        if posInput is not None and findLineMove == 1:
            # ── DÉVIATION À DROITE (La ligne s'échappe vers la droite de l'image)
            if posInput > 400: 
                tracking_servo_status = 1 
                if CVRun and hardware_available:
                    set_angle(CANAL_DIRECTION, 45)   # Braquage des roues à droite
                    set_angle(CANAL_TETE_H, 65)      # Pivot de la tête à droite (90 - 25) pour garder la ligne en vue
                    move.video_Tracking_Move(turn_speed, 1) 
                else:
                    move.motorStop()

            # ── DÉVIATION À GAUCHE (La ligne s'échappe vers la gauche de l'image)
            elif posInput < 240: 
                tracking_servo_status = -1 
                if CVRun and hardware_available:
                    set_angle(CANAL_DIRECTION, 135)  # Braquage des roues à gauche
                    set_angle(CANAL_TETE_H, 115)     # Pivot de la tête à gauche (90 + 25) pour anticiper le virage
                    move.video_Tracking_Move(turn_speed, 1) 
                else:
                    move.motorStop()
                        
            # ── BIEN CENTRÉ
            else: 
                tracking_servo_status = 0 
                if CVRun and hardware_available:
                    set_angle(CANAL_DIRECTION, 90)   # Roues droites tout droit
                    set_angle(CANAL_TETE_H, 90)      # Tête droite face à la piste
                    move.video_Tracking_Move(turn_speed, 1) 
                else: 
                    move.motorStop()
        else: 
            # ── PERTE DE VUE (Balayage de recherche automatique basé sur le dernier état connu)
            if hardware_available:
                if tracking_servo_status == -1: 
                    set_angle(CANAL_DIRECTION, 135)  
                    set_angle(CANAL_TETE_H, 125)     # Regarde agressivement à gauche pour retrouver la ligne
                    move.video_Tracking_Move(turn_speed, 1) 
                elif tracking_servo_status == 1: 
                    set_angle(CANAL_DIRECTION, 45) 
                    set_angle(CANAL_TETE_H, 55)      # Regarde agressivement à droite
                    move.video_Tracking_Move(turn_speed, 1)
                else:
                    move.motorStop() 

    def findlineCV(self, frame_image):
        global findLineMove
        lineColorSet = 255 
        
        frame_hsv = cv2.cvtColor(frame_image, cv2.COLOR_BGR2HSV)
        
        # Isolation de la couleur rouge (deux plages HSV complémentaires)
        lower_red1 = np.array([0, 50, 40])
        upper_red1 = np.array([15, 255, 255])
        lower_red2 = np.array([165, 50, 40])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(frame_hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(frame_hsv, lower_red2, upper_red2)
        frame_findline = cv2.bitwise_or(mask1, mask2)
        
        frame_findline = cv2.GaussianBlur(frame_findline, (5, 5), 0)
        frame_findline = cv2.erode(frame_findline, None, iterations=2)
        frame_findline = cv2.dilate(frame_findline, None, iterations=3)
        
        colorPos_1 = frame_findline[linePos_1]
        colorPos_2 = frame_findline[linePos_2]
        
        try:
            lineColorCount_Pos1 = np.sum(colorPos_1 == lineColorSet)
            lineColorCount_Pos2 = np.sum(colorPos_2 == lineColorSet)
            lineIndex_Pos1 = np.where(colorPos_1 == lineColorSet)
            lineIndex_Pos2 = np.where(colorPos_2 == lineColorSet)

            if lineIndex_Pos1[0].size > 0 or lineIndex_Pos2[0].size > 0:
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

    def pause(self): self.__flag.clear()
    def resume(self): self.__flag.set()

    def run(self):
        while 1:
            self.__flag.wait()
            if self.CVMode == 'findlineCV':
                self.CVThreading = 1
                self.findlineCV(self.imgCV)
                self.CVThreading = 0
            else:
                self.pause()

class Camera(object): 
    modeSelect = 'none'

    @staticmethod
    def modeSet(invar): Camera.modeSelect = invar

    @staticmethod
    def frames():
        global hflip, vflip
        picam2 = Picamera2() 
        preview_config = picam2.preview_configuration
        preview_config.size = (640, 480)
        preview_config.format = 'RGB888'
        preview_config.transform = libcamera.Transform(hflip=hflip, vflip=vflip)
        preview_config.colour_space = libcamera.ColorSpace.Sycc()
        preview_config.buffer_count = 4
        preview_config.queue = True

        if not picam2.is_open: raise RuntimeError('Impossible de démarrer la caméra.')
        picam2.start()

        cvt = CVThread()
        cvt.start()

        while True:
            img = picam2.capture_array()
            if img is None: continue
            
            if Camera.modeSelect == 'none':
                cvt.pause()
            else:
                if not cvt.CVThreading:
                    cvt.mode(Camera.modeSelect, img)
                    cvt.resume()
                try: img = cvt.elementDraw(img)
                except: pass

            if cv2.imencode('.jpg', img)[0]:
                yield cv2.imencode('.jpg', img)[1].tobytes()

if __name__ == '__main__':
    try:
        if hardware_available:
            move.setup()
        Camera.modeSet('findlineCV')
        print("[DEMARRAGE] Suivi de ligne rouge avec balayage dynamique Adafruit activé !")
        
        for frame in Camera.frames():
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n[ARRET] Extinction propre du robot...")
    finally:
        if hardware_available:
            try: move.motorStop()
            except: pass
        if pca_available:
            centrer_servos()
            pca.deinit()
        print("[INFO] Terminé.")


