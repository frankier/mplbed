# AGENTS.md

See the [README](README.md) for motivation and installation, `docs/` for docs, and docstrings in
`src/` for specifics — keep those up to date as you change code; they are the
primary documentation for humans too.

## Style — DRY and reuse first

Follow the patterns already in the codebase rather than inventing new ones.
Be succinct!

## Workflow

Work in a git worktree per task, never directly on `main`:

```sh
git worktree add ../mplbed-<task> -b <task>
```

Commit there, push with `git push -u origin <task>`, and open a pull request
with `gh pr create`. Clean up with `git worktree remove` after merge.
