import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent / "prog" / "main.py"


spec = importlib.util.spec_from_file_location("prog_main", MODULE_PATH)
main_module = importlib.util.module_from_spec(spec)
assert spec is not None and spec.loader is not None
spec.loader.exec_module(main_module)


class MainMenuTests(unittest.TestCase):
    def test_menu_helpers_exist(self):
        self.assertTrue(hasattr(main_module, "print_menu"))
        self.assertTrue(hasattr(main_module, "interactive_menu"))

    def test_menu_text_is_user_friendly(self):
        menu_text = main_module.print_menu()
        self.assertIn("Menu simple", menu_text)
        self.assertIn("Liste des actions", menu_text)
        self.assertIn("Exécuter une action", menu_text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
