# ========================
# Robot trop à droite
# corriger GAUCHE
# ========================

elif etat == (1,1,0):

    dernier_cote = -1

    tourner(GAUCHE_LEGER)
    robot.set_motor(1,VITESSE_VIRAGE)


elif etat == (1,0,0):

    dernier_cote = -1

    tourner(GAUCHE_FORT)
    robot.set_motor(1,VITESSE_RECUP)



# ========================
# Robot trop à gauche
# corriger DROITE
# ========================

elif etat == (0,1,1):

    dernier_cote = 1

    tourner(DROITE_LEGER)
    robot.set_motor(1,VITESSE_VIRAGE)


elif etat == (0,0,1):

    dernier_cote = 1

    tourner(DROITE_FORT)
    robot.set_motor(1,VITESSE_RECUP)
