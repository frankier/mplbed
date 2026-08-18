import ast
from pathlib import Path
import os, sys, glob
from dataclasses import dataclass
try:
    import questionary
    import daphne
except ImportError as e:
    e.add_note("Run ./dev_setup.py from the root and then run with `uv run python run_example.py`.")
    raise


@dataclass
class Example:
    path: Path
    flags: list[str]
    full_docstring: str
    min_docstring: str


def get_docstring(path):
    raw_tree = path.read_text()
    tree = ast.parse(raw_tree, filename=path)
    return ast.get_docstring(tree)


def get_examples():
    from inspect import cleandoc
    examples = []
    for f in glob.glob("*/*.py"):
        path = Path(f)
        if (path.parent / "__init__.py").exists():
            # Modules inside a Python package are not directly runnable.
            continue
        full_docstring = cleandoc(get_docstring(path))
        lines = full_docstring.splitlines() if full_docstring else []
        flags = []
        normal_lines = []
        for line in lines:
            if line.startswith("Flags: "):
                flags.extend((flag.strip() for flag in line.split(":", 1)[-1].strip().split(",")))
            else:
                normal_lines.append(line)
        examples.append(Example(
            path,
            flags,
            full_docstring,
            " ".join(normal_lines).strip()
        ))
    return examples


def describe_choice(example):
    if example.min_docstring:
        return f"{example.path}: {example.min_docstring}"
    else:
        return example.path


def main():
    # Find python files one subdirectory down
    os.chdir(os.path.dirname(__file__))
    examples = get_examples()
    selected = questionary.select(
        "Select an example to run:",
        choices=[
            questionary.Choice(title=describe_choice(example), value=i)
            for i, example in enumerate(examples)
        ]
    ).ask()
    selected = examples[int(selected)]
    if selected.flags:
        selected_flags = questionary.checkbox(
            "Enable flags",
            choices=selected.flags
        ).ask()
        for flag in selected_flags:
            os.environ[flag] = "1"
    selected_path = selected.path
    directory = selected_path.parent
    os.chdir(directory)
    if directory.name in {"quart", "nicegui"}:
        os.execv(sys.executable, [sys.executable, selected_path.name])
    elif directory.name == "django":
        os.execv(sys.executable, [sys.executable, "-m", "daphne", "-p", "8000", "asgi:application"])
    else:
        os.execv(sys.executable, [sys.executable, "-m", "daphne", "-p", "8000", f"{selected_path.stem}:app"])


if __name__ == "__main__":
    main()
