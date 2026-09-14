import sys
from pathlib import Path
from PIL import ImageFont

BASE_DIR = Path(__file__).parent

def get_platform_font(style='bold', lang='default', size=74):
    """
    Returns an ImageFont that works identically on both Windows and Linux (Ubuntu GitHub Actions runner).
    Handles Japanese, Hebrew, Korean, Chinese, Russian/Cyrillic, and Latin alphabets.
    """
    # 1. Check local assets/fonts in root or subdirectories
    font_dirs = [
        BASE_DIR / 'assets' / 'fonts',
        BASE_DIR / lang / 'assets' / 'fonts'
    ]
    candidates = {
        'hebrew': ['DavidCLM-Bold.otf', 'FrankRuehlCLM-Bold.otf'],
        'he': ['DavidCLM-Bold.otf', 'FrankRuehlCLM-Bold.otf'],
        'japanese': ['NotoSansCJK-Bold.ttc', 'YuGothB.ttc'],
        'ja': ['NotoSansCJK-Bold.ttc', 'YuGothB.ttc'],
        'korean': ['NotoSansCJK-Bold.ttc', 'malgunbd.ttf'],
        'ko': ['NotoSansCJK-Bold.ttc', 'malgunbd.ttf'],
        'chinese': ['NotoSansCJK-Bold.ttc', 'msyhbd.ttc'],
        'zh': ['NotoSansCJK-Bold.ttc', 'msyhbd.ttc'],
        'russian': ['DejaVuSans-Bold.ttf', 'segoeuib.ttf'],
        'ru': ['DejaVuSans-Bold.ttf', 'segoeuib.ttf'],
        'default': ['DejaVuSans-Bold.ttf' if style == 'bold' else 'DejaVuSans.ttf', 'segoeuib.ttf']
    }

    for fdir in font_dirs:
        if fdir.exists():
            for fname in candidates.get(lang, candidates['default']):
                fpath = fdir / fname
                if fpath.exists():
                    try:
                        return ImageFont.truetype(str(fpath), size)
                    except Exception:
                        pass

    # 2. Linux (Ubuntu GitHub Actions Runner) System Paths
    linux_fonts = {
        'hebrew': [
            '/usr/share/fonts/truetype/culmus/DavidCLM-Bold.otf',
            '/usr/share/fonts/truetype/culmus/FrankRuehlCLM-Bold.otf',
            '/usr/share/fonts/opentype/noto/NotoSansHebrew-Bold.ttf'
        ],
        'he': [
            '/usr/share/fonts/truetype/culmus/DavidCLM-Bold.otf',
            '/usr/share/fonts/truetype/culmus/FrankRuehlCLM-Bold.otf',
            '/usr/share/fonts/opentype/noto/NotoSansHebrew-Bold.ttf'
        ],
        'japanese': [
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
        ],
        'ja': [
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
        ],
        'korean': [
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
        ],
        'ko': [
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
        ],
        'chinese': [
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
        ],
        'zh': [
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc',
            '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
        ],
        'russian': [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if style == 'bold' else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf'
        ],
        'ru': [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if style == 'bold' else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf'
        ],
        'default': [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if style == 'bold' else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/usr/share/fonts/truetype/freefont/FreeSansBold.ttf'
        ]
    }

    # 3. Windows System Paths
    win_fonts = {
        'hebrew': ['C:/Windows/Fonts/davidbd.ttf', 'C:/Windows/Fonts/segoeuib.ttf'],
        'he': ['C:/Windows/Fonts/davidbd.ttf', 'C:/Windows/Fonts/segoeuib.ttf'],
        'japanese': ['C:/Windows/Fonts/YuGothB.ttc', 'C:/Windows/Fonts/meiryo.ttc', 'C:/Windows/Fonts/msgothic.ttc'],
        'ja': ['C:/Windows/Fonts/YuGothB.ttc', 'C:/Windows/Fonts/meiryo.ttc', 'C:/Windows/Fonts/msgothic.ttc'],
        'korean': ['C:/Windows/Fonts/malgunbd.ttf', 'C:/Windows/Fonts/malgun.ttf'],
        'ko': ['C:/Windows/Fonts/malgunbd.ttf', 'C:/Windows/Fonts/malgun.ttf'],
        'chinese': ['C:/Windows/Fonts/msyhbd.ttc', 'C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf'],
        'zh': ['C:/Windows/Fonts/msyhbd.ttc', 'C:/Windows/Fonts/msyh.ttc', 'C:/Windows/Fonts/simhei.ttf'],
        'russian': ['C:/Windows/Fonts/segoeuib.ttf', 'C:/Windows/Fonts/arialbd.ttf'],
        'ru': ['C:/Windows/Fonts/segoeuib.ttf', 'C:/Windows/Fonts/arialbd.ttf'],
        'default': [
            'C:/Windows/Fonts/segoeuib.ttf' if style == 'bold' else 'C:/Windows/Fonts/segoeui.ttf',
            'C:/Windows/Fonts/arialbd.ttf'
        ]
    }

    font_table = win_fonts if sys.platform == 'win32' else linux_fonts
    target_list = font_table.get(lang, []) + font_table['default']

    for p in target_list:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue

    return ImageFont.load_default()
