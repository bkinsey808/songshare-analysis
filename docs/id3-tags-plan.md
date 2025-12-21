# Plan: Add ID3 Tagging & Metadata to SongShare Analysis ✅

## Purpose & Goals 🎯
- Add metadata (ID3 tags) to music files (MP3, and extend to FLAC/MP4/OGG) to improve track data quality.
- Provide both library API and CLI to analyze files, propose tags, preview changes, and write tags safely.
- Ensure robust tests, CI, and clear docs so this can be used in automated workflows.

## Success criteria ✅
- CLI that can scan a file or directory and print a preview of suggested tag edits.
- Ability to write tags (with dry-run and backup options) for at least MP3 (ID3v2.3/v2.4) using a well-supported library.
- Unit + integration tests with representative fixtures and CI pipeline.

---

## Scope
**In scope:**
- MP3 ID3 read/write (primary)
- Basic support for FLAC/OGG/MP4 metadata (read, extend to write as time allows)
- Non-destructive writes, dry-run, and preview
- CLI + Python API

**Out of scope (initial):**
- Full audio fingerprint matching / metadata lookup services (MusicBrainz) — may be added later as a follow-up
- Complex UI; keep CLI + programmatic API only

---

## High-level Design 🔧
1. **Scan**: Walk files (single file or directory with --recursive). Identify audio files by extension and/or magic bytes.
2. **Read**: Use an audio metadata library to read existing tags.
3. **Analyze**: Compute suggested tags from filename, path, existing tags, and optional heuristics (folder structure like Artist/Album/Track - Title).
4. **Preview**: Show a side-by-side diff of current vs suggested tags; offer dry-run or interactive apply.
5. **Write**: Apply tags safely (write to temp + atomic replace or create backup copy). Support `--yes` to apply changes non-interactively.

---

## Audio features (Essentia) 🔊
Essentia can extract a rich set of low-, mid-, and high-level features useful for analysis and tag suggestion. Below are compact, single-line descriptions for features to include in analysis pipelines and JSON summaries alongside ID3 metadata.

- **Low-level / Time-domain** — RMS (loudness measures overall energy), Zero‑Crossing Rate (signal noisiness), waveform envelope (amplitude over time), energy (per-frame energy arrays).
- **Spectral** — Spectral centroid/bandwidth/rolloff/flatness (timbre & brightness), spectral peaks (prominent frequencies), MFCCs (compact timbral descriptors), Bark bands & spectral contrast.
- **Tonal / Harmonic** — Chromagram / HPCP (pitch-class energy), key detection (key, scale, strength), chord detection & histograms, fundamental frequency (f0) and pitch salience.
- **Rhythm / Temporal** — Onset detection (note/beat onsets), beat timestamps, tempo/BPM estimate with confidence, beat histograms and danceability-like rhythmic descriptors.
- **Segmentation & Structure** — Section/segment boundaries, segment similarity descriptors and repetition patterns for structure analysis.
- **High-level / Semantic (models required)** — Genre, mood, instrumentation, danceability, energy, and other perceptual descriptors via trained classifiers or `MusicExtractor` conveniences.
- **Other useful measures** — Tonal centroid (tonnetz-like descriptors), loudness in LUFS, silence/background detection, and aggregated per-segment statistics (mean/std/percentiles).

Typical output shapes:
- Scalar (e.g., `rhythm.bpm = 120.0`)
- Arrays of timestamps (e.g., `rhythm.beats = [0.512, 1.024, ...]`)
- Per-frame matrices (e.g., `lowlevel.mfcc = [[...],[...],...]`)

Quick usage example (Python):

```python
from essentia.standard import MusicExtractor
extractor = MusicExtractor()    # convenience aggregator
features, frames = extractor('song.mp3')
print(features['rhythm.bpm'], features.get('tonal.key.key'))
```

> Note: high-level descriptors often rely on trained models and the streaming API is available for large-scale pipelines.

---

## Libraries: research & recommendation 📚
- **Mutagen** (recommended): full-featured, supports MP3 (ID3), FLAC (Vorbis), MP4, OGG; pure Python and well-maintained. Good for both read/write and cover art embedding.
- **eyed3**: MP3 focused; good features but narrower scope.
- **tinytag**: read-only and lightweight; not suitable for writing.

Recommendation: use **Mutagen** as the core library.

---

## Analysis-derived fields (from Essentia) 🧭
Below are the metadata and analysis fields we can extract directly (or via models) from Essentia; each entry is one line with a short explanation. Fields that map to standard ID3 frames are noted — others will be stored in a JSON sidecar by default.

