"""
Arabic text normalization utilities
Normalizes Arabic text for better matching across different spellings
"""
import re

def normalize_arabic(text):
    """
    Normalize Arabic text by:
    1. Converting أ/إ/آ → ا
    2. Converting ى → ي
    3. Converting ة → ه
    4. Removing diacritics (harakat)
    5. Removing tanween (double diacritics)
    6. Removing tatweel/kashida
    
    Args:
        text: Arabic text to normalize
        
    Returns:
        Normalized text
    """
    if not text:
        return text
    
    # Convert various forms of alef to simple alef
    text = re.sub('[أإآ]', 'ا', text)
    
    # Convert alef maksura to yaa
    text = re.sub('ى', 'ي', text)
    
    # Convert taa marbuta to haa
    text = re.sub('ة', 'ه', text)
    
    # Remove Arabic diacritics (harakat) - \u064B-\u065F
    text = re.sub('[\u064B-\u065F]', '', text)
    
    # Remove tatweel (kashida) - \u0640
    text = re.sub('\u0640', '', text)
    
    # Remove tanween (double diacritics for nunation)
    text = re.sub('[\u064B-\u064D]', '', text)
    
    return text.strip()


def is_persian_text(text):
    """
    Check if text contains Persian-specific characters
    
    Persian uses unique characters not found in Arabic:
    - پ (pe) - U+067E
    - چ (che) - U+0686  
    - ژ (zhe) - U+0698
    - گ (gaf) - U+06AF
    
    Args:
        text: Text to check
        
    Returns:
        True if text has Persian-specific characters
    """
    if not text:
        return False
    
    # Check for Persian-specific characters
    persian_specific_chars = re.findall('[پچژگ]', text)
    
    # If we find any Persian-specific characters, it's Persian
    return len(persian_specific_chars) > 0


def is_arabic_text(text):
    """
    Check if text contains significant Arabic content
    
    NOTE: This excludes Persian text (which uses similar Unicode range but has unique characters)
    
    Args:
        text: Text to check
        
    Returns:
        True if text has Arabic characters (and is NOT Persian)
    """
    if not text:
        return False
    
    # First check if it's Persian
    if is_persian_text(text):
        return False  # Persian is NOT Arabic
    
    # Count Arabic characters (Unicode range: \u0600-\u06FF)
    arabic_chars = len(re.findall('[\u0600-\u06FF]', text))
    total_chars = len(re.sub(r'\s', '', text))  # Exclude whitespace
    
    if total_chars == 0:
        return False
    
    # If more than 30% of characters are Arabic, consider it Arabic text
    return (arabic_chars / total_chars) > 0.3


def build_arabic_pattern(keyword_normalized):
    """
    Build an Arabic-aware regex pattern that handles:
    - Common clitics/prefixes: و ف ب ل ك
    - Definite article: ال
    - Word boundaries without \\b
    
    Args:
        keyword_normalized: Normalized Arabic keyword
        
    Returns:
        Compiled regex pattern
    
    Example:
        For "مصر" → matches: "مصر", "ومصر", "بمصر", "المصر", "والمصر", etc.
    """
    if not keyword_normalized:
        return None
    
    # Escape the keyword for regex
    escaped_keyword = re.escape(keyword_normalized)
    
    # Pattern components:
    # 1. Negative lookbehind: not preceded by Arabic letter
    # 2. Optional single-char clitic: و ف ب ل ك
    # 3. Optional definite article: ال
    # 4. The keyword itself
    # 5. Negative lookahead: not followed by Arabic letter (allows for exact match)
    
    # Arabic letter range: \u0621-\u064A (covers most Arabic letters)
    pattern = (
        r'(?<![\u0621-\u064A])'    # Not preceded by Arabic letter
        r'(?:[وفبلك])?'             # Optional clitic (single char)
        r'(?:ال)?'                  # Optional definite article
        + escaped_keyword            # The keyword
        + r'(?![\u0621-\u064A])'    # Not followed by Arabic letter
    )
    
    return re.compile(pattern, re.IGNORECASE)


def extract_text_for_matching(text):
    """
    Extract clean text for matching (remove HTML, extra whitespace)
    
    Args:
        text: Raw text (may contain HTML)
        
    Returns:
        Clean text
    """
    if not text:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


# Test the normalization
if __name__ == "__main__":
    test_cases = [
        "الرياض",
        "أمريكا",
        "إيران",
        "آسيا",
        "السعودية",
        "مصر",
        "الإمارات"
    ]
    
    print("Arabic Normalization Test")
    print("=" * 60)
    for text in test_cases:
        normalized = normalize_arabic(text)
        print(f"{text:15} → {normalized:15} {'(changed)' if text != normalized else ''}")
