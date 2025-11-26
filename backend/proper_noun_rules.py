"""
Proper Noun Translation Map

This map is used ONLY to translate user-entered keywords when they are proper nouns.
It does NOT add any keywords - only provides correct translations for names/places.

Purpose: Fix Google Translate errors for proper nouns
Example: "ترامب" should translate to "Trump" in French, not "Atout" (trump card)
"""

# Proper noun translations
# Only used when a user's keyword matches an entry
# Does NOT inject new search terms
PROPER_NOUNS = {
    # Political Figures
    'ترامب': {
        'en': 'Trump',
        'fr': 'Trump',
        'es': 'Trump',
        'ru': 'Трамп',
        'zh': '特朗普',
        'zh-cn': '特朗普'
    },
    
    'بايدن': {
        'en': 'Biden',
        'fr': 'Biden',
        'es': 'Biden',
        'ru': 'Байден',
        'zh': '拜登',
        'zh-cn': '拜登'
    },
    
    'بوتين': {
        'en': 'Putin',
        'fr': 'Poutine',
        'es': 'Putin',
        'ru': 'Путин',
        'zh': '普京',
        'zh-cn': '普京'
    },
    
    'ماكرون': {
        'en': 'Macron',
        'fr': 'Macron',
        'es': 'Macron',
        'ru': 'Макрон',
        'zh': '马克龙',
        'zh-cn': '马克龙'
    },
    
    'شي جين بينغ': {
        'en': 'Xi Jinping',
        'fr': 'Xi Jinping',
        'es': 'Xi Jinping',
        'ru': 'Си Цзиньпин',
        'zh': '习近平',
        'zh-cn': '习近平'
    },
    
    'نتنياهو': {
        'en': 'Netanyahu',
        'fr': 'Netanyahou',
        'es': 'Netanyahu',
        'ru': 'Нетаньяху',
        'zh': '内塔尼亚胡',
        'zh-cn': '内塔尼亚胡'
    },
    
    'زيلينسكي': {
        'en': 'Zelensky',
        'fr': 'Zelensky',
        'es': 'Zelensky',
        'ru': 'Зеленский',
        'zh': '泽连斯基',
        'zh-cn': '泽连斯基'
    },
    
    # Countries
    'السعودية': {
        'en': 'Saudi Arabia',
        'fr': 'Arabie Saoudite',
        'es': 'Arabia Saudita',
        'ru': 'Саудовская Аравия',
        'zh': '沙特阿拉伯',
        'zh-cn': '沙特阿拉伯'
    },
    
    'أمريكا': {
        'en': 'America',
        'fr': 'Amérique',
        'es': 'América',
        'ru': 'Америка',
        'zh': '美国',
        'zh-cn': '美国'
    },
    
    'فرنسا': {
        'en': 'France',
        'fr': 'France',
        'es': 'Francia',
        'ru': 'Франция',
        'zh': '法国',
        'zh-cn': '法国'
    },
    
    'الصين': {
        'en': 'China',
        'fr': 'Chine',
        'es': 'China',
        'ru': 'Китай',
        'zh': '中国',
        'zh-cn': '中国'
    },
    
    'روسيا': {
        'en': 'Russia',
        'fr': 'Russie',
        'es': 'Rusia',
        'ru': 'Россия',
        'zh': '俄罗斯',
        'zh-cn': '俄罗斯'
    },
    
    'بريطانيا': {
        'en': 'Britain',
        'fr': 'Bretagne',
        'es': 'Bretaña',
        'ru': 'Британия',
        'zh': '英国',
        'zh-cn': '英国'
    },
    
    'ألمانيا': {
        'en': 'Germany',
        'fr': 'Allemagne',
        'es': 'Alemania',
        'ru': 'Германия',
        'zh': '德国',
        'zh-cn': '德国'
    },
    
    'إيران': {
        'en': 'Iran',
        'fr': 'Iran',
        'es': 'Irán',
        'ru': 'Иран',
        'zh': '伊朗',
        'zh-cn': '伊朗'
    },
    
    'أوروبا': {
        'en': 'Europe',
        'fr': 'Europe',
        'es': 'Europa',
        'ru': 'Европа',
        'zh': '欧洲',
        'zh-cn': '欧洲'
    },
    
    'آسيا': {
        'en': 'Asia',
        'fr': 'Asie',
        'es': 'Asia',
        'ru': 'Азия',
        'zh': '亚洲',
        'zh-cn': '亚洲'
    },
    
    # Cities
    'الرياض': {
        'en': 'Riyadh',
        'fr': 'Riyad',
        'es': 'Riad',
        'ru': 'Эр-Рияд',
        'zh': '利雅得',
        'zh-cn': '利雅得'
    },
    
    'باريس': {
        'en': 'Paris',
        'fr': 'Paris',
        'es': 'París',
        'ru': 'Париж',
        'zh': '巴黎',
        'zh-cn': '巴黎'
    },
    
    'لندن': {
        'en': 'London',
        'fr': 'Londres',
        'es': 'Londres',
        'ru': 'Лондон',
        'zh': '伦敦',
        'zh-cn': '伦敦'
    },
    
    'موسكو': {
        'en': 'Moscow',
        'fr': 'Moscou',
        'es': 'Moscú',
        'ru': 'Москва',
        'zh': '莫斯科',
        'zh-cn': '莫斯科'
    },
    
    'بكين': {
        'en': 'Beijing',
        'fr': 'Pékin',
        'es': 'Pekín',
        'ru': 'Пекин',
        'zh': '北京',
        'zh-cn': '北京'
    },
    
    'واشنطن': {
        'en': 'Washington',
        'fr': 'Washington',
        'es': 'Washington',
        'ru': 'Вашингтон',
        'zh': '华盛顿',
        'zh-cn': '华盛顿'
    }
}


def get_proper_noun_forms(keyword_ar):
    """
    Get proper noun translations for a keyword if it exists in the map
    
    Args:
        keyword_ar: Arabic keyword
        
    Returns:
        dict of translations or None if not a known proper noun
    """
    return PROPER_NOUNS.get(keyword_ar)


def is_known_proper_noun(keyword_ar):
    """
    Check if a keyword is in the proper noun map
    
    Args:
        keyword_ar: Arabic keyword
        
    Returns:
        bool
    """
    return keyword_ar in PROPER_NOUNS


def add_proper_noun(keyword_ar, translations):
    """
    Add a new proper noun to the map (for future expansion)
    
    Args:
        keyword_ar: Arabic keyword
        translations: dict with language codes and translations
    """
    PROPER_NOUNS[keyword_ar] = translations
    print(f"✅ Added proper noun: {keyword_ar}")


def list_proper_nouns():
    """
    Get list of all proper nouns in the map
    
    Returns:
        list of Arabic keywords
    """
    return list(PROPER_NOUNS.keys())