- **bpm** — Estimated tempo in beats per minute (scalar); maps to ID3 `TBPM` if written.
- **bpm_confidence** — Confidence/strength of the tempo estimate (0–1 float); stored in JSON (`TXXX` if explicitly mapped).
- **key** — Detected musical key (e.g., `C major` / `A minor`); can be mapped to ID3 `TKEY`.
- **key_strength** — Strength/confidence of detected key (0–1 float); stored in JSON.
- **beats** — Array of beat timestamps in seconds for alignment and previews (JSON only).
- **onsets** — Array of onset timestamps (percussive events) in seconds (JSON only).
- **beat_std / beat_cv** — Beat variability: standard deviation of inter-beat intervals (seconds) and coefficient of variation (std/mean) to quantify rhythmic regularity; useful to separate click‑track (very low variability) from human rhythm (higher variability) (JSON/TXXX).
- **rhythm_timing** — Categorical rhythm timing classification derived from beat variability and quantization metrics; values: "human", "clicktrack", or "uncertain". Include `rhythm_timing_confidence` (0–1) and optional `rhythm_timing_reason` (JSON/TXXX).
- **sections** — Detected segment/section boundaries (timestamps and optional labels) for structure (JSON only).
- **loudness** — Integrated loudness (LUFS) or RMS values useful for normalization (scalar; JSON or `TXXX`).
- **mfccs** — MFCC coefficients (per-frame matrix or aggregated stats like mean/std); useful for similarity search (JSON only).
- **chroma** — Chromagram aggregates or histograms (per-frame or summary; helpful for key/chord inference; JSON only).
- **scale_degrees** — Inferred scale degrees relative to the tonic (e.g., `['1','2','b3','4','5','b6','b7']`), derived from mean chroma/HPCP rotated to tonic and key detection; include per-degree confidence scores (JSON only).
- **chords** — Chord sequence or chord histogram detected from audio (JSON only).
- **genre** — Predicted genre label (model-dependent); can be written to ID3 `TCON` if desired.
- **danceability / energy / mood** — High-level perceptual descriptors from models (model-dependent; JSON or `TXXX`). For mood, we will include continuous dimensions (valence/arousal/energy/danceability) and *top-k* categorical labels; additionally we will emit **one presence tag per mood** (e.g., `TXXX:mood_energetic`) only when the model confidence exceeds a configurable threshold (e.g., 0.5). This keeps tags simple and binary for fast filtering while preserving continuous scores and label confidences in the JSON sidecar.
- **instruments** — Predicted instrument(s) present (e.g., `guitar`, `bass`, `drums`, `vocals`, `piano`) with per-instrument confidence and optional time-spans or per-segment labels; model-dependent (JSON or `TXXX`). Emit a compact `TXXX:instruments` histogram/list and per-instrument presence frames `TXXX:instrument_<label>` (confidence or binary presence) when confidence exceeds a configurable threshold (default 0.5). Include `provenance` (model name/version) and `confidence` with instrument outputs.
- **vocal_presence** — Per-frame and track-level vocal activity probability (0–1); useful to infer vocal segments (JSON and compact `TXXX:vocal_presence` summary).
- **vocal_segments** — Start/end timestamps for vocal regions derived from `vocal_presence` (JSON sidecar).
- **vocal_pitch_stats** — Vocal pitch summaries: `vocal_low_note`, `vocal_high_note`, `vocal_median_note` (stored as note+octave strings, e.g., `A3`); optionally include MIDI numbers (`vocal_low_midi`, `vocal_median_midi`, `vocal_high_midi`) for numeric consumers. Include per-field confidence, pitch range in semitones or MIDI if desired, and prefer JSON sidecar for full contour storage.
- **vocal_timbre** — Vocal timbre descriptors (MFCC mean/std, spectral centroid, spectral slope) computed over vocal frames; store per-frame matrices in JSON and aggregated scalars in `TXXX` when robust.
- **vocal_role** — Detected vocal role (e.g., `lead`, `backing`, `chorus`) from a model-based classifier; store as `TXXX:vocal_role = "lead"` when confidence high and include `TXXX:vocal_role_confidence` or JSON provenance.
- **vocal_emotion / prosody** — Emotion and prosody descriptors (valence/arousal/energy, or categorical labels like `energetic`,`sad`) from models; emit continuous scores in JSON and per-label presence frames `TXXX:vocal_emotion_<label>` when confidence ≥ threshold (default 0.5). Include `provenance` and `confidence`.

## ID3 mapping (ID3 frame → derived from) 🔗
Below are suggested mappings showing the ID3 frame on the left and the Essentia-derived source (or JSON/TXXX storage) on the right.

