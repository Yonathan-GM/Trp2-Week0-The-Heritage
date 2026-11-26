Heritage Short: "The Seed That Waited Twenty Years"

A short AI-made film (under 90 seconds, Amharic narration with English subtitles) about a story my parents told me: my grandmother Tiseme kept planting one warka seed through failed seedlings, hungry goats and gentle laughter, and years after she was gone it became a tree for her grandchildren. It is made for my family, who will watch it on their phones (vertical first) and forward it in family chats.

It is built as a reproducible pipeline. One file, storyboard.json, is the contract between every stage: change a line in it, run one command, and only the affected shot is regenerated.

Run it

Needs Python 3.10+ and FFmpeg (ffmpeg and ffprobe on the PATH). No make is required.

git clone https://github.com/Yonathan-GM/Trp2-Week0-The-Heritage
cd Trp2-Week0-The-Heritage
python -m pip install -r requirements.txt
copy .env.example .env          # macOS/Linux: cp .env.example .env   (then add your keys)
python run.py

Keys in .env: ADDIS_API_KEY (narration), CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN (keyframes). GEMINI_API_KEY is optional (smoke test only).

Outputs land in outputs/final/: film_vertical.mp4 (1080x1920, the main version) and film_horizontal.mp4 (1920x1080).

Useful variants:

python run.py --draft              half-size assemble for a fast check
python run.py --only keyframes     one stage
python run.py --from music         start at a stage
python check_submission.py         pre-submission checks (secrets, placeholders, docs, films)

make film does the same as python run.py for people who have make.

Re-runs are incremental: each stage hashes its inputs and regenerates only what changed. Every model call (hit or miss) is logged as one line in runs.jsonl.

Stages
Stage	Script	Model	Runs on
Validate	pipeline/validate.py	JSON Schema	local
Narration	pipeline/narration.py	Addis AI Amharic TTS	Addis AI API
Keyframes	pipeline/keyframes.py	FLUX.1 schnell	Cloudflare Workers AI
Moving shots	pipeline/shots.py	Wan 2.2 TI2V-5B (optional)	Kaggle notebook (manual hand-off)
Music	pipeline/music.py	ACE-Step 1.5 (optional) or music_synth.py	Kaggle notebook, or local code
Assemble	pipeline/assemble.py	FFmpeg + Pillow	local
Wan and ACE-Step run on borrowed GPUs. Those stages write a job file (outputs/shots/wan_input.zip, outputs/music/request.json); you run the notebook in notebooks/, copy the results back, and re-run the stage to log them.
The film does not depend on them. A shot without a Wan clip gets a slow pan/zoom over its keyframe (rendered with sub-pixel crops, see EXPERIMENTS.md). If there is no outputs/music/score.wav, run.py synthesises an original score locally (pipeline/music_synth.py: plucked lyre, pad and shaker in D minor, following the music cues in storyboard.json).
Vertical vs horizontal. The 9:16 film fills the frame (subjects are kept centred in the square keyframes); the 16:9 film shows the whole picture centred on a blurred copy of itself, so nothing is cropped.
Audio. Narration is placed on a timeline, the score is ducked under it (sidechaincompress, threshold 0.02, ratio 6, attack 300 ms, release 1500 ms), and the mix is normalised to about -14 LUFS with a -1 dBTP ceiling. Subtitles (two lines of at most 40 characters, inside the safe area) are burned in.
Reproducibility, honestly

FLUX.1 schnell on Cloudflare does not accept a seed (the API rejects it, see FAILURES.md), so regenerated keyframes will differ from the ones in this film. The cache is what keeps the film stable: unchanged shots are never regenerated.

What it costs

All free tiers; see COSTS.md for measured latency, GPU minutes and list-price equivalents.

Docs

DESIGN.md (audience, tests with real viewers) · ARCHITECTURE.md · EXPERIMENTS.md · FAILURES.md · COSTS.md · ETHICS.md

Made with AI

The film carries an end card stating it was made with AI, and the public post has the platform's AI label switched on. The characters are stylised illustrations, not real people, and the narration is a stock synthetic voice. See ETHICS.md for consent, licences and labelling.
