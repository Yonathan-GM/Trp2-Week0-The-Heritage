# DESIGN

## Audience and intent

**Who watches:** My family and relatives — my parents' generation and my cousins.

**Where:** On their phones, shared in our Telegram family chat. Vertical (9:16) first, with a horizontal cut for TV.

**What they should feel:** Quiet pride and patience. What we plant for others can outlive us, and my grandmother's persistence still shelters us.

**How might we:** How might we help my family feel proud of Grandmother Tiseme's persistence and carry it forward?

## Story

**Whose story / who I talked to:** My grandmother Tiseme's story, told to me by my mother.

**Logline:** My grandmother kept planting one warka seed through failed seedlings, hungry goats and gentle laughter, and years after she was gone it became a tree for her grandchildren.

**Beats:**

1. She plants a seed. Nothing comes up.
2. The seedling dies, then goats eat the next one. She plants again.
3. The village laughs gently. She keeps planting.
4. Old and tired, she plants one last seed and says it will grow even if she isn't there.
5. She dies and the garden goes quiet.
6. A shoot appears and becomes a great tree. We, her grandchildren, play in its shade.
7. My mother tells me whose seed it was.

## AI-assisted workflow

An AI assistant helped translate the oral family story into the structured `storyboard.json` contract, refine Amharic/English subtitle pacing and visual consistency prompts (such as explicit shawl borders and "bare soil, no sprout" constraints), and build the automated validation, caching, and assembly scripts. All cultural details, story beats, editorial approvals, and audience test decisions remained human-directed.

## User test 1: radio cut

**Format:** Amharic narration over placeholder music on a black screen.

**Testers (from the audience):** My mom and dad.

**What they said:** They wanted the story to feel more personal.

**What I changed in `storyboard.json`:** I made the narrator a grandchild ("We, her grandchildren…") and ended on the mother and child in s11, so the story passes from her to my mother to me.

## User test 2: near-final cut

**Format:** Vertical MP4 with narration, subtitles and music, sent on Telegram.

**Testers (3 from the audience):** 3 cousins.

**What they said:** They were amazed that I still remembered the story, and they told me I was the one who asked about the huge tree that gave us shade.

**What I changed:** I added the final scene of me asking about the tree, which closes the loop between the opening question and the answer my mother gives in s11.

## Shot reasons

Every shot has a `reason` field in `storyboard.json`. The arc is:

- **s01–s02:** The place, the woman and the first seed.
- **s03–s05:** Failure, then gentle mockery. She keeps going.
- **s06:** Her one spoken belief — the longest shot.
- **s07:** Her absence, an empty garden — the quietest shot.
- **s08–s09:** The first shoot, then the great tree.
- **s10–s11:** Joy under the tree, then the story passes from her to my mother to me.

## Open items

- **Horizontal (TV) cut:** The vertical cut is the primary version. The horizontal cut reuses the same narration and music, with shots reframed to keep Grandmother Tiseme and the tree centered; no new story beats are added.
- **Per-shot detail:** Individual shot descriptions and `reason` fields live in `storyboard.json`, which is the source of truth for the edit.