- **TBPM** → `bpm` (Essentia tempo estimate)
- **TKEY** → `key` (Essentia key detection, normalized; e.g., `C major`)
- **TCON** → `genre` (model-dependent genre prediction from Essentia)
- **APIC** → cover art (not derived from Essentia; provided via other sources or left unchanged)
- **TXXX:bpm_confidence** → `bpm_confidence` (tempo confidence float; stored in TXXX or JSON)
- **TXXX:key_strength** → `key_strength` (key confidence float; stored in TXXX or JSON)
- **TXXX:beats** → `beats` (beat timestamps — large arrays stored in JSON sidecar by default)
- **TXXX:onsets** → `onsets` (onset timestamps — JSON sidecar)
- **TXXX:beat_std_seconds** → `beat_std` (standard deviation of inter-beat intervals in seconds; numeric TXXX or JSON)
- **TXXX:beat_cv** → `beat_cv` (coefficient of variation (std/mean) for tempo-independent variability; numeric TXXX or JSON)
- **TXXX:rhythm_timing** → `rhythm_timing` (categorical: `"human"` | `"clicktrack"` | `"uncertain"` with `rhythm_timing_confidence` numeric; TXXX or JSON)
- **TXXX:sections** → `sections` (segment boundaries & labels — JSON sidecar)
- **TXXX:mfccs** → `mfccs` (per-frame coefficients or aggregated stats — JSON sidecar)
- **TXXX:chroma** → `chroma` (chromagram or summaries — JSON sidecar)
- **TXXX:chords** → `chords` (chord sequence/histogram — JSON sidecar)
- **TXXX:scale_degrees** → `scale_degrees` (inferred scale degrees relative to tonic; JSON sidecar or `TXXX` as compact string)
- **TXXX:loudness** → `loudness` (LUFS/RMS — can be stored in TXXX or JSON)
- **TXXX:tuning_reference_hz** → `tuning.reference_hz` (detected reference pitch in Hz, e.g., 440.0 or 432.0; write only when confidence is high)
- **TXXX:tuning_cents** → `tuning.cents` (cents offset relative to A440, e.g., -31.7)
- **TXXX:danceability, TXXX:energy, TXXX:mood** → `danceability`/`energy`/`mood` (model-dependent; JSON or TXXX)
- **TXXX:mood_<label>** → `mood_<label>` (one TXXX frame per mood label; can store either a confidence float 0–1 (recommended) or a binary presence `1` when confidence ≥ presence threshold; e.g., `TXXX:mood_energetic = 0.78` or `TXXX:mood_energetic = 1`)
- **TXXX:instruments** → `instruments` (list or histogram of detected instruments; e.g., `{"guitar":0.92,"drums":0.85}`)
- **TXXX:instrument_<label>** → `instrument_<label>` (per-instrument confidence or binary presence; e.g., `TXXX:instrument_guitar = 0.92` or `1` when presence above threshold)
- **TXXX:vocal_presence** → `vocal_presence` (track-level vocal probability summary; e.g., `TXXX:vocal_presence = 0.88`)
- **TXXX:vocal_median_note** → `vocal_median_note` (median vocal pitch as a note+octave string, e.g., `A3`; optional `TXXX:vocal_median_midi` for MIDI note number; write only when confidence is high)
- **TXXX:vocal_low_note** → `vocal_low_note` (lowest vocal pitch as a note+octave string, e.g., `E2`)
- **TXXX:vocal_high_note** → `vocal_high_note` (highest vocal pitch as a note+octave string, e.g., `C6`)
- **TXXX:vocal_timbre** → `vocal_timbre` (compact summary such as `mfcc_mean: [...]` or scalar descriptors) 
- **TXXX:vocal_role** → `vocal_role` (e.g., `lead`, `backing` with `TXXX:vocal_role_confidence`)
- **TXXX:vocal_emotion** → `vocal_emotion` (JSON or compact `{"valence":0.4,"arousal":0.7}`) 
- **TXXX:vocal_emotion_<label>** → `vocal_emotion_<label>` (per-emotion confidence or presence; e.g., `TXXX:vocal_emotion_angry = 0.82`)
- **TXXX:vocal_masculine** → `vocal_masculine` (confidence or presence of masculine sounding voice;)
- **TXXX:vocal_feminine** → `vocal_feminine` (confidence or presence of feminine sounding voice;)
- **TXXX:meter** → `meter` (time signature string, e.g., `4/4`)
- **TXXX:swing_ratio** → `swing_ratio` (numeric ratio measuring swing; e.g., 1.5–1.8)
- **TXXX:backbeat_strength** → `backbeat_strength` (0–1 float, higher when beats 2/4 are emphasized)
- **TXXX:syncopation** → `syncopation` (numeric syncopation score)
- **TXXX:polyrhythms** → `polyrhythms` (list/histogram of detected ratios and confidences; JSON recommended)
- **TXXX:rhythm_type** → `rhythm_type` (categorical label like `straight`,`swing`,`syncopated`,`one-drop`,`polyrhythmic` with `TXXX:rhythm_type_confidence`)

## Essentia capabilities (what we can derive) 🔬
- **Direct / reliable (no external model required)** — `bpm` (tempo estimate), `beats` (beat timestamps), `onsets` (onset timestamps), `mfccs` (per-frame matrix and aggregated stats), `chroma` (per-frame or summary chroma), `key` & `key_strength` (key + confidence), `f0`/pitch (per-frame), `loudness`/RMS/LUFS (loudness measures), `sections`/segment boundaries, and spectral features (centroid, bandwidth, flatness, rolloff, spectral peaks).
- **Model-dependent / optional** — `genre` (requires classifier), `danceability`/`energy`/`mood` (requires trained models), `chords` (recognition methods vary); available via `MusicExtractor` or custom models but accuracy depends on the model.
- **Not provided / out of scope by Essentia** — cover art, lyrics, ISRC, and textual metadata like `artist`/`album`/`title` (these require sidecar data or external lookups).

Notes & caveats:
- Many descriptors are per-frame arrays or matrices; for tagging use aggregated scalars (mean/std/median) and store full arrays in a JSON sidecar (e.g., `song.mp3.analysis.json`).
- For beat variability: compute inter-beat intervals (diff between consecutive beat timestamps), then compute a robust standard deviation (e.g., trimmed std or MAD-based) and the coefficient of variation (std/mean). Report both `beat_std` (seconds) and `beat_cv` (unitless) and store them in `TXXX` frames and/or JSON sidecars for downstream use. Heuristic thresholds (dataset-dependent): `beat_cv < 0.005` often indicates quantized/click-like timing; `beat_cv > 0.02` is more likely human-performed. To set `rhythm_timing`: use a simple rule-based classifier combining `beat_cv`, `beat_std`, and a quantization score (e.g., median absolute phase deviation from nearest grid). Example heuristic: if `beat_cv < 0.005` and quantization score > 0.9 → `rhythm_timing = "clicktrack"`; if `beat_cv > 0.02` → `rhythm_timing = "human"`; otherwise `rhythm_timing = "uncertain"`. Always store `rhythm_timing_confidence` (0–1) and `rhythm_timing_reason` so downstream users can adjust thresholds for their data.
- `MusicExtractor` provides convenient aggregated features and model-based descriptors; for high-performance or streaming workflows use low-level algorithms directly.
- Model-dependent fields should be validated on representative data before writing to ID3; consider writing them only to `TXXX` frames or JSON sidecars until confident.
- For mood tags: write continuous dimensions and top-k labels in JSON, and also emit per-mood `TXXX:mood_<label>` frames with confidence scores so simple tag-based filtering (e.g., `mood_energetic`) is possible without parsing JSON. Always include `provenance` (model name/version) and `confidence` with each mood tag.

