Take videos' urls, get unified .md file. Specific to my partiqular usecase, but might be usefull I guess.

What's the pipeline:
1. Generate urls into urls.txt (I used utils.py)
2. Download video, convert to audio, chunk, process with Whisper to get raw transcription -- all in transcribe_video_url function (in transcribe_video.py)
3. Enhance these transcripts with openai gpt -- check the difference between "transcipts" and "enhanced_transcipts" folders, it's great.
4. Glue enhanced_transcipts together into one .md file. I named each section of .md file by parsing page.html, which I downloaded manually from the course page.
5. Check the result in PhilosophyTranscript.md.
