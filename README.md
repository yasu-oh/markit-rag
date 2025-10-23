# markit-rag

**markit-rag** は、Microsoft Officeファイル（Word, Excel, PowerPointなど）をRAG向けのMarkdown形式に変換するツールです。
内部的には [markitdown](https://github.com/microsoft/markitdown) を利用し、RAG用途で問題となる `NaN` や `null` セルの除去、不要な空行・表セルの正規化を自動で行います。

## 特徴

- **markitdownベース** — Office / PDF / HTML / テキストなど多様な形式をMarkdownに変換
- **NaN / null / None の自動除去** — RAG処理で誤認される空セルを正規化
- **Markdown正規化** — 不要な空行・余分なセル・改行を自動整形
- **ディレクトリ再帰対応** — フォルダ単位で一括変換可能
- **RAG最適化済み出力** — LLMが扱いやすい構造化Markdownを生成

## インストール

Python 3.9 以降が必要です。
```bash
pip install markitdown[all] tqdm
git clone https://github.com/yasu-oh/markit-rag.git
cd markit-rag
```

## 使用例

### 単一ファイルを変換

```bash
python markit-rag.py ./example/report.xlsx
```

### ディレクトリ全体を再帰的に変換

```bash
python markit-rag.py ./docs
```

### 上書き保存を許可する

```bash
python markit-rag.py ./input --overwrite
```

### 詳細ログを有効化

```bash
python markit-rag.py ./input --verbose
```

## コマンドラインオプション

| オプション         | 説明                              |
| ------------- | ------------------------------- |
| `input`       | 入力ファイルまたはディレクトリのパス              |
| `--out`       | 出力ディレクトリ（既定: `markdown_output`） |
| `--overwrite` | 既存ファイルを上書き                      |
| `--verbose`   | 詳細ログを表示                         |

## 内部処理概要

1. **MarkItDownによるMarkdown変換**
   各ファイルを markitdown でMarkdownテキスト化
2. **正規化処理 (`normalize_markdown`)**
   * NaN/null/Noneセル除去
   * 空行削除
   * 末尾空セル除去
   * 改行統一
3. **出力フォルダ構造を保持して保存**
