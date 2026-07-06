#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from motor import RobotMotor
from servo import RobotServos
from ultra import Ultrasonic
from lineTracking import LineTracker
from panel_detector import PanelDetector

class ResourceManager:
    """Conteneur unique de toutes les ressources matérielles."""
    def __init__(self):
        print("[RESOURCE] Initialisation des composants...")
        self.motor = RobotMotor()
        self.servos = RobotServos()
        self.ultrasonic = Ultrasonic()
        self.tracker = LineTracker()
        # Le détecteur de panneaux utilise la caméra ; on l'initialise après
        self.panel_detector = None  # sera initialisé plus tard avec la caméra

        # Centrage initial
        self.servos.set_angle(0, 97)   # direction
        self.servos.set_angle(1, 97)   # tête

    def init_camera_and_panel(self, template_paths):
        """Initialise la caméra et le détecteur de panneaux avec les templates fournis."""
        from picamera2 import Picamera2
        import cv2
        self.camera = Picamera2()
        config = self.camera.create_preview_configuration(
            main={"size": (640, 480), "format": "RGB888"}
        )
        self.camera.configure(config)
        self.camera.start()
        # Charger les templates
        templates = {}
        for key, path in template_paths.items():
            templates[key] = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if templates[key] is None:
                raise FileNotFoundError(f"Template {path} introuvable")
        self.panel_detector = PanelDetector(templates)

    def capture_frame(self):
        """Capture une image depuis la caméra (format BGR pour OpenCV)."""
        if self.camera is None:
            raise RuntimeError("Caméra non initialisée")
        frame = self.camera.capture_array()
        # Picamera2 renvoie du RGB, on convertit en BGR
        return cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

    def stop_all(self):
        """Arrêt d'urgence."""
        print("[RESOURCE] Arrêt d'urgence.")
        self.motor.stop()
        self.servos.set_angle(0, 97)
        self.servos.set_angle(1, 97)
        if hasattr(self, 'camera'):
            self.camera.stop()