Examples (ID3 frame → example value) 🧾
- **TBPM** → `120` (integer) — Essentia `bpm` tempo estimate, written to `TBPM`.
- **TKEY** → `C major` (string) — Essentia `key` result, normalized for `TKEY`.
- **TCON** → `Electronic` (string, model-dependent) — genre label from a classifier (write cautiously).
- **APIC** → `image/jpeg (front cover, 600x600)` — cover art is not derived from Essentia (external source).
- **TXXX:bpm_confidence** → `0.92` (float 0–1) — tempo confidence (store in `TXXX` or JSON).
- **TXXX:key_strength** → `0.78` (float 0–1) — key detection confidence (TXXX/JSON).
- **TXXX:beats** → `[0.512, 1.024, 1.536, 2.048]` (seconds) — beat timestamps (sidecar recommended for large arrays).
- **TXXX:onsets** → `[0.135, 0.483, 0.732, ...]` (seconds) — onset timestamps (JSON sidecar).
- **TXXX:beat_std_seconds** → `0.024` (seconds) — standard deviation of inter-beat intervals; low values indicate quantized click-like timing.
- **TXXX:beat_cv** → `0.002` (unitless std/mean) — coefficient of variation; heuristic thresholds: CV < 0.005 → click-like, CV > 0.02 → human-like (dataset-dependent).
- **TXXX:rhythm_timing** → `"human"` (string) with `rhythm_timing_confidence=0.92` — timing classification label derived from beat metrics and optional quantization checks.
- **TXXX:sections** → `[{"start":0.0,"end":30.5,"label":"intro"},{"start":30.5,"end":90.0,"label":"verse"},...]` — segmentation boundaries & labels (JSON).
- **TXXX:mfccs** → `mean: [-12.3, -6.1, 0.2, ...]` (or full per-frame matrix) — aggregated MFCC stats in tag or full matrix in sidecar.
- **TXXX:chroma** → `{"C":0.12,"C#":0.05,...}` — chroma histogram or summary.
- **TXXX:chords** → `['C:maj','G:maj','A:min']` (or histogram `{"C:maj":0.45}`) — chord sequence or histogram (algorithm-dependent).
- **TXXX:scale_degrees** → `['1','2','b3','4','5','b6','b7']` (or `{'1':0.98,'b3':0.76}`) — inferred degrees relative to tonic with optional per-degree confidences (JSON recommended).
- **TXXX:loudness** → `-12.3 LUFS` (string or numeric) — integrated loudness or RMS.
- **TXXX:danceability** → `0.72` (0–1, model-dependent) — perceptual descriptor.
- **TXXX:energy** → `0.65` (0–1, model-dependent) — perceptual descriptor.
- **TXXX:mood** → `{"valence":0.4,"arousal":0.6}` — multi-dimensional mood output (JSON recommended).
- **TXXX:mood_energetic** → `0.78` (0–1) — per-mood confidence tag for 'energetic'.
- **TXXX:mood_relaxed** → `0.12` (0–1) — per-mood confidence tag for 'relaxed'.
Notes on thresholds & presence:
- Compute continuous mood score (e.g., energy) in 0–1. Emit a presence tag `TXXX:mood_<label>` when the label's confidence ≥ a configurable threshold (default 0.5). Optionally write the numeric confidence to the same `TXXX` frame or to the JSON sidecar for more detail.
- Emit continuous scores (valence/arousal/energy/danceability) and top-k labels with confidences in the JSON sidecar for auditing and advanced filtering.
- Include `provenance` (model name/version) and `confidence` with each mood tag so consumers can adjust thresholds per dataset.

### Rhythm analysis & classification 🥁
- **What we estimate:** meter/time signature (e.g., `4/4`,`3/4`,`6/8`), `swing_ratio` (numeric ratio of even/odd subdivision timing), `backbeat_strength` (energy on beats 2 & 4), `syncopation` (numeric score), `polyrhythms` (list of detected ratio(s) and confidence), and a compact `rhythm_type` label (e.g., `straight`,`swing`,`syncopated`,`one-drop`,`polyrhythmic`) with confidence.
- **Method (summary):** compute beat timestamps and IBIs, build subdivision and phase histograms, measure deviation/quantization to infer swing and syncopation, estimate meter via autocorrelation/periodicity grouping, detect backbeat by measuring energy or drum presence at beat phases (2/4), and find secondary periodicities in the tempogram for polyrhythms. Optionally train a small classifier (RF/NN) on features (onset histograms, tempogram, subdivision ratios, pulse clarity) for `rhythm_type` labeling.
- **Output formats:**
  - JSON sidecar (preferred):

```json
{
  "rhythm": {
    "bpm": 120.0,
    "beats": [0.51, 1.02, ...],
    "meter": "4/4",
    "swing_ratio": 1.67,
    "backbeat_strength": 0.82,
    "syncopation": 0.31,
    "polyrhythms": [{"ratio":"3:2","confidence":0.78}],
    "rhythm_type": {"label":"swing","confidence":0.88}
  }
}
```

  - ID3/TXXX (compact): `TXXX:rhythm_type = "swing"`, `TXXX:meter = "6/8"`, `TXXX:swing_ratio = 1.65` (write numeric/label TXXX only when confidence >= configurable threshold, default 0.6).
