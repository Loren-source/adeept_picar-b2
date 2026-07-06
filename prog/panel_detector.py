#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import cv2
import time

class PanelDetector:
    """Détection de panneaux par template matching + validation temporelle."""
    def __init__(self, templates, threshold=0.65, min_frames=5, cooldown=2.0):
        self.templates = templates
        self.threshold = threshold
        self.min_frames = min_frames
        self.cooldown = cooldown

        self.counter = {name: 0 for name in templates}
        self.last_detected_time = {name: 0 for name in templates}
        self.last_detected_name = None

    def detect(self, frame_bgr, target_name=None):
        """
        Retourne le nom du panneau détecté si validé, sinon None.
        target_name : si spécifié, ne vérifie que ce panneau.
        """
        if frame_bgr is None:
            return None

        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        h, w = gray.shape

        candidates = [target_name] if target_name else list(self.templates.keys())
        best_match = None
        best_score = 0

        for name in candidates:
            template = self.templates[name]
            if template is None:
                continue
            th, tw = template.shape[:2]
            if th > h or tw > w:
                scale = min(w/tw, h/th) * 0.9
                new_w = int(tw * scale)
                new_h = int(th * scale)
                template = cv2.resize(template, (new_w, new_h))

            result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(result)

            if max_val > best_score:
                best_score = max_val
                best_match = name

        now = time.time()

        if best_match is not None and best_score >= self.threshold:
            self.counter[best_match] += 1
            for n in self.templates:
                if n != best_match:
                    self.counter[n] = 0

            if self.counter[best_match] >= self.min_frames:
                if now - self.last_detected_time[best_match] > self.cooldown:
                    self.last_detected_time[best_match] = now
                    self.counter[best_match] = 0
                    return best_match
        else:
            for n in self.templates:
                self.counter[n] = 0

        return None
