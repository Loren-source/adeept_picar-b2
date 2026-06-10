import time
from gpiozero import LED

def switchSetup():
    global led1, led2, led3

    led1 = LED(9)
    led2 = LED(25)
    led3 = LED(11)

def led_rgb():
    global r_rgb1, r_rgb2, r_rgb3
    global l_rgb1, l_rgb2, l_rgb3

    r_rgb1 = LED(1)     # Right Rouge
    r_rgb2 = LED(5)     # Right Vert
    r_rgb3 = LED(6)     # Right Bleu

    l_rgb1 = LED(19)    # Left Rouge
    l_rgb2 = LED(13)    # Left Vert
    l_rgb3 = LED(0)     # Left Bleu


def switch(port, status):

    # LED HAL
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

    # Right RGB
    elif port == 4:
        if status == 1:
            r_rgb1.off()      # logique inversée
        else:
            r_rgb1.on()

    elif port == 5:
        if status == 1:
            r_rgb2.off()
        else:
            r_rgb2.on()

    elif port == 6:
        if status == 1:
            r_rgb3.off()
        else:
            r_rgb3.on()

    # Left RGB
    elif port == 7:
        if status == 1:
            l_rgb1.off()
        else:
            l_rgb1.on()

    elif port == 8:
        if status == 1:
            l_rgb2.off()
        else:
            l_rgb2.on()

    elif port == 9:
        if status == 1:
            l_rgb3.off()
        else:
            l_rgb3.on()

    else:
        print("Wrong Command : Exemple switch(3,1)")


def set_all_switch_off():

    # LED HAL
    for port in range(1, 4):
        switch(port, 0)

    # LED RGB (logique inversée)
    for port in range(4, 10):
        switch(port, 1)


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


def main():

    print("=== Commande manuelle des LED ===")
    print("11 à 19 : allumer les LED")
    print("21 à 29 : éteindre les LED")
    print("00 : tout éteindre")
    print("99 : quitter")

    while True:

        commande = input("\nCommande : ")

        if commande == "99":
            print("Fin du programme")
            set_all_switch_off()
            break

        elif commande == "00":
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

        # Allumer
        if action == 1:
            switch(port, 1)
            print(PORT_NAMES[port], "allumée")

        # Éteindre
        elif action == 2:
            switch(port, 0)
            print(PORT_NAMES[port], "éteinte")

        else:
            print("Commande incorrecte")

if __name__ == "__main__":

    switchSetup()
    led_rgb()

    try:
        main()

    except KeyboardInterrupt:
        print("\nInterruption clavier")
        set_all_switch_off()
