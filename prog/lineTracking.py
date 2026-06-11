import time
from gpiozero import InputDevice

class LineTracker:
    def __init__(self, pin_left=22, pin_middle=27, pin_right=17):
        self.left   = InputDevice(pin=pin_left)
        self.middle = InputDevice(pin=pin_middle)
        self.right  = InputDevice(pin=pin_right)

    def get_status(self):
        """Retourne un dictionnaire avec l'état des 3 capteurs."""
        return {
            'left':   self.left.value,
            'middle': self.middle.value,
            'right':  self.right.value,
        }

    def print_status(self):
        """Affiche l'état des 3 capteurs dans le terminal."""
        s = self.get_status()
        print(f"left: {s['left']}   middle: {s['middle']}   right: {s['right']}")

if __name__ == "__main__":
    tracker = LineTracker()
    try:
        while True:
            tracker.print_status()
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
