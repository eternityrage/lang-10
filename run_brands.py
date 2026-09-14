import os
import sys
import argparse
import asyncio
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / '.env')

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, str(BASE_DIR))
from publisher import upload_reel_to_facebook

ENGINES = {
    'kotoka': ('brands.kotoka.kotoka_engine', 'Japanese'),
    'ivrina': ('brands.ivrina.ivrina_engine', 'Hebrew'),
    'voblo': ('brands.voblo.voblo_engine', 'Spanish'),
    'dimoi': ('brands.dimoi.dimoi_engine', 'French'),
    'spracho': ('brands.spracho.spracho_engine', 'German'),
    'dicoo': ('brands.dicoo.dicoo_engine', 'Italian'),
    'malamoo': ('brands.malamoo.malamoo_engine', 'Korean'),
    'bohua': ('brands.bohua.bohua_engine', 'Chinese'),
    'govoro': ('brands.govoro.govoro_engine', 'Russian'),
    'faloo': ('brands.faloo.faloo_engine', 'Portuguese'),
}

TAGS = {
    'kotoka': '#Japanese #LearnJapanese #Nihongo #Japan #AnimeJapanese #Kotoka #StudyJapanese',
    'ivrina': '#Hebrew #LearnHebrew #Ivrit #Israel #TelAviv #Ivrina #HebrewLanguage',
    'voblo': '#Spanish #LearnSpanish #Espanol #SpanishLanguage #Voblo #HablarEspanol',
    'dimoi': '#French #LearnFrench #Francais #Paris #Dimoi #FrenchPhrases #ParlerFrancais',
    'spracho': '#German #LearnGerman #Deutsch #Germany #Spracho #GermanA1 #DeutschLernen',
    'dicoo': '#Italian #LearnItalian #Italiano #Italy #Dicoo #ParlaItaliano #ItalianPhrases',
    'malamoo': '#Korean #LearnKorean #Hangul #KDrama #Malamoo #Kpop #KoreanLanguage',
    'bohua': '#Chinese #LearnChinese #Mandarin #Hanzi #Bohua #ChineseLanguage #Zhongwen',
    'govoro': '#Russian #LearnRussian #Russkiy #Govoro #RussianLanguage #RussianWords',
    'faloo': '#Portuguese #LearnPortuguese #Portugues #Brazil #Faloo #Brasil #Português'
}

async def run_brand_cycle(brand_name, upload=True):
    brand_lower = brand_name.lower()
    if brand_lower not in ENGINES:
        print(f"Unknown brand: {brand_name}")
        return

    mod_path, lang = ENGINES[brand_lower]
    print(f"\n============================================================")
    print(f"🚀 RUNNING CYCLE FOR {brand_name.upper()} ({lang})")
    print(f"============================================================")

    # Dynamic import of brand engine
    engine_file = BASE_DIR / brand_lower / f'{brand_lower}_engine.py'
    if not engine_file.exists():
        print(f"Engine file not found: {engine_file}")
        return

    import importlib.util
    spec = importlib.util.spec_from_file_location(f"{brand_lower}_engine", engine_file)
    brand_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(brand_mod)

    # Generate a brand new dialogue and video
    video_path = await brand_mod.generate_single_reel()
    print(f"[{brand_name}] New Video Generated: {video_path}")

    # Load the latest dialogue details from history
    hist = brand_mod.load_history()
    latest_entry = hist['dialogues'][-1]['dialogue']
    topic = latest_entry.get('topic', f'{lang} Daily Lesson')

    lines_summary = []
    for line in latest_entry.get('lines', []):
        native = line.get('target_text') or line.get('japanese') or line.get('korean') or line.get('chinese') or line.get('russian') or ''
        en = line.get('english', '')
        lines_summary.append(f"• {native} ({en})")

    dialogue_text = "\n".join(lines_summary)
    hashtags = TAGS.get(brand_lower, f"#{lang} #Learn{lang} #{brand_name.capitalize()}")

    caption = (
        f"✨ Daily {lang} in 15 Seconds! — {topic}\n\n"
        f"Master this quick conversation:\n"
        f"{dialogue_text}\n\n"
        f"Practice speaking it out loud! 💬 Save for later & follow @{brand_name.capitalize()} for daily lessons.\n\n"
        f"{hashtags}"
    )

    title = f"Daily {lang}: {topic}"

    if upload:
        upload_reel_to_facebook(
            video_path=video_path,
            title=title,
            description=caption,
            brand_name=brand_name
        )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Multi-Brand Autonomous Reel Runner")
    parser.add_argument('--brand', type=str, default='all', help="Brand to run (e.g. kotoka, ivrina, faloo, or 'all')")
    parser.add_argument('--no-upload', action='store_true', help="Skip upload step")
    args = parser.parse_args()

    should_upload = not args.no_upload

    if args.brand.lower() == 'all':
        for b in ENGINES.keys():
            asyncio.run(run_brand_cycle(b, upload=should_upload))
    else:
        asyncio.run(run_brand_cycle(args.brand, upload=should_upload))
