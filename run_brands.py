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
from publisher import upload_reel_to_facebook, upload_reel_to_youtube, should_upload_to_youtube

# Standard ISO Language Mappings (Discrete / SEO-Neutral)
ENGINES = {
    'ja': ('ja.ja_engine', 'Japanese', 'ja'),
    'he': ('he.he_engine', 'Hebrew', 'he'),
    'es': ('es.es_engine', 'Spanish', 'es'),
    'fr': ('fr.fr_engine', 'French', 'fr'),
    'de': ('de.de_engine', 'German', 'de'),
    'it': ('it.it_engine', 'Italian', 'it'),
    'ko': ('ko.ko_engine', 'Korean', 'ko'),
    'zh': ('zh.zh_engine', 'Chinese', 'zh'),
    'ru': ('ru.ru_engine', 'Russian', 'ru'),
    'pt': ('pt.pt_engine', 'Portuguese', 'pt'),
}

TAGS = {
    'ja': '#Japanese #LearnJapanese #Nihongo #Japan #AnimeJapanese #StudyJapanese',
    'he': '#Hebrew #LearnHebrew #Ivrit #Israel #TelAviv #HebrewLanguage',
    'es': '#Spanish #LearnSpanish #Espanol #SpanishLanguage #HablarEspanol',
    'fr': '#French #LearnFrench #Francais #Paris #FrenchPhrases #ParlerFrancais',
    'de': '#German #LearnGerman #Deutsch #Germany #GermanA1 #DeutschLernen',
    'it': '#Italian #LearnItalian #Italiano #Italy #ParlaItaliano #ItalianPhrases',
    'ko': '#Korean #LearnKorean #Hangul #KDrama #Kpop #KoreanLanguage',
    'zh': '#Chinese #LearnChinese #Mandarin #Hanzi #ChineseLanguage #Zhongwen',
    'ru': '#Russian #LearnRussian #Russkiy #RussianLanguage #RussianWords',
    'pt': '#Portuguese #LearnPortuguese #Portugues #Brazil #Brasil #Português'
}

async def run_cycle(lang_code, upload=True, youtube_mode='auto'):
    lang_code = lang_code.lower()
    if lang_code not in ENGINES:
        print(f"Unknown language code: {lang_code}")
        return

    mod_path, lang_name, brand_id = ENGINES[lang_code]
    print(f"\n============================================================")
    print(f"RUNNING MODULE: {lang_code.upper()} ({lang_name})")
    print(f"============================================================")

    engine_file = BASE_DIR / lang_code / f'{lang_code}_engine.py'
    if not engine_file.exists():
        print(f"Engine file not found: {engine_file}")
        return

    import importlib.util
    spec = importlib.util.spec_from_file_location(f"{lang_code}_engine", engine_file)
    lang_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lang_mod)

    # Generate dialogue and render 15-second reel
    video_path = await lang_mod.generate_single_reel()
    print(f"[{lang_code}] Generated: {video_path}")

    # Read latest generated lines for post caption & pinned study note
    hist = lang_mod.load_history()
    latest_entry = hist['dialogues'][-1]['dialogue']
    topic = latest_entry.get('topic', f'{lang_name} Daily Lesson')

    lines_summary = []
    for line in latest_entry.get('lines', []):
        native = line.get('target_text') or line.get('japanese') or line.get('korean') or line.get('chinese') or line.get('russian') or ''
        en = line.get('english', '')
        lines_summary.append(f"• {native} ({en})")

    dialogue_text = "\n".join(lines_summary)
    hashtags = TAGS.get(lang_code, f"#{lang_name} #Learn{lang_name}")

    caption = (
        f"✨ Daily {lang_name} in 15 Seconds! — {topic}\n\n"
        f"Master this quick conversation:\n"
        f"{dialogue_text}\n\n"
        f"Practice speaking it out loud! 💬 Save for later & follow for daily lessons.\n\n"
        f"{hashtags}"
    )

    title = f"Daily {lang_name}: {topic}"

    if upload:
        # 1. Facebook Reels (regular 4x daily schedule)
        upload_reel_to_facebook(
            video_path=video_path,
            title=title,
            description=caption,
            brand_name=lang_code
        )

        # 2. YouTube Shorts (strictly 2x daily schedule)
        yt_allowed, yt_reason = should_upload_to_youtube(lang_code, mode=youtube_mode)
        if yt_allowed:
            print(f"[{lang_code}] 🎬 YouTube upload eligible: {yt_reason}")
            yt_tags = [
                f"learn {lang_name.lower()}",
                f"{lang_name.lower()} lesson",
                f"{lang_name.lower()} phrases",
                f"{lang_name.lower()} for beginners",
                "language learning",
                "shorts",
                topic.lower(),
                f"daily {lang_name.lower()}"
            ]
            upload_reel_to_youtube(
                video_path=video_path,
                title=title,
                description=caption,
                tags=yt_tags,
                brand_name=lang_code
            )
        else:
            print(f"[{lang_code}] ⏭️ Skipping YouTube upload: {yt_reason}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Language Matrix Execution Module")
    parser.add_argument('--lang', type=str, default='all', help="Language code (e.g. ja, he, es, or 'all')")
    parser.add_argument('--no-upload', action='store_true', help="Skip upload step")
    parser.add_argument('--youtube', type=str, choices=['auto', 'force', 'skip'], default='auto',
                        help="YouTube upload mode: auto (strictly 2x daily quota), force (bypass quota), or skip")
    args = parser.parse_args()

    should_upload = not args.no_upload

    if args.lang.lower() == 'all':
        for code in ENGINES.keys():
            asyncio.run(run_cycle(code, upload=should_upload, youtube_mode=args.youtube))
    else:
        asyncio.run(run_cycle(args.lang, upload=should_upload, youtube_mode=args.youtube))
