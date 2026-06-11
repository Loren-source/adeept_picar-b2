import argparse
import atexit
import importlib.util
import inspect
import json
import sys
import threading
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent
CURRENT = Path(__file__).stem


def discover_modules() -> Dict[str, Any]:
    modules: Dict[str, Any] = {}
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    for path in ROOT.glob("*.py"):
        if path.name in {f"{CURRENT}.py", "__init__.py"}:
            continue
        module_name = path.stem
        spec = importlib.util.spec_from_file_location(f"{ROOT.name}.{module_name}", path)
        if not spec or not spec.loader:
            continue
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as exc:
            print(f"[menu] Ignoré: {module_name} ({exc})", file=sys.stderr)
            continue
        modules[module_name] = module
    return modules


MODULES = discover_modules()


def discover_members() -> Dict[str, Any]:
    members: Dict[str, Any] = {}
    for module_name, module in MODULES.items():
        for member_name, member in inspect.getmembers(module):
            if inspect.isfunction(member) and member.__module__ == module.__name__:
                members[f"{module_name}.{member_name}"] = member
            elif inspect.isclass(member) and member.__module__ == module.__name__:
                members[f"{module_name}.{member_name}"] = member
    return members


CALLABLES = discover_members()


def list_modules() -> List[str]:
    return sorted(MODULES.keys())


def list_callables() -> List[str]:
    return sorted(CALLABLES.keys())


def resolve_callable(name: str) -> Any:
    if name in CALLABLES:
        return CALLABLES[name]
    candidates = [key for key in CALLABLES if key.endswith(f".{name}")]
    if len(candidates) == 1:
        return CALLABLES[candidates[0]]
    raise KeyError(f"Unknown callable: {name!r}")


def parse_json_or_string(value: Optional[str]) -> Any:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


def normalize_arg_list(values: Optional[List[str]], count: int) -> List[Optional[str]]:
    if not values:
        return [None] * count
    if len(values) == count:
        return values
    if len(values) == 1:
        return values * count
    values = list(values)
    while len(values) < count:
        values.append(values[-1])
    return values


def call_target(name: str, args: Optional[List[Any]] = None, kwargs: Optional[Dict[str, Any]] = None) -> Any:
    target = resolve_callable(name)
    args = args or []
    kwargs = kwargs or {}
    if inspect.isclass(target):
        return target(*args, **kwargs)
    return target(*args, **kwargs)


def run_tasks(tasks: List[Dict[str, Any]], parallel: bool = False) -> List[Tuple[str, Any, str]]:
    results: List[Tuple[str, Any, str]] = []
    if parallel:
        with ThreadPoolExecutor(max_workers=min(len(tasks), 32)) as executor:
            futures = {
                executor.submit(call_target, task["name"], task.get("args"), task.get("kwargs")): task
                for task in tasks
            }
            for future in as_completed(futures):
                task = futures[future]
                try:
                    results.append((task["name"], future.result(), "ok"))
                except Exception as exc:
                    results.append((task["name"], exc, "error"))
    else:
        for task in tasks:
            try:
                result = call_target(task["name"], task.get("args"), task.get("kwargs"))
                results.append((task["name"], result, "ok"))
            except Exception as exc:
                results.append((task["name"], exc, "error"))
    return results


# Persistent executor for fire-and-forget background tasks
_bg_executor = ThreadPoolExecutor(max_workers=8, thread_name_prefix="adeept_bg")
_bg_tasks: Dict[str, Tuple[str, "Future[Any]"]] = {}
_bg_lock = threading.Lock()

atexit.register(_bg_executor.shutdown, wait=False)


def submit_background(name: str, args: Optional[List[Any]] = None, kwargs: Optional[Dict[str, Any]] = None) -> str:
    resolve_callable(name)  # validate now so KeyError is raised in the calling thread, not silently in the worker
    future = _bg_executor.submit(call_target, name, args or [], kwargs or {})
    with _bg_lock:
        task_id = f"{name}#{len(_bg_tasks) + 1}"
        _bg_tasks[task_id] = (name, future)
    return task_id


