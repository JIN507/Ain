"""
NewsData.io API Client
Centralized service layer for all NewsData.io API endpoints.
Supports: latest, crypto, archive, sources, market
"""
import os
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class NewsDataClient:
    """
    NewsData.io API Client supporting multiple endpoints.
    """
    
    BASE_URL = "https://newsdata.io/api/1"
    
    # Supported endpoints
    ENDPOINTS = {
        'latest': '/latest',
        'crypto': '/crypto',
        'archive': '/archive',
        'sources': '/sources',
        'market': '/market',  # Finance/stock news
    }
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('NEWSDATA_API_KEY', '').strip()
        
    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Make API request to NewsData.io"""
        if not self.api_key:
            return {
                'success': False,
                'error': 'مفتاح API غير موجود - يرجى إضافة NEWSDATA_API_KEY في ملف .env',
                'results': [],
                'nextPage': None
            }
        
        url = f"{self.BASE_URL}{endpoint}"
        params['apikey'] = self.api_key
        
        try:
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if response.status_code != 200 or data.get('status') != 'success':
                return {
                    'success': False,
                    'error': data.get('message', 'فشل الطلب من NewsData.io'),
                    'results': [],
                    'nextPage': None
                }
            
            return {
                'success': True,
                'results': data.get('results', []),
                'nextPage': data.get('nextPage'),
                'totalResults': data.get('totalResults', 0)
            }
            
        except requests.Timeout:
            return {
                'success': False,
                'error': 'انتهت مهلة الاتصال بـ NewsData.io',
                'results': [],
                'nextPage': None
            }
        except requests.RequestException as e:
            return {
                'success': False,
                'error': f'خطأ في الاتصال: {str(e)[:200]}',
                'results': [],
                'nextPage': None
            }
        except ValueError:
            return {
                'success': False,
                'error': 'خطأ في تحليل الاستجابة',
                'results': [],
                'nextPage': None
            }
    
    def _normalize_article(self, article: Dict, keyword: str = '', endpoint: str = 'latest') -> Dict[str, Any]:
        """Normalize article to internal format"""
        title = (article.get('title') or '').strip()
        description = (article.get('description') or article.get('content') or '').strip()
        url = article.get('link', '')
        
        if not title or not url:
            return None
        
        return {
            'id': hash(url),
            'title_ar': title,
            'title_original': title,
            'summary_ar': description,
            'summary_original': description,
            'url': url,
            'source_name': article.get('source_name') or article.get('source_id', 'Unknown'),
            'country': article.get('country'),
            'language_detected': article.get('language'),
            'published_at': article.get('pubDate'),
            'image_url': article.get('image_url'),
            'keyword_original': keyword,
            'sentiment': article.get('sentiment') or 'محايد',
            'ai_tag': article.get('ai_tag'),
            'ai_region': article.get('ai_region'),
            'ai_org': article.get('ai_org'),
            'category': article.get('category'),
            'creator': article.get('creator'),
            'video_url': article.get('video_url'),
            'source_icon': article.get('source_icon'),
            'source_priority': article.get('source_priority'),
            'created_at': datetime.now().isoformat(),
            'is_newsdata': True,
            'endpoint': endpoint
        }
    
    def build_query_string(
        self,
        must_include: List[str] = None,
        any_of: List[str] = None,
        exact_phrase: str = None,
        exclude: List[str] = None,
        raw_query: str = None
    ) -> str:
        """
        Build NewsData.io query string with AND/OR/NOT operators.
        
        Args:
            must_include: Terms that must ALL appear (joined with AND)
            any_of: Terms where ANY can appear (joined with OR, wrapped in parentheses)
            exact_phrase: Exact phrase to search (wrapped in quotes)
            exclude: Terms to exclude (prefixed with NOT)
            raw_query: Raw query string (bypasses builder if provided)
        
        Returns:
            Final query string with proper operators (uppercase AND/OR/NOT)
        """
        if raw_query:
            # Normalize operators to uppercase
            q = raw_query
            q = q.replace(' and ', ' AND ').replace(' And ', ' AND ')
            q = q.replace(' or ', ' OR ').replace(' Or ', ' OR ')
            q = q.replace(' not ', ' NOT ').replace(' Not ', ' NOT ')
            return q.strip()
        
        parts = []
        
        # Must include (AND-joined)
        if must_include:
            clean_terms = [t.strip() for t in must_include if t.strip()]
            if clean_terms:
                parts.append(' AND '.join(clean_terms))
        
        # Any of (OR-joined, parenthesized if multiple)
        if any_of:
            clean_terms = [t.strip() for t in any_of if t.strip()]
            if len(clean_terms) == 1:
                or_group = clean_terms[0]
            elif len(clean_terms) > 1:
                or_group = f"({' OR '.join(clean_terms)})"
            else:
                or_group = None
            
            if or_group:
                if parts:
                    parts.append(f"AND {or_group}")
                else:
                    parts.append(or_group)
        
        # Exact phrase (quoted)
        if exact_phrase:
            phrase = exact_phrase.strip().strip('"')
            if phrase:
                quoted = f'"{phrase}"'
                if parts:
                    parts.append(f"AND {quoted}")
                else:
                    parts.append(quoted)
        
        # Exclude terms (NOT)
        if exclude:
            clean_terms = [t.strip() for t in exclude if t.strip()]
            if clean_terms:
                if len(clean_terms) == 1:
                    not_part = f"NOT {clean_terms[0]}"
                else:
                    not_part = f"NOT ({' OR '.join(clean_terms)})"
                
                if parts:
                    parts.append(not_part)
                else:
                    # NOT alone doesn't make sense, but handle it
                    parts.append(not_part)
        
        return ' '.join(parts).strip()
    
    def search_latest(
        self,
        q: str = None,
        q_in_title: str = None,
        q_in_meta: str = None,
        country: str = None,
        exclude_country: str = None,
        language: str = None,
        exclude_language: str = None,
        category: str = None,
        exclude_category: str = None,
        domain: str = None,
        exclude_domain: str = None,
        timeframe: str = None,
        timezone: str = None,
        full_content: bool = None,
        image: bool = None,
        video: bool = None,
        remove_duplicate: bool = None,
        size: int = None,
        page: str = None,
        prioritydomain: str = None,
        sentiment: str = None,
        tag: str = None,
        region: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search latest news (past ~48 hours).
        """
        params = {}
        
        # Query params (mutually exclusive: q, qInTitle, qInMeta)
        if q:
            params['q'] = q
        elif q_in_title:
            params['qInTitle'] = q_in_title
        elif q_in_meta:
            params['qInMeta'] = q_in_meta
        
        # Filters
        if country:
            params['country'] = ','.join(country.split(',')[:5])
        if exclude_country:
            params['excludecountry'] = exclude_country
        if language:
            params['language'] = language
        if exclude_language:
            params['excludelanguage'] = exclude_language
        if category:
            params['category'] = category
        if exclude_category:
            params['excludecategory'] = exclude_category
        if domain:
            params['domain'] = domain
        if exclude_domain:
            params['excludedomain'] = exclude_domain
        if timeframe:
            params['timeframe'] = timeframe
        if timezone:
            params['timezone'] = timezone
        if prioritydomain:
            params['prioritydomain'] = prioritydomain
        
        # Boolean filters
        if full_content is True:
            params['full_content'] = '1'
        if image is True:
            params['image'] = '1'
        if video is True:
            params['video'] = '1'
        if remove_duplicate is True:
            params['removeduplicate'] = '1'
        
        # AI filters (if available in plan)
        if sentiment:
            params['sentiment'] = sentiment
        if tag:
            params['tag'] = tag
        if region:
            params['region'] = region
        
        # Pagination
        if size:
            params['size'] = min(size, 50)  # Max 50 per request
        if page:
            params['page'] = page
        
        result = self._make_request(self.ENDPOINTS['latest'], params)
        
        # Normalize results
        if result['success']:
            normalized = []
            for article in result['results']:
                norm = self._normalize_article(article, q or q_in_title or '', 'latest')
                if norm:
                    normalized.append(norm)
            result['results'] = normalized
        
        return result
    
    def search_crypto(
        self,
        q: str = None,
        coin: str = None,
        tag: str = None,
        sentiment: str = None,
        language: str = None,
        country: str = None,
        timeframe: str = None,
        full_content: bool = None,
        image: bool = None,
        page: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search crypto-related news.
        """
        params = {}
        
        if q:
            params['q'] = q
        if coin:
            params['coin'] = coin
        if tag:
            params['tag'] = tag
        if sentiment:
            params['sentiment'] = sentiment
        if language:
            params['language'] = language
        if country:
            params['country'] = ','.join(country.split(',')[:5])
        if timeframe:
            params['timeframe'] = timeframe
        if full_content is True:
            params['full_content'] = '1'
        if image is True:
            params['image'] = '1'
        if page:
            params['page'] = page
        
        result = self._make_request(self.ENDPOINTS['crypto'], params)
        
        if result['success']:
            normalized = []
            for article in result['results']:
                norm = self._normalize_article(article, q or coin or '', 'crypto')
                if norm:
                    normalized.append(norm)
            result['results'] = normalized
        
        return result
    
    def search_archive(
        self,
        q: str = None,
        q_in_title: str = None,
        from_date: str = None,
        to_date: str = None,
        country: str = None,
        language: str = None,
        category: str = None,
        domain: str = None,
        full_content: bool = None,
        image: bool = None,
        page: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search historical news archive.
        Requires: from_date (YYYY-MM-DD format)
        """
        params = {}
        
        if q:
            params['q'] = q
        elif q_in_title:
            params['qInTitle'] = q_in_title
        
        # Date range (required for archive)
        if from_date:
            params['from_date'] = from_date
        if to_date:
            params['to_date'] = to_date
        
        if country:
            params['country'] = ','.join(country.split(',')[:5])
        if language:
            params['language'] = language
        if category:
            params['category'] = category
        if domain:
            params['domain'] = domain
        if full_content is True:
            params['full_content'] = '1'
        if image is True:
            params['image'] = '1'
        if page:
            params['page'] = page
        
        result = self._make_request(self.ENDPOINTS['archive'], params)
        
        if result['success']:
            normalized = []
            for article in result['results']:
                norm = self._normalize_article(article, q or q_in_title or '', 'archive')
                if norm:
                    normalized.append(norm)
            result['results'] = normalized
        
        return result
    
    def get_sources(
        self,
        country: str = None,
        language: str = None,
        category: str = None,
        prioritydomain: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get available news sources.
        """
        params = {}
        
        if country:
            params['country'] = country
        if language:
            params['language'] = language
        if category:
            params['category'] = category
        if prioritydomain:
            params['prioritydomain'] = prioritydomain
        
        return self._make_request(self.ENDPOINTS['sources'], params)
    
    def search_market(
        self,
        q: str = None,
        symbol: str = None,
        exchange: str = None,
        sentiment: str = None,
        language: str = None,
        country: str = None,
        timeframe: str = None,
        full_content: bool = None,
        page: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Search finance/market/stock news.
        """
        params = {}
        
        if q:
            params['q'] = q
        if symbol:
            params['symbol'] = symbol
        if exchange:
            params['exchange'] = exchange
        if sentiment:
            params['sentiment'] = sentiment
        if language:
            params['language'] = language
        if country:
            params['country'] = ','.join(country.split(',')[:5])
        if timeframe:
            params['timeframe'] = timeframe
        if full_content is True:
            params['full_content'] = '1'
        if page:
            params['page'] = page
        
        result = self._make_request(self.ENDPOINTS['market'], params)
        
        if result['success']:
            normalized = []
            for article in result['results']:
                norm = self._normalize_article(article, q or symbol or '', 'market')
                if norm:
                    normalized.append(norm)
            result['results'] = normalized
        
        return result
    
    def get_count(
        self,
        q: str = None,
        q_in_title: str = None,
        q_in_meta: str = None,
        country: str = None,
        language: str = None,
        category: str = None,
        domain: str = None,
        timeframe: str = None,
        from_date: str = None,
        to_date: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Get article count without fetching full results (saves credits).
        Uses the news count API endpoint.
        """
        params = {}
        
        # Query params (mutually exclusive)
        if q:
            params['q'] = q
        elif q_in_title:
            params['qInTitle'] = q_in_title
        elif q_in_meta:
            params['qInMeta'] = q_in_meta
        
        # Filters
        if country:
            params['country'] = ','.join(country.split(',')[:5])
        if language:
            params['language'] = language
        if category:
            params['category'] = category
        if domain:
            params['domain'] = domain
        if timeframe:
            params['timeframe'] = timeframe
        if from_date:
            params['from_date'] = from_date
        if to_date:
            params['to_date'] = to_date
        
        # Use news/count endpoint
        try:
            url = f"{self.BASE_URL}/news"
            params['apikey'] = self.api_key
            params['size'] = 1  # Minimal fetch to get totalResults
            
            response = requests.get(url, params=params, timeout=10)
            data = response.json()
            
            if response.status_code == 200 and data.get('status') == 'success':
                return {
                    'success': True,
                    'count': data.get('totalResults', 0),
                    'message': None
                }
            else:
                return {
                    'success': False,
                    'count': 0,
                    'message': data.get('message', 'فشل في جلب العدد')
                }
        except Exception as e:
            return {
                'success': False,
                'count': 0,
                'message': str(e)[:200]
            }
    
    def search(self, endpoint: str = 'latest', **kwargs) -> Dict[str, Any]:
        """
        Generic search method that routes to the appropriate endpoint.
        """
        endpoint = endpoint.lower()
        
        if endpoint == 'latest':
            return self.search_latest(**kwargs)
        elif endpoint == 'crypto':
            return self.search_crypto(**kwargs)
        elif endpoint == 'archive':
            return self.search_archive(**kwargs)
        elif endpoint == 'sources':
            return self.get_sources(**kwargs)
        elif endpoint == 'market':
            return self.search_market(**kwargs)
        elif endpoint == 'count':
            return self.get_count(**kwargs)
        else:
            return {
                'success': False,
                'error': f'نقطة نهاية غير معروفة: {endpoint}',
                'results': [],
                'nextPage': None
            }


# Global client instance
newsdata_client = NewsDataClient()
