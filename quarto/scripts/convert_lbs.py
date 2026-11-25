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
BOOK_BIB = REPO_ROOT / "book" / "book.bib"
SITE_URL = "https://allendowney.github.io/LittleBookOfSemaphores/"
SYNC_CODE_URL = "https://github.com/AllenDowney/LittleBookOfSemaphores/tree/master/code/sync_code"

# Sections left out of the HTML book (stubs in book.tex)
SKIP_SLUGS = {"sync-py"}

# Pandoc's rendering of \ref{label}, with the word before it if any
REF_RE = re.compile(
    r"(?:\b(Section|section|Chapter|chapter|Appendix|appendix|Lines|Line|lines|line)\s+)?"
    r"\[\\\[([^\]\\]+)\\\]\]\(#[^)]*\)\{reference-type=\"ref\" reference=\"[^\"]*\"\}"
)
# A label inside a listing, via escapeinside: (*\label{x}*) or (* \label{x} *)
CODE_LABEL_RE = re.compile(r"\s*\(\*\s*\\label\{([^}]*)\}\s*\*\)")

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


def chapter_labels(tex: str) -> dict[str, str]:
    """Labels that belong to a \\chapter (between it and the next marker): label -> title."""
    markers = find_markers(tex)
    out: dict[str, str] = {}
    for idx, (pos, kind, title, _) in enumerate(markers):
        if kind != "chapter":
            continue
        end = markers[idx + 1][0] if idx + 1 < len(markers) else len(tex)
        for label in re.findall(r"\\label\{([^}]*)\}", tex[pos:end]):
            out[label] = title
    return out


def strip_code_labels(md: str) -> tuple[str, dict[str, int]]:
    """Remove (*\\label{x}*) from code blocks; return the text and label -> line number."""
    lines = md.split("\n")
    found: dict[str, int] = {}
    in_code = False
    line_no = 0
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_code = not in_code
            line_no = 0
            continue
        if in_code:
            line_no += 1
            m = CODE_LABEL_RE.search(line)
            if m:
                found[m.group(1)] = line_no
                lines[i] = CODE_LABEL_RE.sub("", line).rstrip()
    return "\n".join(lines), found


def resolve_refs(
    chunks: list[SectionChunk], markdowns: list[str], tex: str, numbers: dict[str, int]
) -> list[str]:
    """Turn Pandoc's same-page \\ref links into links between the section pages.

    Section labels become "Section N" (N as the HTML numbers its pages), chapter labels
    the chapter's title, labels in listings "Line N" (code-line-numbers is on, as in the
    PDF). References to skipped sections (SKIP_SLUGS) are rewritten by hand below.
    """
    # label -> (slug, anchor or None); line labels -> line number
    where: dict[str, tuple[str, str | None]] = {}
    lines: dict[str, int] = {}
    for i, (chunk, md) in enumerate(zip(chunks, markdowns)):
        md, found = strip_code_labels(md)
        markdowns[i] = md
        lines.update(found)
        for label in re.findall(r"^#+ .*\{#([^}\s]+)", md, re.M):
            where[label] = (chunk.slug, label)
        for label in re.findall(r"\\label\{([^}]*)\}", chunk.body_tex):
            if label not in where and label not in found:
                where[label] = (chunk.slug, None)
    chapters = chapter_labels(tex)
    first_page = {}
    for chunk in chunks:
        first_page.setdefault(chunk.chapter_title, chunk.slug)

    def replace(m: re.Match[str], slug_here: str) -> str:
        word, label = m.group(1), m.group(2)
        if label in lines:
            in_range = m.string[: m.start()].rstrip(" \xa0").endswith(("--", "–"))
            if in_range and not word:
                return str(lines[label])  # second half of "Lines a--b"
            return f"{word or 'Line'} {lines[label]}"
        if label in chapters and chapters[label] in first_page:
            title = chapters[label]
            target = f"{first_page[title]}.qmd"
            return f"{word or 'Chapter'} [{title}]({target})"
        if label in where:
            slug, anchor = where[label]
            target = f"{slug}.qmd" + (f"#{anchor}" if anchor else "")
            if slug == slug_here and anchor:
                target = f"#{anchor}"
            if slug in numbers:
                prefix = f"{word} " if word else "Section "
                if prefix.strip().lower() in ("chapter", "appendix"):
                    prefix = "Section "
                return f"{prefix}[{numbers[slug]}]({target})"
        print(f"  unresolved reference: {label}", file=sys.stderr)
        return m.group(0)

    out = []
    for chunk, md in zip(chunks, markdowns):
        # "`sync_code/x.py` (see Sync.py)": that section is a stub, so link the file instead
        md = re.sub(
            r"`sync_code/([\w.]+)` \(see\s\[\\\[sync\.py\\\]\]\(#sync\.py\)"
            r"\{reference-type=\"ref\" reference=\"sync\.py\"\}\)",
            lambda m: f"[`sync_code/{m.group(1)}`]({SYNC_CODE_URL.replace('/tree/', '/blob/')}/{m.group(1)})",
            md,
        )
        md = REF_RE.sub(lambda m: replace(m, chunk.slug), md)
        out.append(re.sub(r"(Lines \d+)(--|–)[ \xa0]+(\d)", r"\1\2\3", md))
    return out


