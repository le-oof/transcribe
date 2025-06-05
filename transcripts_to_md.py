import os
import re
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent
TRANSCRIPTS_DIR = BASE_DIR / 'enhanced_transcripts'
HTML_PATH = BASE_DIR / 'other_time_maybe' / 'page.html'
OUTPUT_MD = BASE_DIR / 'PhilosophyTranscript.md'

# 1. Parse HTML for section names
def extract_section_names(html_path):
    # Matches <span class="instancename">Видео 1.1. ...</span>
    pattern = re.compile(r'<span class="instancename">Видео (\d+\.\d+\.[^<]*)<')
    mapping = {}
    with open(html_path, 'r', encoding='utf-8') as f:
        content = f.read()
        for match in pattern.finditer(content):
            full = match.group(1).strip()  # e.g. "1.1. Предмет философии науки"
            # n.m is the first two parts
            nm_parts = full.split('.', 2)
            if len(nm_parts) < 2:
                continue
            nm_key = nm_parts[0] + '.' + nm_parts[1]
            mapping[nm_key] = full
    return mapping

# 2. Read transcripts and build markdown
def build_markdown(transcripts_dir, section_mapping, output_md):
    transcript_files = sorted([f for f in os.listdir(transcripts_dir) if re.match(r'\d+\.\d+\.txt$', f)])
    with open(output_md, 'w', encoding='utf-8') as out:
        for fname in transcript_files:
            nm = fname[:-4]  # Remove .txt
            section_title = section_mapping.get(nm)
            if not section_title:
                section_title = nm  # fallback
            out.write(f'## {section_title}\n\n')
            with open(os.path.join(transcripts_dir, fname), 'r', encoding='utf-8') as fin:
                out.write(fin.read().strip() + '\n\n')

if __name__ == '__main__':
    section_mapping = extract_section_names(HTML_PATH)
    build_markdown(TRANSCRIPTS_DIR, section_mapping, OUTPUT_MD)
    print(f'PhilosophyTranscript.md created with {len(section_mapping)} sections.')