- **Storage & thresholds:** store dense arrays and tempogram data in JSON sidecars; only emit compact TXXX frames for robust scalars/labels (confidence >= 0.6). For backbeat detection, drum separation or instrument detection improves reliability.
- **Tests & fixtures:** add short drum-loop fixtures for straight rock (4/4), funk (strong backbeat), swing jazz (swing), bossa nova, reggae one-drop, 6/8 waltz, samba, and a polyrhythm (3:2) sample. Unit tests should assert meter, swing_ratio ranges, backbeat_strength thresholds, polyrhythm detection, and style label with minimal confidence.
- **Caveats:** rhythm style labeling is partly heuristic and depends on percussive clarity; heavy production, tempo changes, or dense mixes reduce reliability. Always include `provenance` and `confidence` fields.


## Chord detection & storage 🎸
- **What Essentia can provide:** per-frame or per-segment chord labels (e.g., `C:maj`, `G:maj`, `A:min`) with timestamps and confidence scores, and chord histograms/summaries derived from chroma/HPCP + chord recognizers (available via `MusicExtractor` or lower-level tonal algorithms).
- **Recommended processing:** compute per-frame chroma/HPCP, run chord recognizer, then apply smoothing (median filter or minimum segment duration), and optionally use an HMM/Viterbi step to reduce spurious rapid changes. Merge adjacent identical chords and attach a `confidence` (mean or median of constituent frame confidences).
- **Output formats:**
  - Sequence: array of `{start: float, end: float, chord: string, confidence: float}` (preferred, store in JSON sidecar as `analysis.chords.sequence`).
  - Histogram/summary: mapping `{ 'C:maj': 0.45, 'G:maj': 0.30, ... }` (store in JSON sidecar as `analysis.chords.histogram`).
  - Compact ID3: optional `TXXX:chords` as a comma-separated short sequence or histogram string (useful for quick compatibility), but prefer JSON for timestamps/confidences.
- **Example values:**
  - `TXXX:chords` → `"C:maj,G:maj,A:min"`
  - JSON sidecar excerpt: `{"chords": {"sequence":[{"start":0.0,"end":12.0,"chord":"C:maj","confidence":0.92}, ...], "histogram":{"C:maj":0.45,"G:maj":0.30}}}`
- **Caveats & confidence:** chord recognition accuracy varies with polyphony, instrumentation, tuning, and percussive-heavy mixes; include `confidence` and `provenance` (algorithm/version) in outputs and avoid writing low-confidence labels to ID3 without provenance.

### Extended chord support (7ths & beyond) ♯
- **Goal:** detect extended chords beyond major/minor — dominant 7 (`C7`), major 7 (`Cmaj7`), minor 7 (`Cm7`), diminished (`Cdim`), augmented (`Caug`), sus2/sus4, 6ths, add9, and similar extensions where evidence supports them.

- **Chord types we'll attempt to detect (notation → intervals / description):**
  - **Major** (`C`, `Cmaj`) — intervals: 1, 3, 5 (major triad)
  - **Minor** (`Cm`, `C-`) — intervals: 1, b3, 5 (minor triad)
  - **Diminished** (`Cdim`) — intervals: 1, b3, b5
  - **Augmented** (`Caug`, `C+`) — intervals: 1, 3, #5
  - **Sus2** (`Csus2`) — intervals: 1, 2, 5
  - **Sus4** (`Csus4`) — intervals: 1, 4, 5
  - **Major 7 (maj7)** (`Cmaj7`) — intervals: 1, 3, 5, 7
  - **Dominant 7** (`C7`) — intervals: 1, 3, 5, b7
  - **Minor 7** (`Cm7`) — intervals: 1, b3, 5, b7
  - **Minor‑major 7** (`Cm(maj7)`) — intervals: 1, b3, 5, 7
  - **Sixth** (`C6`) — intervals: 1, 3, 5, 6
  - **Add9 / add2** (`Cadd9`, `Cadd2`) — intervals: 1, 3, 5, 9 (or 2)
  - **9 / dominant 9** (`C9`) — intervals: 1, 3, 5, b7, 9
  - **Diminished 7** (`Cdim7`) — common extended dim (store as `dim7`) where applicable
  - **Other extensions** (maj9, m9, sus2add9, etc.) — detect when evidence supports them and confidence is high

  Notes:
  - We will also detect *slash* (inversion) notation when the bass note is clearly distinct, e.g., `C/E` (store as `chord` with `bass` or as `chord` string `C/E`).
  - When extended‑chord confidence is low, prefer emitting a simplified base chord (e.g., write `C` for `C7` if `C7` confidence is low) while storing the candidate extended label and its confidence in the JSON sidecar.

- **Alg. options in Essentia:** configure chord recognizer templates or invoke `MusicExtractor`/`ChordDetection` with expanded chord vocabularies; use template matching on chroma/HPCP or train a classifier that recognizes extended chord templates.
- **Post-processing:** apply smoothing (median filter / minimum segment duration), and consider an HMM/Viterbi step or a harmonic grammar to reduce spurious rapid label changes; if extended-chord confidence is low, emit a simplified base chord (e.g., `C7` → `C`) as a fallback while storing the extended label and confidence in the JSON sidecar.
- **Output structure:** store extended chord sequence entries as `{start, end, chord: 'Cmaj7', type: 'major-seventh', confidence}` and include a `simplified` base chord field when appropriate; also provide a histogram of extended chord labels.
- **Storage:** prefer JSON sidecar (`analysis.chords.sequence`, `analysis.chords.histogram`). Optional `TXXX:chords` may hold a compact sequence of extended labels (comma-separated) for compatibility.
- **Example:**
  - JSON: `{"chords": {"sequence":[{"start":0.0,"end":12.0,"chord":"Cmaj7","type":"major-seventh","confidence":0.87}, ...]}}`
  - ID3 compact: `TXXX:chords = "Cmaj7,G7,Am7"`
