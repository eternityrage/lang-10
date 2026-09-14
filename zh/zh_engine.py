import os
import sys
import re
import json
import random
import asyncio
import subprocess
import wave
import requests
import numpy as np
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
sys.path.insert(0, str(Path(__file__).parent.parent))
from font_loader import get_platform_font
import edge_tts

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / '.env')

POLLINATIONS_API_KEY = os.getenv('POLLINATIONS_API_KEY')
AI_MODEL = os.getenv('AI_MODEL', 'openai-large')

ASSETS_DIR = BASE_DIR / 'assets'
CHAR_DIR = ASSETS_DIR / 'characters'
OUTPUT_DIR = BASE_DIR / 'output'
AUDIO_DIR = OUTPUT_DIR / 'audio'
VIDEO_DIR = OUTPUT_DIR / 'video'
HISTORY_DIR = OUTPUT_DIR / 'history'

for d in [ASSETS_DIR, CHAR_DIR, OUTPUT_DIR, AUDIO_DIR, VIDEO_DIR, HISTORY_DIR]:
    d.mkdir(parents=True, exist_ok=True)

HISTORY_FILE = HISTORY_DIR / 'dialogue_history.json'

WIDTH = 1080
HEIGHT = 1920
FPS = 24

VOICE_A = 'zh-CN-XiaoxiaoNeural'
VOICE_B = 'zh-CN-YunyangNeural'

CATEGORIES = [
    'Night Market Street Food', 'Ordering Milk Tea', 'Daily Greetings',
    'Bargaining & Shopping', 'Metro & Taxi', 'Compliments & Slang',
    'Hotpot Dinner', 'Morning Coffee'
]

def load_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'dialogues': []}

def save_dialogue_to_history(dialogue_data):
    hist = load_history()
    hist['dialogues'].append({
        'timestamp': datetime.now().isoformat(),
        'dialogue': dialogue_data
    })
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(hist, f, indent=2, ensure_ascii=False)

