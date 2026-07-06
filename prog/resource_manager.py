#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic
from lineTracking import LineTracker
from picamera2 import Picamera2
from panel_detector import PanelDetector

class ResourceManager:
    """Instance unique de toutes les ressources matérielles."""
    def __init__(self):
        print("[RESOURCE] Initialisation matérielle...")
        self.motor = RobotMotor()
        self.servos = RobotServos()
        self.ultrasonic = Ultrasonic()
        self.tracker = LineTracker()
        self.panel_detector = None
        self.camera = None

        # Centrage initial
        self.servos.set_angle(0, 97)
        self.servos.set_angle(1, 97)

    def init_camera_and_panels(self, templates):
        """Initialise la caméra et le détecteur de panneaux."""
        print("[RESOURCE] Initialisation caméra...")
        self.camera = Picamera2()
        config = self.camera.create_preview_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        self.camera.configure(config)
        self.camera.start()
        # Chargement des templates
        panel_templates = {}
        for name, path in templates.items():
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is None:
                raise FileNotFoundError(f"Template {path} introuvable")
            panel_templates[name] = img
        self.panel_detector = PanelDetector(panel_templates)

    def capture_frame(self):
        """Capture une image (BGR pour OpenCV)."""
        if self.camera is None:
            raise RuntimeError("Caméra non initialisée")
        frame = self.camera.capture_array()
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    def stop_all(self):
        """Arrêt d'urgence."""
        print("[RESOURCE] Arrêt d'urgence.")
        self.motor.stop()
        self.servos.set_angle(0, 97)
        self.servos.set_angle(1, 97)
        if self.camera is not None:
            self.camera.stop()