- **Tests & evaluation:** add fixtures containing clear extended chords (jazz, R&B, funk) and include unit/integration tests that assert detection of `C7`, `Cmaj7`, `Cm7`, etc.; track precision/recall metrics and manually verify edge cases.
- **Caveats:** extended chord detection is more error-prone than simple triads; include confidence, provenance, and fallback to base chords where necessary; prefer JSON sidecar for full details so downstream tools can apply stricter filters.

### Tuning & reference pitch (A‑reference detection) 🎵
- **What we estimate:** global reference tuning (A‑reference in Hz, e.g., 440.0 or 432.0) and a cents offset relative to A440, plus a confidence score and provenance.
- **Method (summary):** extract reliable pitched frames (predominant f0 / spectral peaks), filter by salience, map measured pitches to nearest equal‑tempered notes assuming A=440, compute per‑frame cents deviations, aggregate robustly (median/MAD) to get median cents offset, convert to reference_hz = 440 * 2^(cents/1200).
- **Output & storage:**
  - JSON sidecar: `analysis.tuning = { "reference_hz": 432.0, "cents_offset": -31.7, "confidence": 0.87, "method": "median_f0_vs_equal_temperament", "n_frames": 123, "histogram": [...] }` (preferred)
  - Optional ID3/TXXX: `TXXX:tuning_reference_hz = 432.0`, `TXXX:tuning_cents = -31.7` (write only when confidence >= configurable threshold, e.g., 0.7)
- **Caveats & heuristics:** works well with clear pitched content (piano, sustained vocals/instruments); accuracy degrades with dense polyphony, heavy pitch correction, non‑equal temperament, or minimal pitched content. Use robust statistics, require a minimum number of pitched frames, and include `confidence` and `provenance`.

### Instrument detection & storage 🎷
- **What we estimate:** detected instruments and their time spans or overall presence, per-instrument confidence scores, and a histogram/top-k list. Typical labels: `vocals` (optionally `lead_vocal`/`backing_vocal`), `guitar`, `bass`, `drums`, `piano`, `keys`, `synth`, `strings`, `brass`, `woodwind`, `percussion`, `organ`, etc.
- **Method (summary):** use pretrained instrument-recognition models (available via `MusicExtractor` or external classifiers) to produce per-frame or per-segment instrument probabilities, then smooth (median/minimum-duration) and aggregate to track-level confidences. Always attach `provenance` (model name/version) and `confidence` for each instrument.
- **Output formats:**
  - JSON sidecar (preferred):

```json
{
  "instruments": {
    "sequence": [
      {"start":0.0, "end":12.0, "instrument":"guitar", "confidence":0.92},
      {"start":12.0, "end":30.0, "instrument":"vocals", "confidence":0.87}
    ],
    "histogram": {"guitar":0.72, "drums":0.65}
  }
}
```

  - ID3/TXXX (compact): `TXXX:instruments = "guitar:0.72,drums:0.65"` and per-instrument frames such as `TXXX:instrument_guitar = 0.72` (or `1` when presence above threshold).
- **Storage rules & thresholds:** write per-instrument ID3/TXXX frames only when confidence ≥ configurable threshold (default 0.5). For vocals, avoid inferring demographic attributes (gender/age); only detect `vocals` or roles (lead/backing) if model supports them and confidence is high.
- **Tests & evaluation:** add fixtures with isolated instruments and mixtures (vocals+acoustic guitar, drum loop, organ+strings) and unit tests asserting detection/histogram thresholds; include precision/recall checks as part of integration testing.
- **Caveats:** instrument recognition can struggle with overlapping sources, heavy effects, pitch-shifted or non-Western instruments, and dense mixes; prefer storing full details in the JSON sidecar and only write simple TXXX frames for high-confidence results.

### Vocal analysis & storage 🎤
- **What we estimate:** vocal activity (`vocal_presence`), vocal segments, pitch contour and summary stats (`vocal_low_note`, `vocal_high_note`, `vocal_median_note`), timbre descriptors (MFCC aggregates, spectral centroid), vocal role (`lead`/`backing`), and emotion/prosody scores (valence/arousal/energy or categorical labels).
- **Method (summary):** for best results, separate vocals (Spleeter/Demucs/OpenUnmix) then run Essentia `PredominantMelody`, `PitchYinFFT`/`PitchYin`, `MusicExtractor` and spectral descriptors on the `vocals` stem. Compute robust pitch statistics (median, min, max) and detect segments from vocal activity probability. Use smoothing and minimum duration heuristics for segments.
- **Output formats:**
  - JSON sidecar (preferred):

```json
{
  "vocals": {
    "presence": 0.88,
    "segments": [{"start":12.0,"end":47.4}],
    "pitch": {"median_note":"A3", "low_note":"A2", "high_note":"A5", "median_midi":57, "contour_notes": [...]},
    "timbre": {"mfcc_mean": [-12.3, -6.1, ...], "centroid": 2300.0},
    "role": {"label":"lead","confidence":0.91},
    "emotion": {"valence":0.45,"arousal":0.62, "labels":{"energetic":0.78}}
  }
}
```

  - ID3/TXXX (compact): `TXXX:vocal_presence = 0.88`, `TXXX:vocal_median_note = "A3"` (optional `TXXX:vocal_median_midi = 57`), `TXXX:vocal_role = "lead"` (write TXXX frames only when confidence exceeds configurable thresholds, default 0.6).
