# Quarto HTML book

Scaffold for an HTML edition of *The Little Book of Semaphores*, with
optional Sync embeds (Task 23).

## Layout

| Choice | Decision |
|--------|----------|
| Project location | `quarto/` subdirectory (same as ThinkJava2) |
| Config file | `_quarto.yml` (book project; **generated** by conversion) |
| Section sources | `quarto/sections/*.qmd` (**generated** from `book/book.tex`) |
| Output | `quarto/_book/` (gitignored; rebuild with `make html`) |
| Sync assets | `quarto/assets/sync/` (copied from `web/` + `code/` by Make) |
| Book figures | `quarto/assets/book/` (e.g. `table.eps` from `book/`) |
| LaTeX PDF | Unchanged under `book/` for now |

## Prerequisites

- [Quarto CLI](https://quarto.org/docs/get-started/) (external; not in conda)
- [Pandoc](https://pandoc.org/) (usually bundled with Quarto)
- Python 3 (runs `quarto/scripts/convert_lbs.py`)

## Commands

From the **repository root**:

```bash
make quarto-convert    # book/book.tex → sections/*.qmd + _quarto.yml
make html              # render HTML book → quarto/_book/index.html
make html-dev          # short TOC via --profile dev (faster Sync embed iteration)
make html-preview      # live preview (after conversion)
make html-preview-dev  # live preview with short TOC
make publish           # push quarto/_book to gh-pages (run html first)
make html-publish      # make html && make publish
make quarto-sync-assets   # copy Sync embed files only
```

**Workflow:** edit `book/book.tex` → `make quarto-convert` → `make html`.

For Sync embed work (Task 32), use the **dev config** with a short chapter
list in [`_quarto-dev.yml`](_quarto-dev.yml): `make html-dev` or
`make html-preview-dev`. (`make html-dev` temporarily swaps in the dev
config, renders, then restores `_quarto.yml`.)

## Publish (Task 26)

Build locally, then push to the `gh-pages` branch (ThinkJava2 pattern):

```bash
make html-publish    # or: make html && make publish
```

Site URL: https://allendowney.github.io/LittleBookOfSemaphores/
(configured as `site-url` in `_quarto.yml`).

The conversion script splits at LaTeX `\section` boundaries (one HTML
page per section). LaTeX `\chapter` titles become Quarto **`part:`**
groupings in `_quarto.yml`. Preface body lands in `index.qmd`.

## Conversion pipeline (Task 27)

Script: [`scripts/convert_lbs.py`](scripts/convert_lbs.py)

1. Preprocess `book/book.tex` (listings, `\lstinputlisting`, cleanup)
2. Split at `\chapter` / `\section`
3. Pandoc each chunk → `sections/<slug>.qmd`
4. Write `_quarto.yml` with `part:` per chapter

Adapted from ThinkJava2 (`convert.py`, `split_book.py`); LBS uses
**section-level** splits instead of one file per chapter.

## Sync embeds (Task 23 / future Task 24)

Authoring in `.qmd`:

```markdown
::: {.sync example="mutex.py"}
:::
```

Sync embeds are **not** inserted by the conversion script. Task 24 will
hand-edit converted `.qmd` files where `sync_code/` examples exist.

## Next book tasks

- Task 24: add Sync embeds to converted sections
- Task 25: lazy Pyodide / shared runtime
- Task 26: publish to GitHub Pages
