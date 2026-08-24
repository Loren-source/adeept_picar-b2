# Adeept PiCar-B2 – Robot autonome (Raspberry Pi)

Fork du dépôt officiel [adeept/adeept_picar-b2](https://github.com/adeept/adeept_picar-b2), enrichi dans le cadre du **Mastercamp EFREI** avec des algorithmes de navigation autonome développés sur la plateforme robotique **PiCar-B2** (Raspberry Pi + capteurs IR + servomoteurs).

## Ce qui a été développé (dossier `prog/`)

Le dossier `examples/` reste celui d'origine Adeept (code de référence du fabricant). **Tout le développement personnel a été fait dans `prog/`** :

**Navigation autonome**
- `lineTracking.py`, `suivi-ligne.py`, `lignerouge.py` — suivi de ligne par capteurs infrarouges
- `lightTracking.py` — suivi de source lumineuse
- `EvitementsObstacle.py`, `obstacle.py`, `obstacle_labyrinthe.py`, `avancer-distance-check.py` — détection et évitement d'obstacles (capteur ultrason), y compris en environnement labyrinthe

**Vision / détection**
- `arrow_detector.py` — détection de flèches directionnelles
- `panel_detector.py` — détection de panneaux
- `Caméra.py` — gestion du flux caméra

**Orchestration de mission**
- `main.py` — point d'entrée du programme
- `mission_manager.py`, `mission_state.py` — gestion des états et de l'enchaînement des missions du robot
- `resource_manager.py` — gestion des ressources (capteurs/actionneurs partagés entre threads)

**Contrôle matériel bas niveau**
- `motor.py`, `move.py` — pilotage moteurs et déplacements
- `servo.py`, `RPIservo.py`, `initPosServos.py` — pilotage et initialisation des servomoteurs
- `ultra.py` — capteur ultrason
- `LED.py`, `RGB.py` / `rgb.py`, `ws2812.py`, `Spi_WS2812.py` — pilotage des LEDs (dont bandeau WS2812)
- `buzzer.py` — buzzer
- `BatteryLevelMonitoring.py` — surveillance du niveau de batterie

**Tests et étapes de développement (Mastercamp)**
- `E0.py`, `Tache10.py`, `tache11.py`, `test.py`, `test_main_menu.py` — scripts de test et jalons du projet

**Système**
- `setup.py` — configuration/installation
- `wifi_hotspot_manager.sh` — gestion du point d'accès Wi-Fi du robot

## Matériel

- Raspberry Pi (châssis PiCar-B2, Adeept)
- Capteurs infrarouges (suivi de ligne)
- Capteur ultrason (évitement d'obstacles)
- Capteurs de luminosité (suivi de lumière)
- Caméra (détection de flèches/panneaux)
- Bandeau LED WS2812 + buzzer
- Servomoteurs (direction + caméra)

## Structure du repo

```
├── examples/               # Code d'exemple fourni par Adeept (base d'origine)
├── prog/                   # Programme du robot, développé pendant le Mastercamp
│   ├── main.py              # Point d'entrée
│   ├── mission_manager.py / mission_state.py   # Orchestration des missions
│   ├── lineTracking.py / lightTracking.py       # Suivi de ligne / lumière
│   ├── EvitementsObstacle.py / obstacle*.py      # Évitement d'obstacles
│   ├── arrow_detector.py / panel_detector.py     # Vision
│   ├── motor.py / servo.py / ultra.py / LED.py / buzzer.py  # Contrôle matériel
│   └── ...
├── web/                    # Interface web de contrôle du robot
├── flask-video-streaming/    # Streaming vidéo (sous-module)
└── README.md
```

## Contexte

Projet réalisé lors du Mastercamp EFREI Paris, incluant également un volet gestion de projet dont le planning,registre des risques non présent dans ce dépôt technique.

## Origine

Base matérielle et logicielle initiale : [Adeept](https://github.com/adeept/adeept_picar-b2) et l'école. Ce fork contient les développements algorithmiques réalisés dans le cadre du projet académique.

## Auteur

Loren Koudoukpo et son groupe — EFREI Paris, Master Camp, Systèmes embarqués
