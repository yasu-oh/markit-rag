import argparse
import sys
import re
import datetime
from pathlib import Path
from tqdm import tqdm
from markitdown import MarkItDown


_STRICT_NAN_SNIPPETS = ["| NaN |", "|  NaN  |", "| NAN |", "| nan |"]


def add_metadata_frontmatter(md_text: str, src_path: Path) -> str:
    """
    ベクトルDBでの追跡を容易にするため、ファイルの先頭にYAML Frontmatterを追加する。
    """
    now = datetime.datetime.now().isoformat()
    frontmatter = (
        "---\n"
        f"filename: {src_path.name}\n"
        f"converted_at: {now}\n"
        "---\n\n"
    )
    return frontmatter + md_text


def ensure_header_spacing(md_text: str) -> str:
    """
    チャンキング精度向上のため、ヘッダー (#) の前に必ず空行を挿入する。
    """
    # 行頭の # の前に空行がない場合、空行を挿入（先頭行を除く）
    return re.sub(r'([^\n])\n(#{1,6}\s)', r'\1\n\n\2', md_text)


def iter_files(root: Path):
    if root.is_file():
        yield root
        return
    for p in root.rglob("*"):
        if p.is_file():
            yield p


def normalize_markdown(md_text: str) -> str:
    if not md_text:
        return md_text

    # 連続する空白を1つにまとめる
    md = collapse_spaces(md_text)
    # NaNセルを空セルに置換
    md = replace_nan_cells(md)
    # 空行を削除
    md = remove_empty_lines(md)
    # 末尾の空白セルを削除
    md = remove_trailing_empty_cells(md)
    # 3回以上の連続改行を2回改行に変換
    md = normalize_line_breaks(md)
    # チャンキング向上のためヘッダー前後の空行を調整
    md = ensure_header_spacing(md)

    return md


def collapse_spaces(md_text: str) -> str:
    """
    全角空白やタブなどのあらゆる空白文字を半角空白に変換し、
    連続する空白を一つの半角空白にまとめる（改行は維持）。
    """
    return re.sub(r'[^\S\r\n]+', ' ', md_text)


def replace_nan_cells(md_text: str) -> str:
    pattern = re.compile(r'\|\s*(?:`?(?:NaN|null|None|NAN|nan)`?)\s*\|', re.IGNORECASE)
    md = pattern.sub("|  |", md_text)
    for s in _STRICT_NAN_SNIPPETS:
        md = md.replace(s, "|  |")

    return md


def remove_empty_lines(md_text: str) -> str:
    lines = md_text.splitlines()
    cleaned_lines = [line for line in lines if not re.match(r'^\s*\|\s*(\|\s*)*$', line)]

    return '\n'.join(cleaned_lines)


def remove_trailing_empty_cells(md_text: str) -> str:
    lines = md_text.splitlines()
    cleaned_lines = []
    for line in lines:
        if line.strip().startswith('|') and line.strip().endswith('|'):
            # 末尾の空白セルを削除
            cleaned = re.sub(r'\s*\|\s*$', '', line)
            cleaned = re.sub(r'\s*\|\s*(\|\s*)*$', '', cleaned)
            cleaned_lines.append(cleaned)
        else:
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


def normalize_line_breaks(md_text: str) -> str:
    normalized = re.sub(r'\n{3,}', '\n\n', md_text)

    return normalized


def convert_with_markitdown(md_engine: MarkItDown, src: Path) -> str:
    try:
        result = md_engine.convert(str(src))
    except Exception as e:
        raise RuntimeError(f"convert failed for {src}: {e}") from e

    for attr in ("text_content", "content", "markdown", "md", "document", "text"):
        if hasattr(result, attr):
            val = getattr(result, attr)
            if isinstance(val, str) and val.strip():
                return val

    if isinstance(result, dict):
        for k in ("text_content", "content", "markdown", "md", "document", "text"):
            if k in result and isinstance(result[k], str) and result[k].strip():
                return result[k]

    return str(result)


def out_path_for(src_path: Path, in_root: Path, out_root: Path) -> Path:
    rel = src_path.relative_to(in_root if in_root.is_dir() else src_path.parent)

    return (out_root / rel).with_suffix(".md")


def main():
    ap = argparse.ArgumentParser(description="Convert file(s)/folder to Markdown via markitdown, with NaN cell cleanup.")
    ap.add_argument("input", type=str, help="入力パス（ファイル or ディレクトリ）")
    ap.add_argument("--out", type=str, default="markdown_output", help="出力ディレクトリ")
    ap.add_argument("--overwrite", action="store_true", help="同名ファイルを上書き")
    ap.add_argument("--verbose", action="store_true", help="詳細ログ")
    args = ap.parse_args()

    in_path = Path(args.input).expanduser().resolve()
    if not in_path.exists():
        print(f"ERROR: 入力パスが見つかりません: {in_path}", file=sys.stderr)
        sys.exit(1)

    out_root = Path(args.out).expanduser().resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    md_engine = MarkItDown()
    files = list(iter_files(in_path))
    if not files:
        print("INFO: 変換対象ファイルが見つかりません。", file=sys.stderr)
        sys.exit(0)

    pbar = tqdm(files, ncols=100, desc="Converting", unit="file")

    n_ok = n_skip = n_fail = 0

    for src in pbar:
        try:
            dest = out_path_for(src, in_path, out_root)
            dest.parent.mkdir(parents=True, exist_ok=True)

            if dest.exists() and not args.overwrite:
                n_skip += 1
                if args.verbose:
                    tqdm.write(f"[SKIP] {src} -> {dest} (exists)")
                continue

            md_text = convert_with_markitdown(md_engine, src)
            md_text = normalize_markdown(md_text)
            md_text = add_metadata_frontmatter(md_text, src)
            md_text = ensure_header_spacing(md_text)

            with open(dest, "w", encoding="utf-8", newline="\n") as f:
                f.write(md_text)

            n_ok += 1
            if args.verbose:
                tqdm.write(f"[OK]   {src} -> {dest}")

        except Exception as e:
            n_fail += 1
            tqdm.write(f"[FAIL] {src}: {e}")

    print("\nSummary")
    print(f"  OK   : {n_ok}")
    print(f"  SKIP : {n_skip}  (--overwrite で上書き)")
    print(f"  FAIL : {n_fail}")
    print(f"\nOutput dir: {out_root}")


if __name__ == "__main__":
    main()
