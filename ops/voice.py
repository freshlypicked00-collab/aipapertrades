"""Voiceover for the YouTube-first Shorts (owner, Nov 3: "higher quality content ... more targeted to youtube"; agreed standard S9:
a synthetic voiceover, no real person imitated, plus our own music).

Runs on GitHub (voice.yml), where the engines can be installed. Input: a script, ops/voice/<name>.json:
  {"name": "...", "lines": [{"id": "01", "who": "narrator", "text": "...", "style": "optional delivery note"}, ...]}
Output, for every engine that works: social/voice/<name>/<engine>/<id>.wav (mono, 24 kHz) and timing.json
({"<id>": seconds}). Engines:
  gemini  Google's Gemini text-to-speech (the race's Gemini API key; the newest *-tts model the key can see)
  kokoro  Kokoro-82M, open source (Apache-2.0), run on the runner: the fallback, and needs no key
Each line is one sentence or one quote, so the delivery sounds natural; captions are timed inside a line by word length.
  python3 ops/voice.py ops/voice/options-g-opt.json
"""
import base64
import json
import os
import sys
import time
import urllib.request
import wave

VOICES = {   # one fixed voice per character, so the three AIs are recognisable from Short to Short
    'narrator': {'gemini': 'Puck', 'kokoro': 'af_heart'},
    'claude': {'gemini': 'Sadaltager', 'kokoro': 'bm_george'},
    'gemini': {'gemini': 'Zephyr', 'kokoro': 'af_bella'},
    'chatgpt': {'gemini': 'Charon', 'kokoro': 'am_michael'},
}
SR = 24000


def save(path, pcm16, sr=SR):
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm16)
    return len(pcm16) / 2 / sr


def gemini_model(key):
    j = json.load(urllib.request.urlopen(f'https://generativelanguage.googleapis.com/v1beta/models?key={key}&pageSize=200', timeout=60))
    names = [m['name'].split('/')[-1] for m in j.get('models', []) if 'tts' in m['name']]
    import re as _re
    def rank(n):   # the newest generation first, never a "lite" one first, a finished (non-preview) one before a preview, pro before flash
        v = _re.search(r'(\d+(?:\.\d+)?)', n)
        return ('lite' not in n, float(v.group(1)) if v else 0, 'preview' not in n, 'pro' in n)
    names.sort(key=rank, reverse=True)
    if os.environ.get('TTS_MODEL'):
        names = [os.environ['TTS_MODEL']] + [n for n in names if n != os.environ['TTS_MODEL']]
    print('Gemini TTS models:', names)
    return names


def gemini_line(key, model, line):
    who = line.get('who', 'narrator')
    style = line.get('style') or ('Read like an energetic, clear YouTube Shorts narrator, fast but never rushed'
                                  if who == 'narrator' else 'Read this quote calmly and confidently, as the speaker')
    body = {'contents': [{'parts': [{'text': f'{style}: {line["text"]}'}]}],
            'generationConfig': {'responseModalities': ['AUDIO'],
                                 'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': VOICES[who]['gemini']}}}}}
    req = urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}',
                                 json.dumps(body).encode(), {'Content-Type': 'application/json'})
    j = json.load(urllib.request.urlopen(req, timeout=180))
    part = j['candidates'][0]['content']['parts'][0]['inlineData']
    return base64.b64decode(part['data'])   # 16-bit PCM, 24 kHz mono


def run_gemini(script, out):
    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        print('no GEMINI_API_KEY; gemini voice skipped'); return False
    models = gemini_model(key)
    os.makedirs(out, exist_ok=True); timing = {}
    for ln in script['lines']:
        done = False
        tries = [(m, True) for m in models] + [(m, False) for m in models[:2]]   # last: without the delivery note
        for model, styled in tries:
            l2 = dict(ln) if styled else {**ln, 'style': 'Read aloud'}
            try:
                for attempt in range(3):
                    try:
                        pcm = gemini_line(key, model, l2); break
                    except Exception as e:
                        if attempt == 2:
                            raise
                        print('retry', ln['id'], str(e)[:200]); time.sleep(8)
            except Exception as e:
                print('::warning::gemini voice failed with', model, str(e)[:200]); continue
            path = os.path.join(out, ln['id'] + '.wav')
            dur = save(path, pcm)
            try:
                w = heard(path)
            except Exception as e:
                print('::warning::could not listen back:', str(e)[:200]); w = None
            sc = match(ln['text'], w) if w is not None else None
            print(f'{ln["id"]} {model} styled={styled} {dur:.2f}s match={sc}')
            if sc is None or sc >= 0.85:
                timing[ln['id']] = {'s': round(dur, 3), 'model': model, 'styled': styled, 'match': sc}; done = True; break
        if not done:
            print('::warning::no Gemini voice said line ' + ln['id'] + ' correctly'); return False
    json.dump(timing, open(os.path.join(out, 'timing.json'), 'w'), indent=1)
    print('gemini voice done', timing); return True