def generate_ai_dialogue(category=None):
    if not category:
        category = random.choice(CATEGORIES)
    hist = load_history()
    recent = [d['dialogue']['lines'][0]['english'] for d in hist.get('dialogues', [])[-30:] if 'dialogue' in d and 'lines' in d['dialogue']]
    context = chr(10).join(['- ' + r for r in recent[:15]])

    prompt = (
        'Generate an ultra-simple, beginner-friendly 4-line Mandarin Chinese dialogue (Level 1 / HSK 1 beginner) between Character A and Character B.\n'
        f'Category: {category}\n'
        'CRITICAL SIMPLICITY REQUIREMENTS:\n'
        '- Keep each sentence TINY, SIMPLE, and beginner-level (3 to 6 words/characters max per sentence!).\n'
        '- Level: Absolute beginner everyday conversational Chinese (clean, cute, natural).\n'
        '- Anyone seeing the reel should be able to instantly memorize and repeat each line!\n'
        '- Provide English, Chinese Hanzi (simplified), and Pinyin (with tone marks).\n'
        '- Flow: Turn 1 (A) question/greeting -> Turn 2 (B) cheerful answer -> Turn 3 (A) follow-up -> Turn 4 (B) conclusion.\n'
        f'Avoid repeating recent topics:\n{context}\n'
        'Return pure JSON only with keys: topic (string) and lines (list of exactly 4 items, each with speaker ["A" or "B"], english, chinese, pinyin).'
    )

    url = 'https://gen.pollinations.ai/v1/chat/completions'
    headers = {
        'Authorization': 'Bearer ' + str(POLLINATIONS_API_KEY),
        'Content-Type': 'application/json'
    }
    payload = {
        'model': AI_MODEL,
        'messages': [
            {'role': 'system', 'content': 'You are an expert Chinese teacher creating viral micro-dialogues for absolute beginners. Keep sentences short, clean, and memorable. Output ONLY valid JSON.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.75
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=30)
        if res.status_code == 200:
            raw = res.json()['choices'][0]['message']['content'].strip()
            raw = re.sub(r'^```json\s*', '', raw)
            raw = re.sub(r'\s*```$', '', raw)
            data = json.loads(raw)
            speakers = ['A', 'B', 'A', 'B']
            if 'lines' in data:
                for idx, item in enumerate(data['lines'][:4]):
                    item['speaker'] = speakers[idx % len(speakers)]
                    if 'chinese' not in item:
                        for k in ['hanzi', 'mandarin', 'target_text', 'text']:
                            if k in item: item['chinese'] = item[k]; break
                    if 'pinyin' not in item:
                        for k in ['pronunciation', 'romanization', 'romaji']:
                            if k in item: item['pinyin'] = item[k]; break
                    item['japanese'] = item.get('chinese', '')
                    item['romaji'] = item.get('pinyin', '')
                data['lines'] = data['lines'][:4]
            print('[Bohua Chinese] Generated dialogue: ' + str(data.get('topic')))
            return data
    except Exception as e:
        print('[Bohua Chinese] Fallback triggered: ' + str(e))

    return {
        'topic': category,
        'lines': [
            {'speaker': 'A', 'english': 'Hello! Is this milk tea sweet?', 'chinese': '你好！这杯奶茶甜吗？', 'pinyin': 'Nǐ hǎo! Zhè bēi nǎichá tián ma?', 'japanese': '你好！这杯奶茶甜吗？', 'romaji': 'Nǐ hǎo! Zhè bēi nǎichá tián ma?'},
            {'speaker': 'B', 'english': 'Not too sweet, just right!', 'chinese': '不太甜，刚刚好！', 'pinyin': 'Bú tài tián, gānggāng hǎo!', 'japanese': '不太甜，刚刚好！', 'romaji': 'Bú tài tián, gānggāng hǎo!'},
            {'speaker': 'A', 'english': 'One cup with boba please.', 'chinese': '来一杯珍珠奶茶。', 'pinyin': 'Lái yì bēi zhēnzhū nǎichá.', 'japanese': '来一杯珍珠奶茶。', 'romaji': 'Lái yì bēi zhēnzhū nǎichá.'},
            {'speaker': 'B', 'english': 'Okay, here you go!', 'chinese': '好的，给您！', 'pinyin': 'Hǎo de, gěi nín!', 'japanese': '好的，给您！', 'romaji': 'Hǎo de, gěi nín!'}
        ]
    }

def wrap_cjk(text, font, max_w=920):
    lines = []
    cur = ''
    for ch in text:
        test = cur + ch
        bbox = font.getbbox(test)
        if (bbox[2] - bbox[0]) <= max_w:
            cur = test
        else:
            if cur: lines.append(cur)
            cur = ch
    if cur: lines.append(cur)
    return chr(10).join(lines)

def wrap_text(text, font, max_w=920):
    words = text.split(' ')
    lines = []
    cur = []
    for w in words:
        test = ' '.join(cur + [w])
        bbox = font.getbbox(test)
        if (bbox[2] - bbox[0]) <= max_w:
            cur.append(w)
        else:
            if cur: lines.append(' '.join(cur))
            cur = [w]
    if cur: lines.append(' '.join(cur))
    return chr(10).join(lines)

def analyze_audio_speaking_timeline(audio_mp3_path):
    wav_path = audio_mp3_path.with_suffix('.wav')
    subprocess.run(['ffmpeg', '-y', '-i', str(audio_mp3_path), '-ar', '16000', '-ac', '1', str(wav_path)], capture_output=True)
    with wave.open(str(wav_path), 'rb') as wf:
        n_frames = wf.getnframes()
        rate = wf.getframerate()
        audio = np.frombuffer(wf.readframes(n_frames), dtype=np.int16)
    
    samples_per_frame = int(rate / FPS)
    total_frames = int(len(audio) / samples_per_frame)
    
    energies = []
    for i in range(total_frames):
        chunk = audio[i*samples_per_frame : (i+1)*samples_per_frame]
        rms = np.sqrt(np.mean(chunk.astype(np.float32)**2)) if len(chunk) > 0 else 0
        energies.append(rms)
        
    peak = max(energies) if energies else 1
    # Responsive threshold: 8% of peak
    threshold = peak * 0.08
    active_flags = [bool(e > threshold) for e in energies]
    return active_flags

def render_frame(speaker_speaking, is_talking, mouth_flap, line_data, font_en, font_zh, font_ro):
    bg = Image.new('RGB', (WIDTH, HEIGHT), color=(39, 11, 234))
    draw = ImageDraw.Draw(bg)

    # Wrap texts cleanly within safety margins
    wrapped_en = wrap_text(line_data['english'], font_en, max_w=920)
    raw_chinese = line_data.get('chinese', line_data.get('japanese', ''))
    wrapped_zh = wrap_cjk(raw_chinese, font_zh, max_w=920)
    raw_pinyin = line_data.get('pinyin', line_data.get('romaji', ''))
    wrapped_ro = wrap_text(raw_pinyin, font_ro, max_w=920)

    # Measure exact bounding boxes for stacked layout
    bbox_en = draw.multiline_textbbox((0, 0), wrapped_en, font=font_en, align='center', spacing=12)
    h_en = bbox_en[3] - bbox_en[1]

    bbox_zh = draw.multiline_textbbox((0, 0), wrapped_zh, font=font_zh, align='center', spacing=18)
    h_zh = bbox_zh[3] - bbox_zh[1]

    bbox_ro = draw.multiline_textbbox((0, 0), wrapped_ro, font=font_ro, align='center', spacing=12)
    h_ro = bbox_ro[3] - bbox_ro[1]

    gap_1 = 50  # Gap between English and Chinese
    gap_2 = 45  # Gap between Chinese and Pinyin
    total_text_h = h_en + gap_1 + h_zh + gap_2 + h_ro

    # Center the entire text stack vertically in the upper region (Y: 150 to 1100)
    top_y = 180 + (850 - total_text_h) // 2
    if top_y < 160:
        top_y = 160

    cur_y = top_y
    draw.multiline_text((WIDTH // 2, cur_y), wrapped_en, fill=(112, 174, 255), font=font_en, anchor='ma', align='center', spacing=12)
    cur_y += h_en + gap_1

    draw.multiline_text((WIDTH // 2, cur_y), wrapped_zh, fill=(255, 255, 255), font=font_zh, anchor='ma', align='center', spacing=18)
    cur_y += h_zh + gap_2

    draw.multiline_text((WIDTH // 2, cur_y), wrapped_ro, fill=(112, 174, 255), font=font_ro, anchor='ma', align='center', spacing=12)

    # Mouth only opens when speaker is currently talking AND mouth flap cadence is open
    char_a_mouth_open = (speaker_speaking == 'A' and is_talking and mouth_flap)
    char_b_mouth_open = (speaker_speaking == 'B' and is_talking and mouth_flap)

    file_a = 'char_a_talk.png' if char_a_mouth_open else 'char_a_idle.png'
    file_b = 'char_b_talk.png' if char_b_mouth_open else 'char_b_idle.png'

    ca = Image.open(CHAR_DIR / file_a).convert('RGBA').resize((460, 460), Image.Resampling.LANCZOS)
    cb = Image.open(CHAR_DIR / file_b).convert('RGBA').resize((460, 460), Image.Resampling.LANCZOS)

    # Cute bounce when mouth opens
    bounce_a = -18 if char_a_mouth_open else 0
    bounce_b = -18 if char_b_mouth_open else 0

    bg.paste(ca, (70, 1170 + bounce_a), ca)
    bg.paste(cb, (530, 1170 + bounce_b), cb)
    return bg

async def generate_single_reel():
    dialogue = generate_ai_dialogue()
    save_dialogue_to_history(dialogue)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    reel_id = f'bohua_{timestamp}'

    font_en = get_platform_font(style='bold', lang='default', size=58)
    font_zh = get_platform_font(style='bold', lang='zh', size=76)
    font_ro = get_platform_font(style='regular', lang='default', size=52)

    segments = []
    for i, line in enumerate(dialogue['lines']):
        frames_temp = OUTPUT_DIR / f'temp_frames_{reel_id}_{i}'
        frames_temp.mkdir(parents=True, exist_ok=True)
        aud_path = AUDIO_DIR / f'{reel_id}_aud_{i}.mp3'
        voice = VOICE_A if line['speaker'] == 'A' else VOICE_B
        pitch = "+4Hz" if line['speaker'] == 'A' else "+2Hz"
        rate = "-18%" if line['speaker'] == 'A' else "-22%"
        clean_zh = line['chinese'].replace('\n', ' ')
        
        # Slower, clearer pronunciation for beginners with retry resilience
        for attempt in range(4):
            try:
                comm = edge_tts.Communicate(clean_zh, voice, rate=rate, pitch=pitch)
                await comm.save(str(aud_path))
                break
            except Exception as err:
                if attempt == 3:
                    raise err
                await asyncio.sleep(1.0)

        # Pad audio with 1.1s of silence at the end so learners have time to process and read
        padded_aud_path = AUDIO_DIR / f'{reel_id}_aud_{i}_pad.mp3'
        subprocess.run([
            'ffmpeg', '-y',
            '-i', str(aud_path),
            '-af', 'apad=pad_dur=1.1',
            str(padded_aud_path)
        ], capture_output=True)

        active_flags = analyze_audio_speaking_timeline(padded_aud_path)
        total_frames = len(active_flags)

        for old in frames_temp.glob('*.jpg'):
            old.unlink()

        seg_vid = OUTPUT_DIR / f'{reel_id}_seg_{i}.mp4'
        cmd = [
            'ffmpeg', '-y',
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{WIDTH}x{HEIGHT}',
            '-pix_fmt', 'rgb24',
            '-r', str(FPS),
            '-i', '-',
            '-i', str(padded_aud_path),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-preset', 'ultrafast',
            '-shortest',
            str(seg_vid)
        ]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        speaking_counter = 0
        for f in range(total_frames):
            is_active = active_flags[f]
            if is_active:
                speaking_counter += 1
                mouth_flap = ((speaking_counter // 3) % 2 == 1)
            else:
                speaking_counter = 0
                mouth_flap = False
                
            im = render_frame(line['speaker'], is_active, mouth_flap, line, font_en, font_zh, font_ro)
            proc.stdin.write(im.tobytes())
        proc.stdin.close()
        proc.wait()
        segments.append(seg_vid)

    concat_txt = OUTPUT_DIR / f'concat_{reel_id}.txt'
    with open(concat_txt, 'w', encoding='utf-8') as f:
        for s in segments:
            p = str(s.resolve()).replace('\\', '/')
            f.write('file \'' + p + '\'\n')

    final_vid = VIDEO_DIR / f'{reel_id}.mp4'
    subprocess.run(['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat_txt), '-c', 'copy', str(final_vid)], capture_output=True)
    
    for i in range(len(dialogue['lines'])):
        f_dir = OUTPUT_DIR / f'temp_frames_{reel_id}_{i}'
        for f in f_dir.glob('*.*'): f.unlink(missing_ok=True)
        try: f_dir.rmdir()
        except: pass
    for s in segments:
        s.unlink(missing_ok=True)
    concat_txt.unlink(missing_ok=True)

    print('\n[Bohua Chinese] Generated: ' + str(final_vid.name))
    return final_vid

if __name__ == '__main__':
    asyncio.run(generate_single_reel())