- **Storage rules & thresholds:** require a minimum number of pitched frames and a vocal presence ≥ 0.4 to compute pitch stats; note outputs are stored as note+octave strings (e.g., `A3`) and may include optional MIDI numbers for numeric consumers; write TXXX summaries only when `confidence >= 0.6` (configurable). Notes are computed assuming equal-tempered tuning (A=440) unless a reliable tuning offset is detected and applied (`analysis.tuning`). Always include `provenance` (model name/version) and `confidence` in JSON and TXXX where applicable.
- **Tests & fixtures:** add vocal fixtures (isolated lead vocal, processed vocal in mix, backing vocals) and tests for presence detection, pitch stats, role detection, and emotion outputs.
- **Caveats:** separation artifacts affect pitch and timbre; avoid demographic inferences (gender/age) and record the separation/model method and version with each result.

### Separation & stem analysis (Demucs recommended) 🔪
- **Why separate:** high-quality stem separation greatly improves accuracy for vocal pitch, timbre, role detection, and instrument presence. Separation reduces bleed and makes per-stem features (jitter, vibrato, timbre) much more reliable.
- **Recommended tools:**
  - **Demucs** — high-quality, state-of-the-art separation (recommended when quality is primary). GPU recommended for speed; CPU-only works but is slower.
  - **Spleeter** — fast, lightweight 2-/4-stem separation (useful for quick CI-friendly fixtures or low-resource runs).
  - **Open-Unmix** — research-quality, balanced option for some workflows.
- **Example Demucs command:**

```bash
# two-stem vocals separation (outputs to out/<track>/<stem>.wav)
demucs --two-stems=vocals -o out /path/to/song.mp3
# or full stem separation
demucs -n demucs -o out /path/to/song.mp3
```

- **Output & storage:**
  - Store separated stems alongside the analysis sidecar and reference them in `analysis.stems` with `path`, `stem_type` (`vocals`,`drums`,`bass`,`other`), `provenance` (tool name/version), and a `confidence` score where available. Example JSON entry:

```json
"stems": [{"stem_type":"vocals","path":"out/song/vocals.wav","provenance":{"tool":"demucs","version":"4.0"}}]
```

- **Integration into pipeline & CLI:** add an optional flag `--separate-vocals` (or `--separate-stems`) to the `id3` subcommand; when enabled, run Demucs first and analyze the `vocals` stem with Essentia for vocal-specific fields.
- **Performance & CI:** for CI and lightweight runs prefer Spleeter or precomputed fixture stems; reserve Demucs for higher-quality offline runs or optional staged analysis.
- **Tests & fixtures:** include a small pre-separated `fixtures/*.vocals.wav` for unit tests to avoid running separation in CI; add an integration test that runs Demucs on a very short clip in an optional, longer-running test stage.
- **Caveats:** separation is not perfect — document artifacts in `provenance` and include `confidence` and `notes` fields in the sidecar so downstream consumers can filter by quality.

### Genre classifier (PANNs) 🎧
- **Goal:** provide robust, off‑the‑shelf genre labels and confidence scores without requiring model training.
- **Recommendation:** use **PANNs** (pretrained audio tagging models) for multi‑label genre predictions; consider `musicnn` as an alternative if you prefer a music-focused taxonomy.
- **Install (PANNs example):**

```bash
pip install torch panns-inference librosa soundfile
```

- **Minimal inference example (PANNs):**

```python
from panns_inference import SoundTagging
import soundfile as sf

audio, sr = sf.read('song.wav')
model = SoundTagging(device='cpu')
result = model.inference(audio, sr)
# result: {'labels': [...], 'probabilities': [...]}
# Top-k:
top = sorted(zip(result['labels'], result['probabilities']), key=lambda x: -x[1])[:5]
```

- **Mapping to ID3 / JSON:**
  - JSON sidecar: store full probabilities, top-k, and provenance: `analysis.genre = {"top":"Rock","probs":{"Rock":0.82,...},"provenance":{"model":"panns","version":"..."}}`
  - ID3/TXXX rules: write `TCON` = top label only if `top_confidence >= threshold` (default 0.6). Emit `TXXX:genre_<label>` frames with confidence for labels above a presence threshold if desired.
- **Thresholds & rules:** use conservative writes to ID3 (only top label when confidence >= 0.6). For multi-label tagging prefer JSON sidecar for full fidelity. Always include `provenance` and `model_version` in outputs.
- **Tests & fixtures:** add music fixtures covering representative genres (rock, electronic, jazz, classical, hiphop) and unit tests asserting that top label appears in `probs` with reasonable confidence on canonical samples. Include a small end‑to‑end integration test that runs PANNs on a short fixture and validates JSON output structure.
- **Caveats:** model label taxonomies vary — map model labels to your canonical genre list before writing `TCON`. Validate model behavior on your dataset before mass writes.

### MusicBrainz integration 🔗
- **Purpose:** perform metadata lookups (artist, title, album, year, MBIDs, release info, cover art) using MusicBrainz WS/2 and AcoustID fingerprinting when tags are missing or low-confidence.
- **When to use:** fallback when embedded tags are missing or clearly incorrect, or to enrich metadata (release canonicalization, cover art). Always present proposed changes for preview before writing.
- **Tools & libraries:**
  - `musicbrainzngs` (Python) for MusicBrainz lookups
  - Chromaprint (`fpcalc`) + **AcoustID** service for fingerprint → MBID matching (requires AcoustID API key)
  - Cover Art Archive (coverartarchive.org) to fetch release front art by release MBID
- **Recommended flow:**
  1. Read existing tags with Mutagen; if missing/low-confidence and `--fetch-metadata` enabled, compute fingerprint with `fpcalc` (optional: skip fingerprint and do text search first).
  2. Query AcoustID for candidate recording MBIDs (score + list). Map to MusicBrainz recording/release via MBIDs.
  3. Resolve candidates (prefer highest acoustid score + release date/artist match), fetch release info (title/album/year, track position) and cover art URLs.
  4. Present proposed metadata in preview with explicit `provenance` (e.g., `musicbrainz+acoustid`) and `confidence` score for each field.
