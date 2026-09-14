from pathlib import Path
from PIL import ImageFont

FONTS_DIR = Path(__file__).parent / 'assets' / 'fonts'

def get_platform_font(style='bold', lang='default', size=74):
    """
    Returns an ImageFont that works identically on both Windows and Linux (GitHub Actions runner).
    """
    # 1. Check local assets/fonts first
    if FONTS_DIR.exists():
        candidates = {
            'hebrew': ['DavidCLM-Bold.otf', 'FrankRuehlCLM-Bold.otf'],
            'japanese': ['NotoSansCJK-Bold.ttc', 'YuGothB.ttc'],
            'korean': ['NotoSansCJK-Bold.ttc', 'malgunbd.ttf'],
            'chinese': ['NotoSansCJK-Bold.ttc', 'msyhbd.ttc'],
            'default': ['DejaVuSans-Bold.ttf' if style == 'bold' else 'DejaVuSans.ttf', 'segoeuib.ttf']
        }
        for fname in candidates.get(lang, candidates['default']):
            fpath = FONTS_DIR / fname
            if fpath.exists():
                try: return ImageFont.truetype(str(fpath), size)
                except: pass

    # 2. Linux (Ubuntu GitHub Actions Runner) Font Paths
    linux_fonts = {
        'hebrew': ['/usr/share/fonts/truetype/culmus/DavidCLM-Bold.otf', '/usr/share/fonts/opentype/noto/NotoSansHebrew-Bold.ttf'],
        'japanese': ['/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'],
        'korean': ['/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'],
        'chinese': ['/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'],
        'default': [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if style == 'bold' else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf'
        ]
    }

    # 3. Windows Font Paths
    win_fonts = {
        'hebrew': ['C:/Windows/Fonts/davidbd.ttf', 'C:/Windows/Fonts/segoeuib.ttf'],
        'japanese': ['C:/Windows/Fonts/YuGothB.ttc', 'C:/Windows/Fonts/meiryo.ttc'],
        'korean': ['C:/Windows/Fonts/malgunbd.ttf'],
        'chinese': ['C:/Windows/Fonts/msyhbd.ttc'],
        'default': [
            'C:/Windows/Fonts/segoeuib.ttf' if style == 'bold' else 'C:/Windows/Fonts/segoeui.ttf',
            'C:/Windows/Fonts/arialbd.ttf'
        ]
    }

    import sys
    target_list = (win_fonts if sys.platform == 'win32' else linux_fonts).get(lang, []) + (win_fonts if sys.platform == 'win32' else linux_fonts)['default']
    for p in target_list:
        try:
            return ImageFont.truetype(p, size)
        except:
            continue

    return ImageFont.load_default()
