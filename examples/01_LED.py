#!/usr/bin/env/python
# File name   : 01_LED.py
# Website     : www.Adeept.com
# Author      : Adeept
# Date        : 2025/03/10

import time
from gpiozero import LED

def switchSetup():
    global led1,led2,led3
    led1 = LED(9)
    led2 = LED(25)
    led3 = LED(11)
def led_rgb():
    global r_gb1,r_gb2,r_rgb3, l_rgb1, l_rgb2, l_rgb3
    r_gb1= LED(1)
    r_gb2= LED(5)
    r_gb3= LED(6)
    l_gb1= LED(19)
    l_gb2= LED(13)
    l_gb3= LED(0)

def switch(port, status):
    if port == 1:
        if status == 1:
            led1.on()
        elif status == 0:
            led1.off()
    elif port == 2:
        if status == 1:
            led2.on()
        elif status == 0:
            led2.off()
    elif port == 3:
        if status == 1:
            led3.on()
        elif status == 0:
            led3.off()
    elif port == 4:
        if status == 0:
            r_rgb1.on()
        elif status == 1:
            r_rgb1.off()
    elif port == 5:
        if status == 0:
            r_rgb2.on()
        elif status == 1:
            r_rgb2.off()
    elif port == 6:
        if status == 0:
            r_rgb3.on()
        elif status == 1:
            r_rgb3.off()
    elif port == 7:
        if status == 0:
            l_rgb1.on()
        elif status == 1:
            l_rgb1.off()
    elif port == 8:
        if status == 0:
            l_rgb2.on()
        elif status == 1:
            l_rgb2.off()
    elif port == 9:
        if status == 0:
            l_rgb3.on()
        elif status == 1:
            l_rgb3.off()
    else:
        print('Wrong Command: Example--switch(3, 1)->to switch on port3')

def set_all_switch_off():
   for port in range (1,10):
       switch (port,0)

PORT_NAMES = {
    1: 'LED 1',
    2: 'LED 2',
    3: 'LED 3',
    4: 'Right Rouge',
    5: 'Right Vert',
    6: 'Right Bleu',
    7: 'Left Rouge',
    8: 'Left Vert',
    9: 'Left Bleu',
}
 
def main():
    print("=== Contrôle manuel des LEDs ===")
    print("11 à 19 → allumer LED 1 à 9")
    print("21 à 29 → éteindre LED 1 à 9")
    print("00       → éteindre toutes les LEDs")
    print("99       → quitter")

    while True:
        commande = input("\nCommande : ").strip()
 
        # Vérification format
        if len(commande) != 2 or not commande.isdigit():
            print("Format invalide. Entrez 2 chiffres (ex: 11, 23, 00, 99)")
            continue
 
        # Cas spéciaux
        if commande == '99':
            print("Arrêt du programme.")
            set_all_switch_off()
            break
 
        if commande == '00':
            set_all_switch_off()
            print("Toutes les LEDs éteintes.")
            continue
 
        # Décodage
        action = int(commande[0])  # 1 = allumer, 2 = éteindre
        port   = int(commande[1])  # 1 à 9
 
        # Vérification port
        if port < 1 or port > 9:
            print("Port invalide. Choisir entre 1 et 9.")
            continue
 
        # Exécution
        if action == 1:
            switch(port, 1)
            print(f"{PORT_NAMES[port]} allumée.")
        elif action == 2:
            switch(port, 0)
            print(f"{PORT_NAMES[port]} éteinte.")
        else:
            print("Action invalide. Utiliser 1x pour allumer, 2x pour éteindre.")
 

if __name__ == "__main__":
    switchSetup()
    led_rgb()
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterruption clavier.")
        set_all_switch_off()
