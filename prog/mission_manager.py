#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from resource_manager import ResourceManager
from mission_states import (
    run_mission_ir,
    run_mission_obstacle,
    run_mission_camera,
    run_mission_maze
)

class MissionManager:
    def __init__(self, templates):
        self.resources = ResourceManager()
        self.resources.init_camera_and_panels(templates)
        self.current_state = "IR_FOLLOW"

    def run(self):
        print("\n" + "="*60)
        print("  🚗 MISSION MANAGER – PARCOURS COMPLET")
        print("  Ordre : IR → Obstacles → Caméra → Labyrinthe")
        print("  Transitions : panneau 'Travaux' (x2) puis 'Tunnel'")
        print("="*60 + "\n")

        try:
            while self.current_state != "FINISH":
                print(f"[MANAGER] État : {self.current_state}")

                if self.current_state == "IR_FOLLOW":
                    next_state = run_mission_ir(self.resources, panel_name="travaux")
                elif self.current_state == "OBSTACLE_AVOID":
                    next_state = run_mission_obstacle(self.resources, panel_name="travaux")
                elif self.current_state == "LINE_CAMERA":
                    next_state = run_mission_camera(self.resources, panel_name="tunnel")
                elif self.current_state == "MAZE_NAV":
                    next_state = run_mission_maze(self.resources)
                else:
                    print(f"[MANAGER] État inconnu : {self.current_state}")
                    break

                if next_state == "FINISH":
                    print("[MANAGER] 🏁 Parcours terminé avec succès.")
                    self.current_state = "FINISH"
                else:
                    print(f"[MANAGER] Transition : {self.current_state} → {next_state}")
                    self.current_state = next_state
                    self.resources.panel_detector.counter = {k:0 for k in self.resources.panel_detector.counter}
                    time.sleep(0.5)

        except KeyboardInterrupt:
            print("\n[MANAGER] Interruption utilisateur.")
        except Exception as e:
            print(f"[MANAGER] ERREUR CRITIQUE : {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.shutdown()

    def shutdown(self):
        print("[MANAGER] Arrêt complet.")
        self.resources.stop_all()

if __name__ == "__main__":
    # Chemins des images templates des panneaux
    templates = {
        "travaux": "panneau_travaux.png",
        "tunnel": "panneau_tunnel.png",
    }
    manager = MissionManager(templates)
    manager.run()