def get_background_status() -> List[Tuple[str, str, Any]]:
    with _bg_lock:
        snapshot = list(_bg_tasks.items())
    status_list = []
    for task_id, (_name, future) in snapshot:
        if future.done():
            try:
                result = future.result()
                status_list.append((task_id, "terminé", result))
            except Exception as exc:
                status_list.append((task_id, "erreur", exc))
        elif future.running():
            status_list.append((task_id, "en cours", None))
        else:
            status_list.append((task_id, "en attente", None))
    return status_list


def print_menu() -> str:
    lines = [
        "Menu simple pour le robot Adeept",
        "================================",
        "",
        "Bienvenue ! Ce menu vous permet d'utiliser le robot sans devoir lire toute la documentation.",
        "",
        "Options rapides:",
        "  1. Liste des actions disponibles",
        "  2. Exécuter une action",
        "  3. Voir les modules",
        "  4. Aide rapide",
        "  5. Exécuter plusieurs tâches (parallèle/séquentiel)",
        "  6. Lancer une tâche en arrière-plan",
        "  7. Voir les tâches en arrière-plan",
        "  8. Quitter",
        "",
        "Exemples d'actions:",
        "  - motor.RobotMotor",
        "  - ultra.Ultrasonic",
        "  - LED.LED",
        "",
        "Lancer le menu interactif:",
        "  python prog/main.py --menu",
        "",
        "Lignes de commande utiles:",
        "  python prog/main.py --list",
        "  python prog/main.py --call motor.RobotMotor",
        "  python prog/main.py --call ultra.Ultrasonic",
        "  python prog/main.py --call motor.RobotMotor --call ultra.Ultrasonic --parallel",
        "",
        "Liste des actions:",
    ]
    for callable_name in list_callables():
        lines.append(f"  - {callable_name}")
    return "\n".join(lines)


def print_help() -> None:
    print("Aide rapide du menu :")
    print("  python prog/main.py --menu      : ouvre le menu interactif")
    print("  python prog/main.py --list      : liste les actions disponibles")
    print("  python prog/main.py --call module.member : exécute une action")
    print("  python prog/main.py --call module.member --args '[...]' --kwargs '{...}'")
    print("  python prog/main.py --call a --call b --parallel : exécute a et b en parallèle")
    print()
    print("Astuce : si vous ne connaissez pas le nom exact, commencez par --list puis choisissez l'action voulue.")


