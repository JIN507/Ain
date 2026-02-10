"""
Utility functions for Ain News Monitor
"""
import re
from datetime import datetime
from bs4 import BeautifulSoup

def strip_html_tags(text):
    """Simple regex-based HTML tag stripper - removes ALL HTML tags.
    Use as a fast safety net after clean_html_content or on any text
    that might still contain stray HTML."""
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', ' ', str(text))
    text = re.sub(r'&nbsp;|&amp;|&lt;|&gt;|&quot;|&#\d+;', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def clean_html_content(html_text):
    """
    Clean HTML content from RSS feeds - remove navigation, ads, social links, etc.
    Keep only the actual article text.
    
    Args:
        html_text: Raw HTML string from RSS feed
    
    Returns:
        str: Cleaned plain text (article content only)
    """
    if not html_text:
        return ""
    
    # Check if input looks like a URL or filename (not HTML content)
    # This prevents BeautifulSoup warnings about markup resembling locators
    html_str = str(html_text).strip()
    
    # If it looks like a URL or path, return empty (it's not HTML content)
    if (html_str.startswith(('http://', 'https://', 'file://', '/', 'C:\\', 'D:\\')) or
        ('.' in html_str and len(html_str) < 100 and not '<' in html_str)):
        # This is likely a URL or filename, not HTML content
        return ""
    
    # If there's no HTML tags, return as-is (plain text)
    if '<' not in html_str:
        return html_str
    
    # Parse HTML (suppress warnings by using try-except)
    try:
        soup = BeautifulSoup(html_text, 'html.parser')
    except Exception as e:
        # If parsing fails, return empty string
        return ""
    
    # Remove unwanted elements
    unwanted_tags = [
        'script', 'style', 'nav', 'header', 'footer', 'aside',
        'iframe', 'form', 'button', 'input', 'select', 'textarea'
    ]
    
    for tag in unwanted_tags:
        for element in soup.find_all(tag):
            element.decompose()
    
    # Remove elements with unwanted classes/ids (common patterns)
    unwanted_patterns = [
        'ad', 'advertisement', 'promo', 'sponsor', 'related', 'sidebar',
        'social', 'share', 'comment', 'footer', 'header', 'nav', 'menu',
        'newsletter', 'subscription', 'signup', 'login', 'register',
        'cookie', 'popup', 'modal', 'banner'
    ]
    
    # Remove elements by class (with safe error handling)
    for element in soup.find_all(True):  # Find all elements
        try:
            if hasattr(element, 'attrs') and element.attrs:
                # Check class attribute
                element_classes = element.attrs.get('class', [])
                if element_classes:
                    classes = ' '.join(element_classes).lower()
                    if any(pattern in classes for pattern in unwanted_patterns):
                        element.decompose()
                        continue
                
                # Check id attribute
                elem_id = element.attrs.get('id', '')
                if elem_id:
                    elem_id = elem_id.lower()
                    if any(pattern in elem_id for pattern in unwanted_patterns):
                        element.decompose()
        except (AttributeError, TypeError, KeyError):
            # Skip elements that cause issues
            continue
    
    # Remove links that look like navigation/boilerplate (with safe error handling)
    for link in soup.find_all('a'):
        try:
            href = link.get('href', '') if hasattr(link, 'get') else ''
            href = href.lower() if href else ''
            text = link.get_text() if hasattr(link, 'get_text') else ''
            text = text.lower() if text else ''
            
            # Remove common navigation/boilerplate links
            boilerplate_keywords = [
                'subscribe', 'newsletter', 'donate', 'support', 'follow',
                'facebook', 'twitter', 'instagram', 'linkedin', 'youtube',
                'bluesky', 'ad-choice', 'privacy', 'terms', 'contact',
                'fundjournalism', 'revealnews.org', 'dovetail.prx.org'
            ]
            
            if any(keyword in href for keyword in boilerplate_keywords):
                link.decompose()
            elif any(keyword in text for keyword in boilerplate_keywords):
                link.decompose()
        except (AttributeError, TypeError):
            continue
    
    # Remove lists (ul/ol) that are likely navigation/links (with safe error handling)
    for list_elem in soup.find_all(['ul', 'ol']):
        try:
            # If list has mostly links, it's likely navigation
            links = list_elem.find_all('a')
            items = list_elem.find_all('li')
            
            if items and len(items) > 0 and len(links) / len(items) > 0.5:  # More than 50% links
                list_elem.decompose()
        except (AttributeError, TypeError, ZeroDivisionError):
            continue
    
    # Extract text from remaining paragraphs (with safe error handling)
    paragraphs = []
    for p in soup.find_all('p'):
        try:
            text = p.get_text(separator=' ', strip=True) if hasattr(p, 'get_text') else ''
            
            # Skip very short paragraphs (likely not article content)
            if not text or len(text) < 20:
                continue
            
            # Skip paragraphs with common boilerplate patterns
            boilerplate_phrases = [
                'تعرف على خياراتك الإعلانية',
                'know your advertising options',
                'اشترك في نشرتنا',
                'subscribe to our newsletter',
                'تابعنا على',
                'follow us on',
                'جميع الحقوق محفوظة',
                'all rights reserved',
                'للمزيد من',
                'for more',
                'اقرأ أيضاً',
                'read also',
                'المزيد من الأخبار',
                'more news'
            ]
            
            text_lower = text.lower()
            if any(phrase in text_lower for phrase in boilerplate_phrases):
                continue
            
            paragraphs.append(text)
        except (AttributeError, TypeError):
            continue
    
    # If we got paragraphs, join them
    if paragraphs:
        # Limit to reasonable length (avoid extracting entire page)
        result = ' '.join(paragraphs[:10])  # Max 10 paragraphs
    else:
        # Fallback: get all text (last resort)
        try:
            result = soup.get_text(separator=' ', strip=True) if hasattr(soup, 'get_text') else ''
        except (AttributeError, TypeError):
            result = ''
    
    # Clean up whitespace
    result = re.sub(r'\s+', ' ', result)
    result = result.strip()
    
    # Limit length (500 chars for summary)
    if len(result) > 500:
        result = result[:497] + '...'
    
    return result

def normalize_arabic(text):
    """
    Normalize Arabic text for consistent matching
    - Normalize alef variants: أ إ آ ٱ → ا
    - Normalize ta marbuta/ha: ة → ه
    - Normalize ya: ى → ي
    - Remove diacritics
    """
    if not text:
        return ""
    
    # Remove diacritics
    text = re.sub(r'[\u064B-\u065F\u0670]', '', text)
    
    # Normalize alef
    text = re.sub(r'[أإآٱ]', 'ا', text)
    
    # Normalize ta marbuta
    text = re.sub(r'ة', 'ه', text)
    
    # Normalize alef maksura
    text = re.sub(r'ى', 'ي', text)
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    return text.lower()

def keyword_matches(text, keyword, translations=None):
    """
    Check if keyword (or its translations) exists in text
    
    Args:
        text: Text to search in
        keyword: Arabic keyword
        translations: Dict of {lang: translation_text}
    
    Returns:
        bool: True if match found
    """
    if not text or not keyword:
        return False
    
    text_norm = normalize_arabic(text).lower()
    keyword_norm = normalize_arabic(keyword).lower()
    
    # Check Arabic keyword
    if keyword_norm in text_norm:
        return True
    
    # Check translations
    if translations:
        for lang, trans in translations.items():
            if trans and trans.lower() in text.lower():
                return True
    
    return False

def parse_datetime(date_str):
    """
    Parse various datetime formats from RSS feeds
    """
    if not date_str:
        return None
    
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except:
            continue
    
    return None

def is_valid_url(url):
    """Check if URL is valid"""
    if not url:
        return False
    return url.startswith('http://') or url.startswith('https://')


# ==================== HTML TEXT EXTRACTION (with URL/Path Detection) ====================

def looks_like_url_or_path(text: str) -> bool:
    """
    Detect if a string looks like a URL, file path, or filename.
    
    This helps avoid passing URLs/paths to BeautifulSoup, which triggers
    MarkupResemblesLocatorWarning.
    
    Args:
        text: String to check
        
    Returns:
        True if it looks like URL/path/filename, False otherwise
        
    Examples:
        >>> looks_like_url_or_path("https://example.com")
        True
        >>> looks_like_url_or_path("C:\\Users\\file.html")
        True
        >>> looks_like_url_or_path("<p>Hello world</p>")
        False
    """
    if not text:
        return False
    
    text = text.strip()
    
    # Check for URL schemes
    url_schemes = (
        'http://', 'https://', 'ftp://', 'ftps://',
        'file://', 'data:', 'mailto:', 'tel:'
    )
    if text.startswith(url_schemes):
        return True
    
    # Check for absolute paths (Unix/Linux/Mac)
    if text.startswith('/'):
        # Could be path like /var/www/file.html
        # But also could be HTML like "</div>" - check for HTML closing tag
        if text.startswith('</') and '>' in text:
            return False  # It's an HTML closing tag
        return True
    
    # Check for Windows absolute paths
    # C:\, D:\, etc.
    if re.match(r'^[A-Za-z]:\\', text):
        return True
    
    # Check for relative Windows paths
    if '\\' in text and len(text) < 200:
        # Likely a Windows path like "folder\file.html"
        return True
    
    # Check for short filename-like strings (no spaces, has extension)
    # e.g., "index.html", "page.htm", "style.css"
    if (len(text) < 100 and 
        ' ' not in text and 
        '.' in text and
        not text.startswith('<')):
        # Check for common file extensions
        common_extensions = (
            '.html', '.htm', '.xml', '.php', '.asp', '.jsp',
            '.css', '.js', '.json', '.txt', '.md', '.pdf',
            '.png', '.jpg', '.jpeg', '.gif', '.svg'
        )
        if any(text.lower().endswith(ext) for ext in common_extensions):
            return True
    
    return False


def looks_like_html_markup(text: str) -> bool:
    """
    Detect if a string contains HTML markup.
    
    Args:
        text: String to check
        
    Returns:
        True if it looks like HTML, False otherwise
        
    Examples:
        >>> looks_like_html_markup("<p>Hello</p>")
        True
        >>> looks_like_html_markup("Just plain text")
        False
        >>> looks_like_html_markup("<div class='test'>Content</div>")
        True
    """
    if not text:
        return False
    
    text = text.strip()
    
    # Must contain at least one '<' and one '>'
    if '<' not in text or '>' not in text:
        return False
    
    # Check for common HTML patterns
    # Opening tags: <tag>, <tag attr="value">
    # Closing tags: </tag>
    # Self-closing: <tag />
    html_patterns = [
        r'<\w+[^>]*>',           # Opening tag: <div>, <p class="test">
        r'</\w+>',                # Closing tag: </div>, </p>
        r'<\w+[^>]*/\s*>',       # Self-closing: <br />, <img />
        r'<!\s*DOCTYPE',          # DOCTYPE declaration
        r'<!--.*?-->',            # HTML comments
    ]
    
    for pattern in html_patterns:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            return True
    
    return False


def extract_text_from_html(html_str: str) -> str:
    """
    Extract plain text from HTML string, with robust handling of non-HTML input.
    
    This function:
    1. Returns empty string for None/empty input
    2. Returns empty string for URLs, paths, or filenames (avoids BeautifulSoup warning)
    3. Returns input as-is for plain text (no HTML markup)
    4. Parses and extracts text from actual HTML markup
    
    Args:
        html_str: Input string (may be HTML, plain text, URL, or path)
        
    Returns:
        Extracted plain text, or empty string if input is URL/path
        
    Examples:
        >>> extract_text_from_html(None)
        ''
        >>> extract_text_from_html("https://example.com")
        ''
        >>> extract_text_from_html("Just plain text")
        'Just plain text'
        >>> extract_text_from_html("<p>Hello <b>world</b>!</p>")
        'Hello world!'
    """
    # Handle None or empty
    if not html_str:
        return ""
    
    # Convert to string if needed
    text = str(html_str).strip()
    
    if not text:
        return ""
    
    # Check if it's a URL, path, or filename
    # DO NOT parse these with BeautifulSoup!
    if looks_like_url_or_path(text):
        return ""
    
    # Check if it contains HTML markup
    if not looks_like_html_markup(text):
        # It's plain text - return as-is
        return text
    
    # It looks like HTML - parse it with BeautifulSoup
    # Suppress MarkupResemblesLocatorWarning
    import warnings
    from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
    
    try:
        with warnings.catch_warnings():
            # Suppress the specific warning
            warnings.filterwarnings('ignore', category=MarkupResemblesLocatorWarning)
            
            # Parse HTML
            soup = BeautifulSoup(text, 'html.parser')
            
            # Extract text using stripped_strings (removes extra whitespace)
            # Join with space to separate text from different elements
            extracted = ' '.join(soup.stripped_strings)
            
            # Clean up multiple spaces
            extracted = re.sub(r'\s+', ' ', extracted)
            
            return extracted.strip()
            
    except Exception as e:
        # If parsing fails for any reason, return empty string
        # (Better safe than crashing)
        return ""
