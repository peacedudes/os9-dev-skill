#!/usr/bin/env python3
"""
Prepare an index.json of Markdown files with metadata and chunk files for vector indexing.
This is a non-destructive operation: it reads markdowns and writes index.json and a
`chunks/` directory with JSON files containing chunks.
"""
import os,sys,json,re
from pathlib import Path

ROOT = Path('.')
OUT_INDEX = ROOT / 'translations_index.json'
CHUNKS_DIR = ROOT / 'chunks'
CHUNK_SIZE = 800  # characters per chunk approx

md_files = [p for p in ROOT.rglob('*.md') if not p.name.endswith('_de.md') and 'node_modules' not in p.parts]
md_files = sorted(md_files)

index = []
if not CHUNKS_DIR.exists():
    CHUNKS_DIR.mkdir()

for p in md_files:
    rel = str(p)
    try:
        txt = p.read_text(encoding='utf-8')
    except Exception:
        continue
    title = None
    m = re.search(r'^#\s+(.+)$', txt, re.MULTILINE)
    if m: title = m.group(1).strip()
    entry = {'path': rel, 'title': title or '', 'length': len(txt), 'language': 'en', 'topics': []}
    index.append(entry)
    # chunk into roughly CHUNK_SIZE chars with overlaps
    i=0
    n=0
    while i < len(txt):
        chunk = txt[i:i+CHUNK_SIZE]
        chunk_obj = {'source': rel, 'chunk_index': n, 'text': chunk}
        outp = CHUNKS_DIR / (p.name.replace('.md','') + f'.chunk{n}.json')
        outp.write_text(json.dumps(chunk_obj, ensure_ascii=False, indent=2), encoding='utf-8')
        n+=1
        i += CHUNK_SIZE - 50

OUT_INDEX.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'Wrote {len(index)} entries and chunks to {CHUNKS_DIR}')
