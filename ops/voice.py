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
    names.sort(key=lambda n: (('pro' in n), n), reverse=True)   # a pro TTS model first, then the newest name
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
    for model in models:
        try:
            os.makedirs(out, exist_ok=True); timing = {'_model': model}
            for ln in script['lines']:
                for attempt in range(3):
                    try:
                        pcm = gemini_line(key, model, ln); break
                    except Exception as e:
                        if attempt == 2:
                            raise
                        print('retry', ln['id'], str(e)[:200]); time.sleep(8)
                timing[ln['id']] = round(save(os.path.join(out, ln['id'] + '.wav'), pcm), 3)
            json.dump(timing, open(os.path.join(out, 'timing.json'), 'w'), indent=1)
            print('gemini voice done with', model, timing); return True
        except Exception as e:
            print('::warning::gemini voice failed with', model, str(e)[:300])
    return False


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


if __name__ == '__main__':
    script = json.load(open(sys.argv[1]))
    base = os.path.join('social', 'voice', script['name'])
    ok_g = run_gemini(script, os.path.join(base, 'gemini'))
    ok_k = run_kokoro(script, os.path.join(base, 'kokoro'), os.environ.get('KOKORO_DIR', '/tmp/kokoro'))
    if not (ok_g or ok_k):
        sys.exit('no voice engine worked')
