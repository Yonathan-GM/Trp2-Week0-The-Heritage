# ETHICS

## Consent record

GATE: if a real person appears or is voiced without a record here, the project fails review.

No real person's face, photograph, likeness, or recorded voice appears in this film:

- **Visuals:** All five characters in `storyboard.json` (`grandmother`, `children`, `kids`, `mother`, `child`) are marked `"consent": "fictional_or_stylised"` and rendered as stylised watercolour illustrations.
- **Voice:** Narration is generated using Addis AI's stock synthetic Amharic voice (`am-yohanes-calm`), not a cloned or personal voice.
- **Story provenance:** The narrative is a family memory about Grandmother Tiseme shared orally by the author's mother, retold without exposing identifying personal data.

| Subject / Character | Relationship | What appears (face / likeness / voice / words) | Consent / Status |
|---|---|---|---|
| Grandmother Tiseme (`grandmother`) | Author's late grandmother | Stylised watercolour illustration & narrated family story | `fictional_or_stylised` illustration; family story shared by author's mother |
| Mother (`mother`) | Author's mother | Stylised watercolour illustration | `fictional_or_stylised` illustration; no real likeness or voice used |
| Grandchildren (`children`, `kids`, `child`) | Author and cousins (collective) | Stylised watercolour silhouettes/figures | `fictional_or_stylised` illustration; no real likenesses used |
| Narrator voice (`am-yohanes-calm`) | Synthetic stock TTS voice | Amharic spoken audio | Stock synthetic voice provided via Addis AI API |

## Licences

| Model / tool | Licence / Terms | Output terms | Notes |
|---|---|---|---|
| Addis AI TTS (`am-yohanes-calm`) | Addis AI API Terms of Service | Permitted for generated audio outputs per account plan | Primary narration provider (`pipeline/narration.py`) |
| FLUX.1 schnell (`@cf/black-forest-labs/flux-1-schnell`) | Apache 2.0 (model weights) / Cloudflare Workers AI Terms | Generated images usable under Apache 2.0 & Cloudflare service terms | Keyframe illustrations (`pipeline/keyframes.py`) |
| Wan 2.2 TI2V-5B | Apache 2.0 | Generated video outputs usable under Apache 2.0 | Optional motion stage (`pipeline/shots.py`) |
| ACE-Step 1.5 | MIT | Outputs usable commercially | Optional music stage (`pipeline/music.py`) |
| Local Python score synth (`pipeline/music_synth.py`) | Project repository code (NumPy-generated audio) | Self-authored original synthesis; no third-party audio samples | Active fallback in `outputs/music/score.wav` |
| Google Gemini API (`gemini-3.5-flash` / `3.8-flash`) | Google API Terms of Service | Subject to Google Generative AI terms (free-tier data handling applies) | Used only for text smoke test / legacy narration fallback |
| FFmpeg / Pillow / NumPy | LGPL/GPL (`ffmpeg`), HPND (`pillow`), BSD-3-Clause (`numpy`) | n/a (local processing tools) | Local assembly & audio processing |

## Labelling plan

- End card explicitly states `"Made with AI"` for 3 seconds (`end_card` in `storyboard.json`).
- Platform AI-disclosure label switched on whenever shared publicly.
- SynthID / C2PA metadata preserved intact where provided by upstream tools.

## Private data

Free and hosted AI endpoints may log or retain prompts under free-tier terms. The following private family details were intentionally withheld from all prompts and `storyboard.json`:

- Family surnames and full names of living relatives.
- Specific Ethiopian village/town names, GPS locations, or home landmarks.
- Exact dates of birth, death, or family photographs (no reference photos were uploaded to `refs/`).