- **Example (musicbrainzngs usage):**

```python
import musicbrainzngs
musicbrainzngs.set_useragent('songshare-analyze','0.1','you@example.com')
res = musicbrainzngs.search_recordings(recording='Song Title', artist='Artist', limit=5)
# inspect res['recording-list'] and choose best candidate
rec = res['recording-list'][0]
mbid = rec['id']
full = musicbrainzngs.get_recording_by_id(mbid, includes=['artists','releases'])
```

- **User-Agent & rate-limiting:** set a descriptive User-Agent including contact; throttle requests (~1 req/sec) and cache responses locally to avoid abusive patterns. Avoid running large search loops in CI and prefer cached fixtures.
- **Provenance & merge rules:** store raw lookup responses in JSON sidecar under `analysis.metadata_sources.musicbrainz` with MBIDs and confidence. For each proposed field include `provenance` and `confidence`. Only write ID3 fields automatically when confidence ≥ configurable threshold (default 0.6) or when `--apply-metadata --yes` is explicitly provided.
- **CLI flags:** `--fetch-metadata` (enable lookups), `--metadata-source acoustid|musicbrainz|discogs|spotify` (choose source priority), `--apply-metadata`, `--yes` (non-interactive apply).
- **Tests & fixtures:** add small integration fixtures (short clips + expected MBIDs) and unit tests for merge logic (do not overwrite accurate existing tags). Mark heavy AcoustID tests as optional/long-running.
- **Caveats:** AcoustID may return multiple or ambiguous candidates, partial dates are common (year-only), different releases may exist for the same recording; always record provenance and do not overwrite human-provided metadata without explicit confirmation.



Notes:
- Arrays and per-frame matrices are typically stored in a JSON sidecar (e.g., `song.mp3.analysis.json`) rather than directly in standard frames.
- Use `TBPM`, `TKEY`, and `TCON` for compact scalar values; large arrays (beats, mfccs, sections) should default to JSON sidecars.
- Include provenance and confidence (timestamps and floating confidences) when writing `TXXX` frames or JSON so downstream consumers can assess reliability.

Normalization & validation:
- Numeric fields (e.g., `bpm`, `key_strength`) will be constrained to expected ranges and rounded as appropriate.
- Key outputs will be normalized to readable strings (e.g., `C major`, `A minor`).
- Timestamps will use seconds with millisecond precision where applicable.


---

## CLI & API design
CLI example:

```
# Preview changes for all files in `./music` recursively
songshare-analyze id3 --preview --recursive ./music

# Apply changes non-interactively
songshare-analyze id3 --apply --yes ./music/01-MySong.mp3

# Interactive for a single album directory
songshare-analyze id3 --interactive ./music/Artist/Album
```

Python API (example usage):

```python
from songshare_analysis.id3 import analyze_file, apply_tags
suggestions = analyze_file(Path('music/song.mp3'))
# suggestions -> dict with current and proposed tags
apply_tags(Path('music/song.mp3'), suggestions['proposed'], dry_run=True)
```

---

## Safety & UX ⚠️
- **Dry-run** and **preview** by default.
- **Backup** option: `--backup` creates `.bak` copies or stores original tags in a sidecar file.
- **Atomic writes**: write to a temp file then replace the original.
- **Logging**: support `--verbose` and `--quiet`.

---

## Tests & Fixtures 🧪
- Add `tests/fixtures` with representative audio files (small MP3s, FLAC, MP4).
- Unit tests: reading tags, computing suggestions, normalization functions, and writer (use temp files).
- Integration tests: run CLI on fixture dirs, assert tags updated and readable after write.
- Use `pytest` (existing project uses it).

---

## CI & Linting 🔁
- Add tests to existing CI pipeline; ensure fixtures are small to keep CI fast.
- Run linter and formatters as part of CI (pre-existing repo rules apply).

---

## Timeline & First Milestones 🗓️
1. Create planning doc and TODOs (this doc) — done ✅
2. Research libraries & pick `mutagen` (1-2 days)
3. Implement core reader + analyzer + unit tests for MP3 (3-4 days)
4. Implement writer (dry-run + backup) and tests (2-3 days)
5. Add CLI and integration tests (2 days)
6. Add more formats (FLAC/MP4) and expand tests (2-3 days)

---

## Acceptance / Deliverables 📦
- `songshare_analysis.id3` module with documented functions
- `bin/songshare-analyze` CLI command implementing `id3` subcommand
- Tests with fixtures and CI passing
- `docs/id3-tags-plan.md` (this doc) and an example usage snippet in `README.md`

---

## Risks & Mitigations ⚠️
- Corrupting files when writing: mitigate with backups, atomic writes, and dry-run.
- Format-specific pitfalls (e.g., ID3 versions): standardize on ID3v2.3 or 2.4 and test both.
- Large files / performance: operate on tags only (no audio decoding) so should be fast.

---

## Next steps (short term) ▶️
1. Start library research and confirm `mutagen` usage (assignable todo).
2. Implement a simple `analyze_file()` that reads tags and proposes updates from filename.
3. Add tests for analyze step and a small fixture MP3.
4. Prototype chord extraction using Essentia: `songshare_analysis.chords.extract_chords()` and `write_chord_sidecar()` (writes per-segment chord sequence + histogram to `<audio>.analysis.json`) — tests added.


---

If this plan looks good I can open the first implementation PR with the initial `mutagen`-based reader and a small CLI skeleton.
