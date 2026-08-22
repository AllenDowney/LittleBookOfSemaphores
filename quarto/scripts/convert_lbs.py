#!/usr/bin/env python3
"""
Task 27/31: Convert book/book.tex to Quarto section pages.

Pipeline:
  1. Preprocess LaTeX (listings, lstinputlisting, cleanup)
  2. Split at \\chapter / \\section boundaries
  3. Pandoc each chunk → quarto/sections/*.qmd
  4. Write quarto/_quarto.yml (parts = LaTeX chapters)

Usage (from repo root):
  python quarto/scripts/convert_lbs.py
  make quarto-convert
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BOOK_TEX = REPO_ROOT / "book" / "book.tex"
QUARTO_DIR = REPO_ROOT / "quarto"
SECTIONS_DIR = QUARTO_DIR / "sections"
ASSETS_DIR = QUARTO_DIR / "assets" / "book"
BUILD_DIR = QUARTO_DIR / "build"
QUARTO_YML = QUARTO_DIR / "_quarto.yml"
EXTRACT_LABELS = REPO_ROOT.parent / "ThinkJava2" / "quarto" / "extract-labels.lua"

PANDOC_PREAMBLE = r"""
\documentclass{article}
\usepackage{listings}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{color}
\usepackage{amsmath}
\definecolor{light-gray}{gray}{0.95}
\lstset{basicstyle=\tt, frame=single,
  backgroundcolor=\color{light-gray}, escapeinside={(*}{*)},
  numbers=left, numberstyle=\tiny, numbersep=10pt}
