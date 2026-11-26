Heritage Short — Quick Assessment Cheat Sheet
1. What is it?
A short AI-made film (under 90 sec) in Amharic with English subtitles. It tells a true family story: the narrator's grandmother Tiseme kept planting a single warka seed despite failed seedlings, hungry goats, and gentle laughter. Years after she died, it became a tree for her grandchildren. Made for family to watch on phones (vertical first) and forward in family chats.

2. What makes it technically interesting?
It's a reproducible pipeline. One file — storyboard.json — is the "contract" between every stage. Change a line in it, run one command, and only the affected shot is regenerated.

3. How do you run it?
Requirements: Python 3.10+, FFmpeg (ffmpeg and ffprobe on PATH). No make needed.

bash
git clone https://github.com/Yonathan-GM/Trp2-Week0-The-Heritage
cd Trp2-Week0-The-Heritage
python -m pip install -r requirements.txt
cp .env.example .env        # then add keys
python run.py
Keys needed: ADDIS_API_KEY (narration), CLOUDFLARE_ACCOUNT_ID + CLOUDFLARE_API_TOKEN (keyframes). GEMINI_API_KEY optional (smoke test only).

4. What are the outputs?
In outputs/final/:

film_vertical.mp4 — 1080x1920 (main version)

film_horizontal.mp4 — 1920x1080

5. Useful commands
Command	What it does
python run.py --draft	Half-size assemble for fast check
python run.py --only keyframes	Run one stage
python run.py --from music	Start at a stage
python check_submission.py	Pre-submission checks (secrets, placeholders, docs, films)
make film	Same as python run.py (for make users)
Re-runs are incremental: each stage hashes its inputs, regenerates only what changed. Every model call is logged as one line in runs.jsonl.

6. Pipeline stages
Stage	Script	Model	Runs on
Validate	pipeline/validate.py	JSON Schema	local
Narration	pipeline/narration.py	Addis AI Amharic TTS	Addis AI API
Keyframes	pipeline/keyframes.py	FLUX.1 schnell	Cloudflare Workers AI
Moving shots	pipeline/shots.py	Wan 2.2 TI2V-5B (optional)	Kaggle notebook
Music	pipeline/music.py	ACE-Step 1.5 (optional) or music_synth.py	Kaggle / local
Assemble	pipeline/assemble.py	FFmpeg + Pillow	local
Wan & ACE-Step run on borrowed GPUs (Kaggle notebooks, manual hand-off). The film does not depend on them: shots without a Wan clip get a slow pan/zoom over the keyframe (sub-pixel crops). If no outputs/music/score.wav, run.py synthesises an original score locally (plucked lyre, pad, shaker in D minor).

7. Vertical vs horizontal
9:16 fills the frame (subjects kept centred in square keyframes).

16:9 shows the whole picture centred on a blurred copy of itself — nothing cropped.

8. Audio & subtitles
Narration on a timeline; score ducked under it (sidechaincompress, threshold 0.02, ratio 6, attack 300ms, release 1500ms).

Mix normalised to ~ -14 LUFS with -1 dBTP ceiling.

Subtitles: two lines, max 40 chars, inside safe area, burned in.

9. Reproducibility caveat (honest point)
FLUX.1 schnell on Cloudflare does not accept a seed (API rejects it). So regenerated keyframes differ from the ones in the film. The cache keeps the film stable — unchanged shots are never regenerated.

10. Cost
All free tiers. See COSTS.md for measured latency, GPU minutes, and list-price equivalents.

11. Ethics / AI labelling
End card states the film was made with AI; public post has the platform's AI label on.

Characters are stylised illustrations, not real people; narration is a stock synthetic voice.

See ETHICS.md for consent, licences, labelling.

12. Docs index
DESIGN.md (audience, tests with real viewers) · ARCHITECTURE.md · EXPERIMENTS.md · FAILURES.md · COSTS.md · ETHICS.md

