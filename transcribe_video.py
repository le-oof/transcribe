import subprocess
import whisper
from pathlib import Path


def sanitize_filename(name):
    return ''.join(c for c in name if c.isalnum() or c in (' ', '.', '.', '_', '-')).rstrip()

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
        title = result.stdout.replace('.', '_').strip().split('\n')[0] or 'video'
    folder_name = sanitize_filename(title)
    folder_path = Path(output_dir) / folder_name
    folder_path.mkdir(parents=True, exist_ok=True)

    # Try to download best audio only
    audio_path = folder_path / 'audio.wav'
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
    # If audio download failed, download best video
    video_path = folder_path / 'video.mp4'
    video_cmd = [
        'yt-dlp',
        '-f', 'bestvideo+bestaudio/best',
        '-o', str(video_path),
        '-c', 'continue',  # If video already exists, continue to convert
        url,
    ]
    video_result = subprocess.run(video_cmd, capture_output=True, text=True)
    print('Video download error messages if any:', video_result.stderr, '\n')

    if not video_path.exists():
        raise RuntimeError('Failed to download audio or video.')
    # Extract audio using ffmpeg

    print(video_path)
    extract_cmd = [
        'ffmpeg', '-y', '-i', str(video_path), '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1', str(audio_path)
    ]
    extract_result = subprocess.run(extract_cmd, capture_output=True, text=True)
    print(extract_result.stderr)

    if not audio_path.exists():
        raise RuntimeError('Failed to extract audio from video.')
    # Remove video file
    video_path.unlink()
    return str(audio_path), folder_name

def transcribe_audio(audio_path, language='ru'):
    model = whisper.load_model('base', device='cpu')
    result = model.transcribe(audio_path, language=language)
    return result['text']

def transcribe_video_url(url, output_dir='.'):
    audio_path, folder_name = download_audio_or_video(url, output_dir)
    transcript = transcribe_audio(audio_path, language='ru')
    transcript_path = Path(output_dir) / folder_name / 'transcript.txt'
    with open(transcript_path, 'w', encoding='utf-8') as f:
        f.write(transcript)
    print(f'Transcription saved to: {transcript_path}')
    return transcript_path

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: python transcribe_video.py <video_url> [output_dir]')
        sys.exit(1)
    url = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else '.'
    transcribe_video_url(url, output_dir)