\begin{document}
""".strip()

PANDOC_POSTAMBLE = r"\end{document}"


@dataclass
class SectionChunk:
    chapter_title: str
    section_title: str
    slug: str
    body_tex: str
    unnumbered: bool = False
    is_chapter_intro: bool = False


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\$[^$]+\$", "", text)  # drop simple math
    text = text.replace("'", "")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "section"


def read_braced_title(text: str, open_brace: int) -> tuple[str, int]:
    """Return (title, index after closing brace). open_brace points at '{'."""
    depth = 0
    i = open_brace
    start = open_brace + 1
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text):
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i], i + 1
        i += 1
    raise ValueError(f"Unmatched brace at {open_brace}")


def strip_latex_comments(text: str) -> str:
    """Remove unescaped % comments (line remainder)."""
    out_lines: list[str] = []
    for line in text.splitlines():
        cleaned: list[str] = []
        i = 0
        while i < len(line):
            if line[i] == "%" and (i == 0 or line[i - 1] != "\\"):
                break
            cleaned.append(line[i])
            i += 1
        out_lines.append("".join(cleaned).rstrip())
    return "\n".join(out_lines)


def is_commented_command(text: str, start: int) -> bool:
    """True if the command at `start` appears after an unescaped % on its line."""
    line_start = text.rfind("\n", 0, start) + 1
    prefix = text[line_start:start]
    i = 0
    while i < len(prefix):
        if prefix[i] == "%" and (i == 0 or prefix[i - 1] != "\\"):
            return True
        i += 1
    return False


def is_meaningful_intro(body: str) -> bool:
    """Chapter intros with only labels/whitespace should not become pages."""
    body = strip_latex_comments(body)
    body = re.sub(r"\\label\{[^}]*\}", "", body)
    body = re.sub(r"\\clearemptydoublepage", "", body)
    return bool(body.strip())


def find_markers(text: str) -> list[tuple[int, str, str, bool]]:
    """Return sorted (pos, kind, title, starred) for chapter/section commands."""
    markers: list[tuple[int, str, str, bool]] = []
    for kind in ("chapter", "section"):
        pattern = re.compile(rf"\\{kind}\*?\s*\{{", re.IGNORECASE)
        for m in pattern.finditer(text):
            if is_commented_command(text, m.start()):
                continue
            starred = "*" in text[m.start() : m.end()]
            title, end = read_braced_title(text, m.end() - 1)
            markers.append((m.start(), kind, title.strip(), starred))
    markers.sort(key=lambda x: x[0])
    return markers


def preprocess_latex(source: str, book_dir: Path) -> str:
    text = source

    # Drop everything before first \chapter (title page, maketitle, etc.)
    first_ch = re.search(r"\\chapter", text)
    if first_ch:
        text = text[first_ch.start() :]

    # Drop trailing \end{document} if present
    text = re.sub(r"\\end\{document\}\s*$", "", text)

    replacements = [
        (r"\\clearemptydoublepage", ""),
        (r"\\blankpage", ""),
        (r"\\frontmatter", ""),
        (r"\\mainmatter", ""),
        (r"\\backmatter", ""),
        (r"\\appendix\b", ""),
        (r"\\index\{[^}]*\}", ""),
        (r"\\makeindex", ""),
        (r"\\pagestyle\{[^}]*\}", ""),
        (r"\\lhead\[[^\]]*\]\{[^}]*\}", ""),
        (r"\\rhead\[[^\]]*\]\{[^}]*\}", ""),
        (r"\\cfoot\{\}", ""),
        (r"\\renewcommand\{\\chaptermark\}\[[^\]]*\]\{[^}]*\}", ""),
        (r"\\renewcommand\{\\sectionmark\}\[[^\]]*\]\{[^}]*\}", ""),
    ]
    for pat, repl in replacements:
        text = re.sub(pat, repl, text)

    # listings often use an empty {} argument that breaks Pandoc
    text = re.sub(r"(\\begin\{lstlisting\}(?:\[[^\]]*\])?)\{\}", r"\1", text)

    # Inline external listing files
    def expand_lstinputlisting(match: re.Match[str]) -> str:
        opts = match.group(1) or ""
        path = match.group(2).strip()
        src = (book_dir / path).resolve()
        if not src.exists():
            src = (REPO_ROOT / path.lstrip("./")).resolve()
        if not src.exists():
            return f"% MISSING LISTING: {path}\n"
        code = src.read_text(encoding="utf-8", errors="replace")
        return f"\\begin{{lstlisting}}{opts}\n{code}\\end{{lstlisting}}\n"

    text = re.sub(
        r"\\lstinputlisting(\[[^\]]*\])?\{([^}]+)\}",
        expand_lstinputlisting,
        text,
        flags=re.DOTALL,
    )

    # Fix figure path for Quarto assets copy
    text = text.replace("{table.eps}", "{assets/book/table.eps}")

    return text


def split_into_sections(tex: str) -> list[SectionChunk]:
    markers = find_markers(tex)
    if not markers:
        raise RuntimeError("No \\chapter or \\section markers found")

    chunks: list[SectionChunk] = []
    used_slugs: dict[str, int] = {}
    current_chapter = ""
    current_chapter_starred = False

    def unique_slug(title: str) -> str:
        base = slugify(title)
        n = used_slugs.get(base, 0)
        used_slugs[base] = n + 1
        return base if n == 0 else f"{base}-{n + 1}"

    for idx, (pos, kind, title, starred) in enumerate(markers):
        next_pos = markers[idx + 1][0] if idx + 1 < len(markers) else len(tex)
        header_end = tex.find("{", pos)
        _, body_start = read_braced_title(tex, header_end)

        if kind == "chapter":
            current_chapter = title
            current_chapter_starred = starred
            # Chapter intro: body until next marker (if next is section in same chapter)
            if idx + 1 < len(markers) and markers[idx + 1][1] == "section":
                intro = tex[body_start : markers[idx + 1][0]].strip()
                if is_meaningful_intro(intro):
                    slug = unique_slug(title)
                    chunks.append(
                        SectionChunk(
                            chapter_title=title,
                            section_title=title,
                            slug=slug,
                            body_tex=intro,
                            unnumbered=starred,
                            is_chapter_intro=True,
                        )
                    )
            continue

        body = tex[body_start:next_pos].strip()
        slug = unique_slug(title)
        chunks.append(
            SectionChunk(
                chapter_title=current_chapter,
                section_title=title,
                slug=slug,
                body_tex=body,
                unnumbered=starred,
            )
        )

    return chunks


def pandoc_chunk(body_tex: str, resource_paths: list[Path]) -> str:
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    tex_path = BUILD_DIR / "chunk.tex"
    full = f"{PANDOC_PREAMBLE}\n{body_tex}\n{PANDOC_POSTAMBLE}\n"
    tex_path.write_text(full, encoding="utf-8")

    cmd = [
        "pandoc",
        str(tex_path),
        "--from=latex",
        "--to=markdown",
        "--wrap=none",
        "-o",
        "-",
    ]
    for path in resource_paths:
        cmd.extend(["--resource-path", str(path)])
    if EXTRACT_LABELS.exists():
        cmd.extend(["--lua-filter", str(EXTRACT_LABELS)])

    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def yaml_quote(value: str) -> str:
    if re.search(r'[:#"\'\n]', value):
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def write_qmd(chunk: SectionChunk, markdown: str) -> Path:
    SECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    path = SECTIONS_DIR / f"{chunk.slug}.qmd"

    yaml_lines = ["---", f"title: {yaml_quote(chunk.section_title)}"]
    if chunk.unnumbered:
        yaml_lines.append("number-sections: false")
    yaml_lines.append("---")
    yaml_lines.append("")

    md = markdown.strip()
    md = re.sub(
        r"\]\(greenteapress\.com/",
        "](http://greenteapress.com/",
        md,
    )
    # Drop a duplicate top-level heading if Pandoc emitted one
    first_line = md.split("\n", 1)[0] if md else ""
    if first_line.startswith("# "):
        md = md.split("\n", 1)[1].lstrip("\n") if "\n" in md else ""

    path.write_text("\n".join(yaml_lines) + md + "\n", encoding="utf-8")
    return path


def generate_quarto_yml(chunks: list[SectionChunk], section_files: list[Path]) -> None:
    """Write _quarto.yml with part groupings per LaTeX chapter."""
    out: list[str] = [
        "project:",
        "  type: book",
        "  output-dir: _book",
        "",
        "book:",
        '  title: "The Little Book of Semaphores"',
        '  author: "Allen B. Downey"',
        "  date: today",
        "  page-navigation: true",
        "  repo-url: https://github.com/AllenDowney/LittleBookOfSemaphores",
        "  repo-actions: [source]",
        "  chapters:",
        "    - index.qmd",
    ]

    current_part: str | None = None
    for chunk, path in zip(chunks, section_files):
        rel = path.relative_to(QUARTO_DIR).as_posix()
        if chunk.chapter_title != current_part:
            out.append(f"    - part: {yaml_quote(chunk.chapter_title)}")
            out.append("      chapters:")
            current_part = chunk.chapter_title
        out.append(f"        - {rel}")

    out.extend(
        [
            "",
            "filters:",
            "  - filters/sync.lua",
            "",
            "resources:",
            "  - assets/sync/**",
            "  - assets/book/**",
            "",
            "format:",
            "  html:",
            "    theme: cosmo",
            "    toc: true",
            "    number-sections: true",
            "    css:",
            "      - styles.css",
            "      - assets/sync/sync_embed.css",
            "    include-in-header:",
            "      - text: |",
            '          <script type="module" src="assets/sync/sync_embed.js"></script>',
            "    site-url: https://allendowney.github.io/LittleBookOfSemaphores/",
            "",
            "execute:",
            "  freeze: auto",
            "  enabled: false",
            "",
        ]
    )
    QUARTO_YML.write_text("\n".join(out), encoding="utf-8")


def update_index_qmd() -> None:
    """Point index at the converted preface section if present."""
    preface = SECTIONS_DIR / "preface.qmd"
    index = QUARTO_DIR / "index.qmd"
    if not preface.exists():
        return
    text = preface.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        body = parts[2].strip() if len(parts) > 2 else ""
    else:
        body = text
    index.write_text(
        "---\ntitle: \"Preface\"\nnumber-sections: false\n---\n\n" + body + "\n",
        encoding="utf-8",
    )


def main() -> int:
    if not BOOK_TEX.exists():
        print(f"Missing {BOOK_TEX}", file=sys.stderr)
        return 1

    print(f"Reading {BOOK_TEX}")
    raw = BOOK_TEX.read_text(encoding="utf-8")
    tex = preprocess_latex(raw, BOOK_TEX.parent)

    print("Splitting into sections…")
    chunks = split_into_sections(tex)
    print(f"  {len(chunks)} section pages")

    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    eps = BOOK_TEX.parent / "table.eps"
    if eps.exists():
        shutil.copy2(eps, ASSETS_DIR / "table.eps")

    resource_paths = [QUARTO_DIR, BOOK_TEX.parent, REPO_ROOT / "code"]

    # Remove old generated sections (keep directory)
    if SECTIONS_DIR.exists():
        for old in SECTIONS_DIR.glob("*.qmd"):
            old.unlink()

    section_files: list[Path] = []
    for i, chunk in enumerate(chunks, 1):
        print(f"  [{i}/{len(chunks)}] {chunk.chapter_title} → {chunk.section_title}")
        md = pandoc_chunk(chunk.body_tex, resource_paths)
        path = write_qmd(chunk, md)
        section_files.append(path)

    # Drop duplicate preface from sections list if copied to index.qmd
    filtered: list[tuple[SectionChunk, Path]] = []
    for chunk, path in zip(chunks, section_files):
        if chunk.is_chapter_intro and chunk.slug == "preface":
            continue
        filtered.append((chunk, path))

    update_index_qmd()
    generate_quarto_yml([c for c, _ in filtered], [p for _, p in filtered])

    sample = QUARTO_DIR / "sample.qmd"
    if sample.exists():
        sample.unlink()
        print("Removed placeholder sample.qmd")

    print(f"Wrote {len(filtered)} sections under {SECTIONS_DIR}")
    print(f"Wrote {QUARTO_YML}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
