import subprocess
import whisper
from pathlib import Path
from utils import sanitize_filename
import ast
from tqdm import tqdm


def download_audio_or_video(url: str, output_dir: str) -> tuple[str, str]:
    """
    Tries to download audio only. If not possible, downloads video, extracts audio, and deletes video.
    Returns path to the audio file and the (sanitized) video title.
    """
    # Get video info first to get the title
    info_cmd = [
        'yt-dlp',
        '--print', '%(title)s',
        url
    ]
    result = subprocess.run(info_cmd, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout:
        print(f"[yt-dlp] Failed to get video title. stderr: {result.stderr.strip()}")
        title = 'video'
    else:
        title = result.stdout.strip().split('\n')[0] or 'video'
    folder_name = sanitize_filename(title)
    folder_path = Path(output_dir) / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)

    # Try to download best audio only
    audio_path = folder_path / 'audio.m4a'
    audio_cmd = [
        'yt-dlp',
        '-f', 'bestaudio',
        '-o', str(audio_path),
        url
    ]
    audio_result = subprocess.run(audio_cmd, capture_output=True, text=True)
    print('Audio download error messages if any:', audio_result.stderr, '\n')

    if audio_path.exists():
        return str(audio_path), folder_name

    audio_path = folder_path / 'audio.wav'
    # Use yt-dlp template to allow multiple streams
    video_path_template = folder_path / 'video.%(ext)s'
    video_cmd = [
        'yt-dlp',
        '-f', 'bestvideo+bestaudio/best',
        '-o', str(video_path_template),
        url,
    ]
    video_result = subprocess.run(video_cmd, capture_output=True, text=True)
    print('Video download error messages if any:', video_result.stderr, '\n')

    # Find the downloaded video file (should be .mp4 or .mkv)
    video_files = list(folder_path.glob('video.*'))
    if not video_files:
        raise RuntimeError('Failed to download audio or video.')
    video_path = video_files[0]  # Take the first found
    # Extract audio using ffmpeg

    extract_cmd = [
        'ffmpeg', '-y', '-i', str(video_path), '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', str(audio_path)
    ]
    extract_result = subprocess.run(extract_cmd, capture_output=True, text=True)
    print(extract_result.stderr)

    if not audio_path.exists():
        raise RuntimeError('Failed to extract audio from video.')
    # Remove video file with retry logic for Windows
    import time
    for _ in range(5):
        try:
            video_path.unlink()
            break
        except PermissionError:
            print(f"[WARN] File {video_path} is busy, retrying...")
            time.sleep(1)
    else:
        print(f"[ERROR] Could not delete {video_path} after several retries.")
    return str(audio_path), folder_name

def split_audio_to_chunks(audio_path, chunk_length, overlap=5):
    """
    Splits audio into overlapping chunks of chunk_length seconds with the given overlap (in seconds) using ffmpeg.
    Returns a list of chunk file paths.
    """
    from pathlib import Path
    chunk_dir = Path(audio_path).parent / 'chunks'
    chunk_dir.mkdir(exist_ok=True)

    # Get audio duration using ffprobe
    ffprobe_cmd = [
        'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)
    ]
    result = subprocess.run(ffprobe_cmd, capture_output=True, text=True)
    duration = float(result.stdout.strip())

    chunk_files = []
    i = 0
    start = 0.0
    while start < duration:
        chunk_path = chunk_dir / f'chunk_{i:03d}.wav'
        # Adjust chunk length if last chunk exceeds duration
        actual_length = min(chunk_length, duration - start)
        ffmpeg_cmd = [
            'ffmpeg', '-y', '-i', str(audio_path),
            '-ss', str(start), '-t', str(actual_length),
            '-c', 'copy', str(chunk_path)
        ]
        subprocess.run(ffmpeg_cmd, capture_output=True)
        chunk_files.append(chunk_path)
        i += 1
        start = i * (chunk_length - overlap)
    # Only return chunk files that exist (ffmpeg may not create very short trailing chunks)
    chunk_files = [f for f in chunk_files if f.exists()]
    return chunk_files


def transcribe_audio(audio_path, language='ru', chunk_length=50):
    model = whisper.load_model('base', device='cpu')
    chunk_files = split_audio_to_chunks(audio_path, chunk_length)
    transcript = ''
    for idx, chunk in enumerate(chunk_files):
        print(f'Transcribing chunk {idx+1}/{len(chunk_files)}: {chunk}')
        result = model.transcribe(str(chunk), language=language)
        transcript += 'New chunk:\n' + result['text'].strip() + '\n'
    # Clean up chunk files
    for chunk in chunk_files:
        chunk.unlink()
    chunk_dir = (Path(audio_path).parent / 'chunks')
    if chunk_dir.exists():
        try:
            chunk_dir.rmdir()
        except OSError:
            pass  # Directory not empty (shouldn't happen)
    return transcript

def get_transcript_path(url, transcript_dir, sanitize_filename):
    import subprocess
    from pathlib import Path
    info_cmd = [
        'yt-dlp',
        '--print', '%(title)s',
        url
    ]
    result = subprocess.run(info_cmd, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout:
        title = 'video'
    else:
        title = result.stdout.strip().split('\n')[0] or 'video'
    folder_name = sanitize_filename(title)
    name = folder_name
    if name.startswith('s.'):
        parts = name.split('.')
        new_first = str(int(parts[1]) + 5)
        name = '.'.join([new_first] + parts[2:])
    transcript_folder = Path(transcript_dir)
    transcript_folder.mkdir(exist_ok=True)
    transcript_path = transcript_folder / f"{name}.txt"
    return transcript_path, name

def transcribe_video_url(url: str, output_dir: str, transcript_dir: str = 'transcripts'):
    from utils import sanitize_filename
    transcript_path, name = get_transcript_path(url, transcript_dir, sanitize_filename)
    audio_path, folder_name = download_audio_or_video(url, output_dir)
    transcript = transcribe_audio(audio_path, language='ru')
    with open(transcript_path, 'w', encoding='utf-8') as f:
        f.write(transcript)
    print(f'Transcription saved to: {transcript_path}')
    return transcript_path

if __name__ == '__main__':
    import sys
    from pathlib import Path
    
    def process_url_list(urls, output_dir='files', transcript_dir='transcripts'):
        for url in tqdm(urls):
            url = url.strip()
            if url:
                transcript_path, _ = get_transcript_path(url, transcript_dir, sanitize_filename)
                if transcript_path.exists():
                    print(f"Transcript already exists for {url}, skipping.")
                    continue
                print(f"\nProcessing URL: {url}")
                transcribe_video_url(url, output_dir, transcript_dir)

    if len(sys.argv) < 2:
        # No URL provided, try urls.txt
        urls_file = Path('urls.txt')
        if not urls_file.exists():
            print('Usage: python transcribe_video.py <video_url> [output_dir] OR place URLs in urls.txt')
            sys.exit(1)
        with open(urls_file, encoding='utf-8') as f:
            line = f.read().strip()
            urls = ast.literal_eval(line)
        process_url_list(urls)
    else:
        url = sys.argv[1]
        output_dir = sys.argv[2] if len(sys.argv) > 2 else '.'
        transcribe_video_url(url, output_dir)
