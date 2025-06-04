import os
import openai
import sys
from pathlib import Path

TRANSCRIPTS_DIR = Path('transcripts')
ENHANCED_DIR = Path('enhanced_transcripts')
CONTEXT_COUNT = 3
CHARACTER_LIMIT = 1_000_000


def count_total_characters(directory):
    total = 0
    for file in sorted(directory.glob('*.txt')):
        with open(file, 'r', encoding='utf-8') as f:
            total += len(f.read())
    return total


def load_transcripts(directory):
    files = sorted(directory.glob('*.txt'))
    transcripts = []
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            transcripts.append((file.name, f.read()))
    return transcripts


def enhance_transcript(api_key, context_transcripts, current_transcript):
    openai.api_key = api_key
    # Prepare context: last CONTEXT_COUNT enhanced transcripts
    context_text = '\n\n'.join([t[1] for t in context_transcripts[-CONTEXT_COUNT:]]) if context_transcripts else ''
    prompt = (
        "You are an expert transcriber and editor. You receive a transcript from Whisper that may contain grammar errors, misheard or misspelled words, and unnecessary delimiters like 'New chunk'. "
        "Your job is to fix grammar and spelling, correct misheard or misspelled words, remove all 'New chunk' delimiters, and glue the transcript together smoothly. "
        "Chunks overlap by 5 seconds. "
        "Sometimes you need to think to understand what was meant: use your knowledge of philosophy and history. "
        "Rewrite as little as possible: only make necessary corrections to make the text correct and consistent. "
        "Here are up to 3 previous enhanced transcripts for context (if any):\n" + context_text +
        "\n\nHere is the next transcript to enhance:\n" + current_transcript +
        "\n\nReturn ONLY the enhanced transcript, nothing else."
    )
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=4096,
    )
    return response['choices'][0]['message']['content'].strip()


def main():
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        api_key = input('Enter your OpenAI API key: ').strip()
        if not api_key:
            print('No API key provided. Exiting.')
            sys.exit(1)

    if not TRANSCRIPTS_DIR.exists():
        print(f"Transcripts directory '{TRANSCRIPTS_DIR}' does not exist. Exiting.")
        sys.exit(1)

    ENHANCED_DIR.mkdir(exist_ok=True)

    total_chars = count_total_characters(TRANSCRIPTS_DIR)
    print(f"Total characters in transcripts: {total_chars}")
    if total_chars > CHARACTER_LIMIT:
        print(f"Character limit exceeded ({CHARACTER_LIMIT}). Aborting.")
        sys.exit(1)

    transcripts = load_transcripts(TRANSCRIPTS_DIR)
    context_enhanced = []

    for idx, (filename, transcript) in enumerate(transcripts):
        print(f"Enhancing {filename} ({idx+1}/{len(transcripts)})...")
        enhanced = enhance_transcript(api_key, context_enhanced, transcript)
        context_enhanced.append((filename, enhanced))
        out_path = ENHANCED_DIR / filename
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(enhanced)
        print(f"Saved enhanced transcript to {out_path}")

    print("All transcripts enhanced.")


if __name__ == '__main__':
    main()
