from gpiozero import LED
import time

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

    r_rgb1 = LED(1)     # Right Rouge
    r_rgb2 = LED(5)     # Right Vert
    r_rgb3 = LED(6)     # Right Bleu

    l_rgb1 = LED(19)    # Left Rouge
    l_rgb2 = LED(13)    # Left Vert
    l_rgb3 = LED(0)     # Left Bleu

# ==========================
# Commande des LED
# ==========================

def switch(port, status):

    if port == 1:
        if status == 1:
            led1.on()
        else:
            led1.off()

    elif port == 2:
        if status == 1:
            led2.on()
        else:
            led2.off()

    elif port == 3:
        if status == 1:
            led3.on()
        else:
            led3.off()

    elif port == 4:
        if status == 1:
            r_rgb1.on()
        else:
            r_rgb1.off()

    elif port == 5:
        if status == 1:
            r_rgb2.on()
        else:
            r_rgb2.off()

    elif port == 6:
        if status == 1:
            r_rgb3.on()
        else:
            r_rgb3.off()

    elif port == 7:
        if status == 1:
            l_rgb1.on()
        else:
            l_rgb1.off()

    elif port == 8:
        if status == 1:
            l_rgb2.on()
        else:
            l_rgb2.off()

    elif port == 9:
        if status == 1:
            l_rgb3.on()
        else:
            l_rgb3.off()

    else:
        print("Wrong Command : Exemple switch(3,1)")

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
        port = int(commande[1])

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
# Lancement
# ==========================

if __name__ == "__main__":

    switchSetup()
    led_rgb()

    # Tout éteindre au démarrage
    set_all_switch_off()

    try:
        main()

    except KeyboardInterrupt:
        print("\nInterruption clavier")
        set_all_switch_off()
