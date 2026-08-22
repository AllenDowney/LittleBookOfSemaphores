# Quarto HTML book

Scaffold for an HTML edition of *The Little Book of Semaphores*, with
optional Sync embeds (Task 23).

## Layout

| Choice | Decision |
|--------|----------|
| Project location | `quarto/` subdirectory (same as ThinkJava2) |
| Config file | `_quarto.yml` (Quarto book project) |
| Output | `quarto/_book/` (gitignored; rebuild with `make html`) |
| Sync assets | `quarto/assets/sync/` (copied from `web/` + `code/` by Make) |
| LaTeX PDF | Unchanged under `book/` for now |

## Prerequisites

Install Quarto externally: <https://quarto.org/docs/get-started/>

This repo’s conda env does **not** install Quarto (CLI is separate).

## Commands

From the **repository root**:

```bash
make html           # sync assets + render → quarto/_book/index.html
make html-preview   # sync assets + live preview
make quarto-sync-assets   # copy Sync embed files only
```

From `quarto/` (after assets are synced):

```bash
quarto render
quarto preview
```

## Sync embeds (Task 23)

Authoring in `.qmd`:

```markdown
::: {.sync example="mutex.py"}
:::
```

- `file=` is accepted as an alias for `example=`
- HTML only: the Lua filter (`filters/sync.lua`) emits a `.sync-embed`
  mount; `assets/sync/sync_embed.js` hydrates it with Pyodide
- Example sources live under `assets/sync/examples/` (copied from
  `code/sync_code/` by `make quarto-sync-assets`)
- Canonical embed sources: `web/sync_embed.js`, `web/sync_embed.css`

Until Pyodide loads, readers see a pending code placeholder (same idea as
ThinkJava2’s javarunner pending state).

## LaTeX conversion (future)

ThinkJava2’s conversion tooling lives under `~/ThinkJava2/quarto/`:

- `convert.py` — normalize custom LaTeX before Pandoc
- `split_book.py` / related Makefile targets — chapter `.qmd` files
- Notes in `QUARTO_CONVERSION_SUMMARY.md`

Plan: adapt those scripts for `book/book.tex` rather than hand-porting
the whole book at once.

## Next Sync book tasks

- Task 24: wire chapter examples from `sync_code/`
- Task 25: multi-instance + lazy Pyodide
- Task 26: publish Quarto+Sync to Pages