def run_kokoro(script, out, model_dir):
    try:
        import numpy as np
        from kokoro_onnx import Kokoro
    except Exception as e:
        print('::warning::kokoro not installed:', e); return False
    k = Kokoro(os.path.join(model_dir, 'kokoro-v1.0.onnx'), os.path.join(model_dir, 'voices-v1.0.bin'))
    os.makedirs(out, exist_ok=True); timing = {'_model': 'kokoro-v1.0'}
    for ln in script['lines']:
        who = ln.get('who', 'narrator')
        audio, sr = k.create(ln['text'], voice=VOICES[who]['kokoro'], speed=float(ln.get('speed', 1.08 if who == 'narrator' else 1.0)), lang='en-us')
        pcm = (np.clip(audio, -1, 1) * 32767).astype('<i2').tobytes()
        timing[ln['id']] = round(save(os.path.join(out, ln['id'] + '.wav'), pcm, sr), 3)
    json.dump(timing, open(os.path.join(out, 'timing.json'), 'w'), indent=1)
    print('kokoro voice done', timing); return True


def load16k(path):
    import numpy as np
    with wave.open(path) as w:
        sr = w.getframerate(); x = np.frombuffer(w.readframes(w.getnframes()), '<i2').astype(np.float32) / 32768
    n = int(len(x) * 16000 / sr)
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


_WHISPER = None


def heard(path):
    """What a voice line actually says, with word times (faster-whisper, open source), or None if it is not installed."""
    global _WHISPER
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return None
    if _WHISPER is None:
        _WHISPER = WhisperModel(os.environ.get('WHISPER_MODEL', 'small.en'), device='cpu', compute_type='int8')
    segs, _ = _WHISPER.transcribe(load16k(path), language='en', word_timestamps=True, beam_size=5)
    return [[w.word.strip(), round(w.start, 3), round(w.end, 3)] for sg in segs for w in (sg.words or [])]


def match(text, words):
    import difflib, re as _re
    norm = lambda t: _re.sub(r'[^a-z0-9 ]', ' ', t.lower().replace('-', ' ')).split()
    return difflib.SequenceMatcher(None, norm(text), norm(' '.join(w[0] for w in words))).ratio()


def align(folder, script):
    """Word timings for the captions, and a check that the voice said the words in the script: each line is transcribed back with
    faster-whisper (open source, MIT). Writes words.json {line id: [[word, start, end], ...]} and a match score per line."""
    import difflib, re as _re
    norm = lambda t: _re.sub(r'[^a-z0-9 ]', ' ', t.lower().replace('-', ' ')).split()
    out, report = {}, {}
    for ln in script['lines']:
        wav = os.path.join(folder, ln['id'] + '.wav')
        if not os.path.exists(wav):
            continue
        words = heard(wav)
        if words is None:
            print('::warning::faster-whisper not installed, no word timings'); return
        out[ln['id']] = words
        said = ' '.join(w[0] for w in words)
        score = difflib.SequenceMatcher(None, norm(ln['text']), norm(said)).ratio()
        report[ln['id']] = {'heard': said, 'match': round(score, 3)}
        if score < 0.85:
            print(f'::warning::voice line {ln["id"]} may not say the script ({score:.2f}): heard "{said}"')
    json.dump(out, open(os.path.join(folder, 'words.json'), 'w'), indent=0)
    json.dump(report, open(os.path.join(folder, 'check.json'), 'w'), indent=1)
    print('aligned', folder, report)


if __name__ == '__main__':
    script = json.load(open(sys.argv[1]))
    base = os.path.join('social', 'voice', script['name'])
    ok_g = os.environ.get('ENGINES', 'gemini,kokoro').find('gemini') >= 0 and run_gemini(script, os.path.join(base, 'gemini'))
    ok_k = os.environ.get('ENGINES', 'gemini,kokoro').find('kokoro') >= 0 and run_kokoro(script, os.path.join(base, 'kokoro'), os.environ.get('KOKORO_DIR', '/tmp/kokoro'))
    if not (ok_g or ok_k):
        sys.exit('no voice engine worked')
    for eng, ok in (('gemini', ok_g), ('kokoro', ok_k)):
        if ok:
            try:
                align(os.path.join(base, eng), script)
            except Exception as e:
                print('::warning::word timings failed for', eng, str(e)[:300])
