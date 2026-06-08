#!/usr/bin/env python3
from gpiozero import TonalBuzzer
from time import sleep

# Initialize a TonalBuzzer connected to GPIO18 (BCM)
tb = TonalBuzzer(18) 

# Define a musical tune as a sequence of notes and durations.
SONG = [
    # phrase 1
    ["C4", 0.2], [None, 0.2], ["C4", 0.6], ["E4", 0.2], ["Db4", 0.2],
    ["C4", 0.2], ["E4", 0.2], [None, 0.2], ["E4", 0.6], ["G4", 0.2],
    ["F4", 0.2], ["E4", 0.2], ["F4", 0.2], [None, 0.2], ["F4", 0.6],
    ["Ab5", 0.2], ["G4", 0.2], ["F4", 0.2], ["E4", 0.2], [None, 0.2], ["Db4", 0.6], ["C4", 0.2],
]

SONG1 = [
    # intro / riff principal
    ["A4", 0.3], ["A4", 0.3], ["A4", 0.3], ["G4", 0.3],
    ["A4", 0.3], ["A4", 0.3], ["A4", 0.3], ["G4", 0.3],

    # couplet 1
    ["A4", 0.4], ["A4", 0.2], ["G4", 0.3], ["A4", 0.3],
    ["C5", 0.6], [None, 0.1],
    ["A4", 0.4], ["G4", 0.2], ["E4", 0.3], ["G4", 0.3],
    ["A4", 0.6], [None, 0.1],

    ["A4", 0.4], ["A4", 0.2], ["G4", 0.3], ["A4", 0.3],
    ["C5", 0.6], [None, 0.1],
    ["G4", 0.4], ["E4", 0.2], ["D4", 0.3], ["E4", 0.3],
    ["A4", 0.6], [None, 0.2],

    # refrain — montée dramatique
    ["E5", 0.4], ["E5", 0.2], ["D5", 0.4],
    ["C5", 0.4], ["C5", 0.2], ["A4", 0.4],
    ["G4", 0.3], ["A4", 0.3], ["C5", 0.3], ["A4", 0.3],
    ["G4", 0.8], [None, 0.1],

    ["E5", 0.4], ["E5", 0.2], ["D5", 0.4],
    ["C5", 0.4], ["C5", 0.2], ["A4", 0.4],
    ["G4", 0.3], ["A4", 0.3], ["C5", 0.3], ["D5", 0.3],
    ["E5", 0.8], [None, 0.2],

    # pont — descente tendue
    ["C5", 0.3], ["C5", 0.3], ["C5", 0.3], ["Bb4", 0.3],
    ["A4", 0.3], ["G4", 0.3], ["A4", 0.3], ["C5", 0.3],
    ["A4", 0.6], [None, 0.1],

    ["G4", 0.3], ["G4", 0.3], ["A4", 0.3], ["G4", 0.3],
    ["E4", 0.3], ["D4", 0.3], ["E4", 0.6],
    [None, 0.2],

    # final — montée héroïque
    ["A4", 0.2], ["C5", 0.2], ["E5", 0.2], ["A5", 0.6],
    [None, 0.1],
    ["G5", 0.3], ["E5", 0.3], ["D5", 0.3], ["C5", 0.3],
    ["A4", 0.3], ["G4", 0.3],
    ["A4", 0.8], [None, 0.3],
]

def play(tune):
    """
    Play a musical tune using the buzzer.
    :param tune: List of tuples (note, duration), 
    where each tuple represents a note and its duration.
    """
    for note, duration in tune:
        print(note)  # Output the current note being played
        tb.play(note)  # Play the note on the buzzer
        sleep(float(duration))  # Delay for the duration of the note
    tb.stop()  # Stop playing after the tune is complete

if __name__ == "__main__":
    try:
        play(SONG1)  # Execute the play function to start playing the tune.

    except KeyboardInterrupt:
        # Handle KeyboardInterrupt for graceful termination
        pass
