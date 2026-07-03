import ast
from pathlib import Path
import os, sys, glob
try:
    import questionary
    import daphne
except ImportError as e:
    e.add_note("Run ./dev_setup.py from the root and then run with `uv run python run_example.py`.")
    raise

def get_docstring(path):
    py_file = Path(path)
    raw_tree = py_file.read_text()
    tree = ast.parse(raw_tree, filename=path)
    return ast.get_docstring(tree)

def describe_choice(choice):
    from inspect import cleandoc
    docstring = get_docstring(choice)
    if docstring:
        docstring = cleandoc(docstring).strip().replace("\n", " ")
        return f"{choice}: {docstring}"
    else:
        return choice

def main():
    # Find python files one subdirectory down
    os.chdir(os.path.dirname(__file__))
    python_files = [Path(f) for f in glob.glob("*/*.py")]
    selected = questionary.select(
        "Select an example to run:",
        choices=[
            questionary.Choice(title=describe_choice(f), value=i)
            for i, f in enumerate(python_files)
        ]
    ).ask()
    selected = python_files[int(selected)]
    directory = selected.parent
    os.chdir(directory)
    if directory.name == "quart":
        os.execv(sys.executable, [sys.executable, selected.name])
    else:
        os.execv(sys.executable, [sys.executable, "-m", "daphne", "-p", "8000", f"{selected.stem}:app"])


if __name__ == "__main__":
    main()