def number_code_blocks(md: str) -> str:
    """Number the lines of every listing, as the PDF does (lstset numbers=left), so
    "Line N" references can be followed. The listings have no language class, so
    Quarto's code-line-numbers doesn't apply; Pandoc's .numberLines does."""
    lines = md.split("\n")
    in_code = False
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped.startswith("```"):
            continue
        if not in_code:
            indent = line[: len(line) - len(stripped)]
            attrs = stripped[3:].strip()
            if attrs.startswith("{") and ".numberLines" not in attrs:
                lines[i] = f"{indent}``` {{.numberLines {attrs[1:].lstrip()}"
            elif not attrs:
                lines[i] = f"{indent}``` {{.numberLines}}"
            elif not attrs.startswith("{"):
                lines[i] = f"{indent}``` {{.{attrs} .numberLines}}"
        in_code = not in_code
    return "\n".join(lines)


def fix_citation_keys(md: str, keys: dict[str, str]) -> str:
    """Citation keys are case-sensitive in Pandoc but not in BibTeX ([@Parnas] -> parnas)."""
    return re.sub(r"\[@([^\]\s;]+)\]", lambda m: f"[@{keys.get(m.group(1).lower(), m.group(1))}]", md)


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
        "  post-render: scripts/seo_postrender.py",
        "",
        "book:",
        '  title: "The Little Book of Semaphores"',
        f"  site-url: {SITE_URL}",
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
    if BOOK_BIB.exists():
        out.append("    - references.qmd")

    out.extend(
        [
            "",
            "bibliography: ../book/book.bib",
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
            "    canonical-url: true",
            "    css:",
            "      - styles.css",
            "      - assets/sync/sync_embed.css",
            "    include-in-header:",
            "      - text: |",
            '          <script type="module" src="assets/sync/sync_embed.js"></script>',
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

    markdowns: list[str] = []
    for i, chunk in enumerate(chunks, 1):
        print(f"  [{i}/{len(chunks)}] {chunk.chapter_title} → {chunk.section_title}")
        markdowns.append(pandoc_chunk(chunk.body_tex, resource_paths))

    # Pages in the book, in order: the preface intro goes to index.qmd, stubs are left out
    def in_book(chunk: SectionChunk) -> bool:
        if chunk.is_chapter_intro and chunk.slug == "preface":
            return False
        return chunk.slug not in SKIP_SLUGS

    # Quarto's chapter numbers: every page counts, index.qmd as 1, including the ones
    # whose number is hidden (number-sections: false), so the first numbered page is 3
    numbers: dict[str, int] = {}
    page = 1
    for chunk in chunks:
        if in_book(chunk):
            page += 1
            if not chunk.unnumbered:
                numbers[chunk.slug] = page

    markdowns = resolve_refs(chunks, markdowns, tex, numbers)
    markdowns = [number_code_blocks(md) for md in markdowns]
    if BOOK_BIB.exists():
        keys = {k.lower(): k for k in re.findall(r"^@\w+\{([^,\s]+),", BOOK_BIB.read_text(), re.M)}
        markdowns = [fix_citation_keys(md, keys) for md in markdowns]
        (QUARTO_DIR / "references.qmd").write_text(
            "# References {.unnumbered}\n\n::: {#refs}\n:::\n", encoding="utf-8"
        )

    section_files = [write_qmd(chunk, md) for chunk, md in zip(chunks, markdowns)]
    filtered = [(c, p) for c, p in zip(chunks, section_files) if in_book(c)]
    for chunk, path in zip(chunks, section_files):
        if chunk.slug in SKIP_SLUGS:
            path.unlink()

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
