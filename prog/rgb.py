#import RPi.GPIO as GPIO
from gpiozero import PWMOutputDevice as PWM
import time

Left_R = 19
Left_G = 0
Left_B = 13

Right_R = 1
Right_G = 5
Right_B = 6

colors = [
    0xFF0000,
    0x00FF00,
    0x0000FF,
    0xFFFF00,
    0xFF00FF,
    0x00FFFF,
    0x6F00D2,
    0xFF5809
]


# ==========================================================
# INITIALISATION
# ==========================================================

def setup():
    global L_R, L_G, L_B
    global R_R, R_G, R_B

    L_R = PWM(pin=Left_R, initial_value=1.0, frequency=2000)
    L_G = PWM(pin=Left_G, initial_value=1.0, frequency=2000)
    L_B = PWM(pin=Left_B, initial_value=1.0, frequency=2000)

    R_R = PWM(pin=Right_R, initial_value=1.0, frequency=2000)
    R_G = PWM(pin=Right_G, initial_value=1.0, frequency=2000)
    R_B = PWM(pin=Right_B, initial_value=1.0, frequency=2000)


# ==========================================================
# OUTILS
# ==========================================================

def map(x, in_min, in_max, out_min, out_max):
    return (x-in_min)*(out_max-out_min)/(in_max-in_min)+out_min


def _rgb_to_pwm(r, g, b):

    r = map(r,0,255,0,1.0)
    g = map(g,0,255,0,1.0)
    b = map(b,0,255,0,1.0)

    return 1-r,1-g,1-b


# ==========================================================
# CONTROLE INDIVIDUEL
# ==========================================================

def setLeftRGB(r,g,b):

    r,g,b = _rgb_to_pwm(r,g,b)

    L_R.value = r
    L_G.value = g
    L_B.value = b


def setRightRGB(r,g,b):

    r,g,b = _rgb_to_pwm(r,g,b)

    R_R.value = r
    R_G.value = g
    R_B.value = b


# ==========================================================
# LES DEUX FEUX
# ==========================================================

def setAllRGBColor(r,g,b):

    setLeftRGB(r,g,b)
    setRightRGB(r,g,b)


def setAllColor(col):

    R = (col & 0xff0000)>>16
    G = (col & 0x00ff00)>>8
    B = (col & 0x0000ff)

    setAllRGBColor(R,G,B)


# ==========================================================
# FONCTIONS SIMPLES
# ==========================================================

def eteindre():

    setAllRGBColor(0,0,0)


def rouge():

    setAllRGBColor(255,0,0)


def orange():

    setAllRGBColor(255,120,0)


# ==========================================================
# FEUX DE DIRECTION
# ==========================================================

def clignotant_gauche(on):

    if on:
        setLeftRGB(255,120,0)
    else:
        setLeftRGB(0,0,0)

    setRightRGB(0,0,0)


def clignotant_droite(on):

    if on:
        setRightRGB(255,120,0)
    else:
        setRightRGB(0,0,0)

    setLeftRGB(0,0,0)


# ==========================================================
# WARNINGS
# ==========================================================

def warnings(on):

    if on:
        setAllRGBColor(255,0,0)
    else:
        eteindre()


# ==========================================================
# PERTE DE LIGNE
# ==========================================================

def perte_ligne():

    setAllRGBColor(255,0,0)


# ==========================================================
# DEMO
# ==========================================================

def loop():

    while True:

        print("Gauche")
        for i in range(8):
            clignotant_gauche(i%2)
            time.sleep(0.25)

        print("Droite")
        for i in range(8):
            clignotant_droite(i%2)
            time.sleep(0.25)

        print("Warnings")
        for i in range(8):
            warnings(i%2)
            time.sleep(0.25)

        print("Rouge fixe")
        perte_ligne()
        time.sleep(2)

        eteindre()
        time.sleep(1)


# ==========================================================
# FIN
# ==========================================================

def destroy():

    eteindre()

    L_R.stop()
    L_G.stop()
    L_B.stop()

    R_R.stop()
    R_G.stop()
    R_B.stop()


if __name__ == "__main__":

    setup()

    try:
        loop()

    except KeyboardInterrupt:
        destroy()