def interactive_menu() -> None:
    print("\nMenu simple pour le robot Adeept")
    print("================================")
    print("Choisissez une option :")
    print("  1) Voir les actions disponibles")
    print("  2) Exécuter une action")
    print("  3) Voir les modules disponibles")
    print("  4) Afficher l'aide rapide")
    print("  5) Exécuter plusieurs tâches (parallèle/séquentiel)")
    print("  6) Lancer une tâche en arrière-plan")
    print("  7) Voir les tâches en arrière-plan")
    print("  8) Quitter")

    while True:
        try:
            choice = input("\nVotre choix (1-8) : ").strip().lower()
        except EOFError:
            print("\nRetour au terminal.")
            return

        if choice in {"1", "actions", "liste"}:
            print("\nActions disponibles :")
            for callable_name in list_callables():
                print("  -", callable_name)

        elif choice in {"2", "run", "executer", "action"}:
            name = input("Nom de l'action à lancer (ex. motor.RobotMotor) : ").strip()
            if not name:
                print("Aucune action saisie.")
                continue
            try:
                result = call_target(name)
                print(f"\n[{name}] -> {result!r}")
            except Exception as exc:
                print(f"\nErreur lors de l'exécution de {name!r} : {exc}")

        elif choice in {"3", "modules", "modules disponibles"}:
            print("\nModules disponibles :")
            for module_name in list_modules():
                print("  -", module_name)

        elif choice in {"4", "help", "aide"}:
            print_help()

        elif choice in {"5", "multi", "parallele", "parallel"}:
            print("Entrez les actions à lancer (une par ligne, ligne vide pour terminer) :")
            names = []
            while True:
                name = input(f"  Action {len(names) + 1} (vide pour terminer) : ").strip()
                if not name:
                    break
                names.append(name)
            if not names:
                print("Aucune action saisie.")
                continue
            mode = input("Exécution parallèle ? (o/n, défaut: n) : ").strip().lower()
            use_parallel = mode in {"o", "oui", "y", "yes"}
            tasks_to_run = [{"name": n, "args": [], "kwargs": {}} for n in names]
            print(f"\nLancement {'en parallèle' if use_parallel else 'en séquence'} de {len(tasks_to_run)} tâche(s)...")
            results = run_tasks(tasks_to_run, parallel=use_parallel)
            for t_name, result, status in results:
                if status == "ok":
                    print(f"  [{t_name}] -> {result!r}")
                else:
                    print(f"  [{t_name}] ERREUR: {result}")

        elif choice in {"6", "bg", "background", "arriere-plan"}:
            name = input("Nom de l'action à lancer en arrière-plan : ").strip()
            if not name:
                print("Aucune action saisie.")
                continue
            try:
                task_id = submit_background(name)
                print(f"\nTâche lancée en arrière-plan : {task_id}")
            except KeyError as exc:
                print(f"\nErreur : {exc}")

        elif choice in {"7", "status", "statut", "bg-status"}:
            statuses = get_background_status()
            if not statuses:
                print("\nAucune tâche en arrière-plan.")
            else:
                print(f"\n{len(statuses)} tâche(s) en arrière-plan :")
                for task_id, state, result in statuses:
                    if state == "terminé":
                        print(f"  [{task_id}] terminé -> {result!r}")
                    elif state == "erreur":
                        print(f"  [{task_id}] erreur -> {result}")
                    else:
                        print(f"  [{task_id}] {state}")

        elif choice in {"8", "q", "quit", "exit", "sortir"}:
            print("Au revoir.")
            return

        else:
            print("Choix non reconnu. Tapez 1 à 8.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Menu simple pour le robot Adeept", add_help=False)
    parser.add_argument("--list-modules", action="store_true")
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--call", action="append")
    parser.add_argument("--args", action="append")
    parser.add_argument("--kwargs", action="append")
    parser.add_argument("--parallel", action="store_true")
    parser.add_argument("--menu", action="store_true")
    parser.add_argument("--help", action="store_true")
    args = parser.parse_args()

    if args.help:
        print_help()
        return

    if args.menu:
        interactive_menu()
        return

    if not any([args.list_modules, args.list, args.call]):
        if sys.stdin.isatty():
            print(print_menu())
            interactive_menu()
        else:
            print(print_menu())
            print("\nUtilisez --menu pour ouvrir le mode interactif, ou --list pour afficher les actions.")
        return

    if args.list_modules:
        for module_name in list_modules():
            print(module_name)

    if args.list:
        for callable_name in list_callables():
            print(callable_name)

    if args.call:
        arg_list = normalize_arg_list(args.args, len(args.call))
        kwarg_list = normalize_arg_list(args.kwargs, len(args.call))
        tasks: List[Dict[str, Any]] = []
        for call_name, arg_text, kwarg_text in zip(args.call, arg_list, kwarg_list):
            parsed_args = parse_json_or_string(arg_text)
            parsed_kwargs = parse_json_or_string(kwarg_text)
            if isinstance(parsed_args, list):
                call_args = parsed_args
            elif parsed_args is None:
                call_args = []
            else:
                call_args = [parsed_args]
            if isinstance(parsed_kwargs, dict):
                call_kwargs = parsed_kwargs
            elif parsed_kwargs is None:
                call_kwargs = {}
            else:
                raise ValueError("kwargs must be a JSON object")
            tasks.append({"name": call_name, "args": call_args, "kwargs": call_kwargs})
        results = run_tasks(tasks, parallel=args.parallel)
        for name, result, status in results:
            if status == "ok":
                print(f"[{name}] -> {result!r}")
            else:
                print(f"[{name}] ERROR: {result}")


if __name__ == "__main__":
    main()