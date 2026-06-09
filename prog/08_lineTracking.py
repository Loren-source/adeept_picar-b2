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


if __name__ == "main":
    sensor = LineSensor()          # On instancie l'objet une seule fois

    try:
        while True:
            sensor.print_status()  # On appelle la méthode sur l'objet
            time.sleep(0.3)
    except KeyboardInterrupt:
        pass
