#!/usr/bin/env python3
import time
from gpiozero import LED

# ==========================
# Initialisation LED HAL3.1
# ==========================
def switchSetup():
    global led1, led2, led3
    led1 = LED(9)
    led2 = LED(25)
    led3 = LED(11)

# ==========================
# Initialisation LED RGB
# ==========================
def led_rgb():
    global r_rgb1, r_rgb2, r_rgb3
    global l_rgb1, l_rgb2, l_rgb3
    # Feu droit
    r_rgb1 = LED(1)    # Right Rouge
    r_rgb2 = LED(5)    # Right Vert
    r_rgb3 = LED(6)    # Right Bleu
    # Feu gauche
    l_rgb1 = LED(0)    # Left Rouge
    l_rgb2 = LED(19)   # Left Vert
    l_rgb3 = LED(13)   # Left Bleu

# ==========================
# Commande des LED
# ==========================
def switch(port, status):
    # LED HAL3.1 — logique normale (1=allumée, 0=éteinte)
    if port == 1:
        led1.on() if status == 1 else led1.off()
    elif port == 2:
        led2.on() if status == 1 else led2.off()
    elif port == 3:
        led3.on() if status == 1 else led3.off()
    # LED RGB — logique inversée (1=off(), 0=on())
    elif port == 4:
        r_rgb1.off() if status == 1 else r_rgb1.on()
    elif port == 5:
        r_rgb2.off() if status == 1 else r_rgb2.on()
    elif port == 6:
        r_rgb3.off() if status == 1 else r_rgb3.on()
    elif port == 7:
        l_rgb1.off() if status == 1 else l_rgb1.on()
    elif port == 8:
        l_rgb2.off() if status == 1 else l_rgb2.on()
    elif port == 9:
        l_rgb3.off() if status == 1 else l_rgb3.on()
    else:
        print("Commande incorrecte")

# ==========================
# Tout éteindre
# ==========================
def set_all_switch_off():
    for port in range(1, 10):
        switch(port, 0)

# ==========================
# Nom des LED
# ==========================
PORT_NAMES = {
    1: "LED1",
    2: "LED2",
    3: "LED3",
    4: "Right Rouge",
    5: "Right Vert",
    6: "Right Bleu",
    7: "Left Rouge",
    8: "Left Vert",
    9: "Left Bleu"
}

# ==========================
# Programme principal
# ==========================
def main():
    print("=== Contrôle manuel des LED ===")
    print("11 à 19 : allumer")
    print("21 à 29 : éteindre")
    print("00 : tout éteindre")
    print("99 : quitter")

    while True:
        commande = input("\nCommande : ").strip()

        if commande == "99":
            print("Fin du programme")
            set_all_switch_off()
            break

        if commande == "00":
            set_all_switch_off()
            print("Toutes les LED sont éteintes")
            continue

        if len(commande) != 2 or not commande.isdigit():
            print("Commande incorrecte")
            continue

        action = int(commande[0])
        port   = int(commande[1])

        if port < 1 or port > 9:
            print("Port incorrect")
            continue

        if action == 1:
            switch(port, 1)
            print(PORT_NAMES[port], "allumée")
        elif action == 2:
            switch(port, 0)
            print(PORT_NAMES[port], "éteinte")
        else:
            print("Commande incorrecte")

# ==========================
# Lancement du programme
# ==========================
if __name__ == "__main__":
    switchSetup()
    led_rgb()
    set_all_switch_off()
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterruption clavier")
        set_all_switch_off()
