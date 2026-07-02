# ============================================================
# PARAMÈTRES OPTIMAUX
# ============================================================
CENTRE            = 97
SERVO_ALPHA       = 0.8          # plus réactif (0.7 → 0.8)

# Angles extrêmes (vos limites mécaniques)
ANGLE_GAUCHE_MAX  = 128          # conservez si c'est la butée
ANGLE_DROITE_MAX  = 65           # conservez si c'est la butée

# VITESSES (ajustées)
VITESSE_DROITE    = 34           # inchangée (ligne droite)
VITESSE_VIRAGE_GAUCHE = 14       # réduite de 20 → 14
VITESSE_VIRAGE_DROITE = 10       # réduite de 18 → 10 (plus faible car moins de braquage)
VITESSE_PERDU     = 2            # inchangée
VITESSE_RECH      = 2            # inchangée

# LISSAGE
VITESSE_ALPHA     = 0.3          # inchangé

# Gestion des pertes (plus de temps)
MAX_HOLD          = 80           # augmenté (60 → 80)
MAINTIEN_AVANT_BALAYAGE = 150    # augmenté (100 → 150)
DUREE_RECHERCHE   = 150          # augmenté (100 → 150)
