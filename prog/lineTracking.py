import time
from gpiozero import InputDevice


class LineSensor:
    """Gère les 3 capteurs de ligne IR d'un robot."""

    def init(self, pin_left=22, pin_middle=27, pin_right=17):
        # Les pins deviennent des attributs de l'objet
        self.left   = InputDevice(pin=pin_left)
        self.middle = InputDevice(pin=pin_middle)
        self.right  = InputDevice(pin=pin_right)

    def read(self):
        """Retourne un dictionnaire avec l'état des 3 capteurs."""
        return {
            "left":   self.left.value,
            "middle": self.middle.value,
            "right":  self.right.value,
        }

    def print_status(self):
        """Affiche l'état des capteurs dans le terminal."""
        values = self.read()
        print("left: %(left)d   middle: %(middle)d   right: %(right)d" % values)

class LineTracker:
    def __init__(self, left_pin=line_pin_left, middle_pin=line_pin_middle, right_pin=line_pin_right):
        self.left = InputDevice(pin=left_pin)
        self.middle = InputDevice(pin=middle_pin)
        self.right = InputDevice(pin=right_pin)

    def get_status(self):
        return {
            'left': self.left.value,
            'middle': self.middle.value,
            'right': self.right.value
        }
if name=="__main__":
    line_tracker = LineTracker()
    try:
        while True:
            status = line_tracker.get_status()
            print(f"Left: {status['left']}   Middle: {status['middle']}   Right: {status['right']}")
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass

if __name__ == "main":
    sensor = LineSensor()          # On instancie l'objet une seule fois

    try:
        while True:
            sensor.print_status()  # On appelle la méthode sur l'objet
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
