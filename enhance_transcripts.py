import os
import openai
import sys
from pathlib import Path

TRANSCRIPTS_DIR = Path('transcripts')
ENHANCED_DIR = Path('enhanced_transcripts')
CONTEXT_COUNT = 1
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
    client = openai.OpenAI(api_key=api_key)
    # Prepare context: last CONTEXT_COUNT enhanced transcripts
    context_text = '\n\n'.join([t[1] for t in context_transcripts[-CONTEXT_COUNT:]]) if context_transcripts else ''
    prompt = (
        "You are an expert transcriber and editor. You receive a transcript from Whisper that may contain grammar errors, misheard or misspelled words, and unnecessary delimiters like 'New chunk'. "
        "Your job is to fix grammar and spelling, correct misheard or misspelled words, remove all 'New chunk' delimiters, and glue the transcript together smoothly. "
        "Chunks overlap by 5 seconds. "
        "Sometimes you need to think to understand what was meant: use your knowledge in philosophy and history. "
        "For example, 'бород мечал' in one transcript was meant to be 'Бор отмечал' (it was said about Нильс Бор during the lecture). "
        "Rewrite as little as possible: only make necessary corrections to make the text correct and consistent. "
        "Here are up to 2 previous enhanced transcripts for context (if any):\n" + context_text +
        "\n\nHere is the next transcript to enhance:\n" + current_transcript +
        "\n\nReturn ONLY the enhanced transcript, nothing else."
    )
    response = client.chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": prompt}],
        max_completion_tokens=10000,
        # service_tier="flex",
    )
    print(response.choices[0].message.content)

    print(response)
    return response.choices[0].message.content.strip()


def main():
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} <OPENAI_API_KEY>")
        sys.exit(1)
    api_key = sys.argv[1]

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
        out_path = ENHANCED_DIR / filename
        if out_path.exists():
            print(f"{out_path} already exists. Skipping.")
            # Still add to context_enhanced for context chaining
            with open(out_path, 'r', encoding='utf-8') as f:
                enhanced = f.read()
            context_enhanced.append((filename, enhanced))
            continue
        print(f"Enhancing {filename} ({idx+1}/{len(transcripts)})...")
        enhanced = enhance_transcript(api_key, context_enhanced, transcript)
        context_enhanced.append((filename, enhanced))
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(enhanced)
        print(f"Saved enhanced transcript to {out_path}")

    print("All transcripts enhanced.")


if __name__ == '__main__':
    main()
