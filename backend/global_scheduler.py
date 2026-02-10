"""
Global Monitoring Scheduler for Ain News Monitor

ARCHITECTURE: Single global scheduler replaces per-user schedulers.
- ONE background thread (not per-user) fetches RSS feeds ONCE
- Matches articles against ALL users' keywords in one pass
- Distributes results to each user based on their keywords
- DB lock ensures only one Gunicorn worker runs monitoring

SCALING: O(feeds × keywords) instead of O(users × feeds × keywords)
- 40 users with 5 keywords each = 1 fetch cycle, not 40
- Memory: ~1 thread instead of ~40 threads
- DB connections: 1 session per run, not 40 concurrent sessions
"""
import threading
import time
import gc
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Set, Tuple
from utils import strip_html_tags


class GlobalMonitoringScheduler:
    """
    Single global scheduler that monitors news for ALL users at once.
    
    Flow:
    1. Wake up every N minutes
    2. Acquire global DB lock (prevents duplicate runs across Gunicorn workers)
    3. Collect ALL enabled keywords from ALL users
    4. Deduplicate keywords (many users may share keywords)
    5. Fetch RSS feeds ONCE
    6. Match articles against all keyword expansions
    7. For each match: save article to EVERY user who has that keyword
    8. Release lock, sleep, repeat
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._interval = 1800  # 30 minutes
        self._running = False
        self._executing = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._trigger_event = threading.Event()
        self._status_lock = threading.Lock()
        self._last_run: Optional[datetime] = None
        self._last_result: Optional[Dict[str, Any]] = None
        self._run_count = 0
        self._error_count = 0
    
    # ── Status ────────────────────────────────────────────────────────
    
    def get_status(self) -> Dict[str, Any]:
        """Get global scheduler status"""
        with self._status_lock:
            return {
                "running": self._running,
                "executing": self._executing,
                "interval_minutes": self._interval // 60,
                "last_run": self._last_run.isoformat() if self._last_run else None,
                "next_run": self._calculate_next_run(),
                "run_count": self._run_count,
                "error_count": self._error_count,
                "last_result": self._last_result,
            }
    
    def get_user_status(self, user_id: int) -> Dict[str, Any]:
        """
        Get monitoring status from a specific user's perspective.
        Combines global scheduler state with user's keyword state.
        """
        from models import get_db, Keyword
        
        db = get_db()
        try:
            keyword_count = db.query(Keyword).filter(
                Keyword.user_id == user_id,
                Keyword.enabled == True
            ).count()
        finally:
            db.close()
        
        status = self.get_status()
        status["user_has_keywords"] = keyword_count > 0
        status["user_keyword_count"] = keyword_count
        return status
    
    def _calculate_next_run(self) -> Optional[str]:
        if not self._running or not self._last_run:
            return None
        next_run = datetime.fromtimestamp(self._last_run.timestamp() + self._interval)
        return next_run.isoformat()
    
    # ── Lifecycle ─────────────────────────────────────────────────────
    
    def start(self) -> Dict[str, Any]:
        """Start the global monitoring scheduler"""
        with self._status_lock:
            if self._running:
                return {"success": False, "message": "Global scheduler already running"}
            self._running = True
            self._stop_event.clear()
            self._last_run = datetime.now()
        
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        print(f"[GLOBAL-SCHED] Started - monitoring every {self._interval // 60} minutes for ALL users")
        return {"success": True, "message": f"Global scheduler started (every {self._interval // 60} min)"}
    
    def stop(self) -> Dict[str, Any]:
        """Stop the global monitoring scheduler"""
        with self._status_lock:
            if not self._running:
                return {"success": False, "message": "Global scheduler not running"}
            self._running = False
            self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        
        print(f"[GLOBAL-SCHED] Stopped")
        return {"success": True, "message": "Global scheduler stopped"}
    
    def trigger_now(self) -> Dict[str, Any]:
        """Trigger an immediate monitoring run (e.g. after new keyword added).
        Also force-releases any stale DB locks so the run can actually execute."""
        with self._status_lock:
            if not self._running:
                return {"success": False, "message": "Global scheduler not running"}
        
        # Force-release any stale locks so the triggered run can proceed
        self._force_release_stale_locks()
        
        print(f"[GLOBAL-SCHED] Triggered immediate run (cleared stale locks)")
        self._trigger_event.set()
        return {"success": True, "message": "Immediate run triggered"}
    
    def _force_release_stale_locks(self):
        """Force-release any RUNNING global jobs that may be stale."""
        from models import get_db, MonitorJob
        SYSTEM_USER_ID = 0
        db = get_db()
        try:
            stale_jobs = db.query(MonitorJob).filter(
                MonitorJob.user_id == SYSTEM_USER_ID,
                MonitorJob.status == 'RUNNING'
            ).all()
            for job in stale_jobs:
                age = (datetime.utcnow() - (job.started_at or datetime.utcnow())).total_seconds()
                # Force-release if older than 2 minutes (triggered runs should be fast to start)
                if age > 120:
                    job.status = 'FAILED'
                    job.error_message = f'Force-released stale lock (age: {int(age)}s)'
                    job.finished_at = datetime.utcnow()
                    print(f"[GLOBAL-SCHED] Force-released stale job {job.id} (age: {int(age)}s)")
            db.commit()
        except Exception as e:
            print(f"[GLOBAL-SCHED] Error releasing stale locks: {e}")
            db.rollback()
        finally:
            db.close()
    
    # ── Main Loop ─────────────────────────────────────────────────────
    
    def _run_loop(self):
        """Main scheduler loop - runs monitoring then sleeps"""
        self._execute_global_monitoring()
        
        while not self._stop_event.is_set():
            self._trigger_event.clear()
            
            # Wait for interval, interruptible by stop or trigger
            for _ in range(self._interval):
                if self._stop_event.is_set():
                    return
                if self._trigger_event.is_set():
                    self._trigger_event.clear()
                    break
                time.sleep(1)
            
            if not self._running:
                break
            
            self._execute_global_monitoring()
    
    # ── DB Lock (multi-worker safe) ───────────────────────────────────
    
    def _acquire_global_lock(self, db) -> Optional[int]:
        """
        Acquire a global DB lock for monitoring.
        Uses MonitorJob with user_id=0 (system) to indicate global run.
        Returns job_id if lock acquired, None if another worker is running.
        """
        from models import MonitorJob
        
        SYSTEM_USER_ID = 0  # Sentinel for global jobs
        
        active_job = db.query(MonitorJob).filter(
            MonitorJob.user_id == SYSTEM_USER_ID,
            MonitorJob.status == 'RUNNING'
        ).first()
        
        if active_job:
            age = datetime.utcnow() - (active_job.started_at or datetime.utcnow())
            if age > timedelta(minutes=5):
                active_job.status = 'FAILED'
                active_job.error_message = 'Stale global job (worker timeout)'
                active_job.finished_at = datetime.utcnow()
                db.commit()
                print(f"[GLOBAL-SCHED] Cleaned up stale global job {active_job.id}")
            else:
                print(f"[GLOBAL-SCHED] Another worker running global job {active_job.id} - skipping")
                return None
        
        new_job = MonitorJob(
            user_id=SYSTEM_USER_ID,
            status='RUNNING',
            started_at=datetime.utcnow(),
            progress=0,
            progress_message='Starting global monitoring...'
        )
        db.add(new_job)
        db.commit()
        
        return new_job.id
    
    def _release_global_lock(self, db, job_id: int, success: bool, result: Dict[str, Any]):
        """Release the global DB lock and update job status"""
        from models import MonitorJob
        
        job = db.query(MonitorJob).filter(MonitorJob.id == job_id).first()
        if job:
            job.status = 'SUCCEEDED' if success else 'FAILED'
            job.finished_at = datetime.utcnow()
            job.progress = 100
            job.total_fetched = result.get('total_fetched', 0)
            job.total_matched = result.get('total_matches', 0)
            job.total_saved = result.get('total_saved', 0)
            if not success:
                job.error_message = result.get('error', 'Unknown error')
            db.commit()
    
    # ── Core Monitoring ───────────────────────────────────────────────
    
    def _execute_global_monitoring(self):
        """
        Execute monitoring for ALL users at once.
        
        1. Collect all unique keywords from all users
        2. Build keyword→users map
        3. Fetch RSS feeds ONCE
        4. Match against all keywords
        5. Save articles per-user
        """
        from models import get_db, Source, Keyword, Article
        from keyword_expansion import load_expansions_from_keywords
        from async_monitor_wrapper import run_optimized_monitoring
        
        self._executing = True
        job_id = None
        
        print(f"\n{'='*60}")
        print(f"[GLOBAL-SCHED] Starting global monitoring at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        db = get_db()
        try:
            # Step 1: Acquire global lock
            job_id = self._acquire_global_lock(db)
            if job_id is None:
                with self._status_lock:
                    self._last_run = datetime.now()
                    self._last_result = {"skipped": True, "reason": "Another worker running"}
                return
            
            print(f"[GLOBAL-SCHED] Acquired DB lock (job {job_id})")
            
            # Step 2: Collect ALL enabled keywords from ALL users
            all_keywords = db.query(Keyword).filter(Keyword.enabled == True).all()
            
            if not all_keywords:
                print(f"[GLOBAL-SCHED] No enabled keywords for any user - skipping")
                self._release_global_lock(db, job_id, True, {"skipped": True})
                with self._status_lock:
                    self._last_run = datetime.now()
                    self._last_result = {"skipped": True, "reason": "No keywords"}
                return
            
            # Step 3: Build keyword→users map and deduplicate
            keyword_user_map: Dict[str, Set[int]] = {}  # {keyword_ar: {user_id, ...}}
            for kw in all_keywords:
                if kw.text_ar not in keyword_user_map:
                    keyword_user_map[kw.text_ar] = set()
                keyword_user_map[kw.text_ar].add(kw.user_id)
            
            # Unique keywords for expansion loading (one per text)
            seen_texts = set()
            unique_keywords = []
            for kw in all_keywords:
                if kw.text_ar not in seen_texts:
                    seen_texts.add(kw.text_ar)
                    unique_keywords.append(kw)
            
            total_users = len(set(kw.user_id for kw in all_keywords))
            print(f"[GLOBAL-SCHED] {len(unique_keywords)} unique keywords across {total_users} users")
            for text, users in keyword_user_map.items():
                print(f"   • '{text}' → {len(users)} user(s)")
            
            # Step 4: Load keyword expansions (translations to 33 languages)
            keyword_expansions = load_expansions_from_keywords(unique_keywords)
            
            if not keyword_expansions:
                print(f"[GLOBAL-SCHED] No keyword expansions available - skipping")
                self._release_global_lock(db, job_id, True, {"skipped": True})
                with self._status_lock:
                    self._last_run = datetime.now()
                    self._last_result = {"skipped": True, "reason": "No expansions"}
                return
            
            # Step 5: Get all enabled RSS sources
            sources = db.query(Source).filter(Source.enabled == True).all()
            sources_list = [{
                'id': s.id,
                'country_name': s.country_name,
                'name': s.name,
                'url': s.url,
                'enabled': s.enabled
            } for s in sources]
            
            print(f"[GLOBAL-SCHED] Fetching from {len(sources_list)} RSS sources...")
            
            # Step 6: Fetch RSS feeds ONCE and match against ALL keywords
            monitoring_result = run_optimized_monitoring(
                sources_list,
                keyword_expansions,
                max_concurrent=50,
                max_per_source=30
            )
            
            # Step 7: Save results per-user
            total_saved = 0
            user_save_counts: Dict[int, int] = {}
            
            if monitoring_result.get('success') and monitoring_result.get('matches'):
                matches = monitoring_result['matches']
                print(f"\n[GLOBAL-SCHED] {len(matches)} matches found - distributing to users...")
                
                total_saved, user_save_counts = self._save_matches_for_all_users(
                    db, matches, keyword_user_map
                )
            
            # Step 8: Build result summary
            result = {
                "success": True,
                "total_fetched": monitoring_result.get('total_fetched', 0),
                "total_matches": len(monitoring_result.get('matches', [])),
                "total_saved": total_saved,
                "users_served": len(user_save_counts),
                "per_user_saves": {str(k): v for k, v in user_save_counts.items()},
                "timestamp": datetime.now().isoformat()
            }
            
            self._release_global_lock(db, job_id, True, result)
            
            with self._status_lock:
                self._last_run = datetime.now()
                self._run_count += 1
                self._last_result = result
            
            print(f"\n{'='*60}")
            print(f"[GLOBAL-SCHED] COMPLETED")
            print(f"   Fetched: {result['total_fetched']} articles from {len(sources_list)} sources")
            print(f"   Matched: {result['total_matches']}")
            print(f"   Saved:   {total_saved} total across {len(user_save_counts)} users")
            for uid, count in user_save_counts.items():
                print(f"      User {uid}: {count} articles")
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"[GLOBAL-SCHED] ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            if job_id:
                self._release_global_lock(db, job_id, False, error_result)
            
            with self._status_lock:
                self._error_count += 1
                self._last_run = datetime.now()
                self._last_result = error_result
        finally:
            db.close()
            self._executing = False
            gc.collect()
            print(f"[GLOBAL-SCHED] Memory cleaned (gc.collect)")
    
    # ── Multi-User Article Saving ─────────────────────────────────────
    
    def _save_matches_for_all_users(
        self,
        db,
        matches: list,
        keyword_user_map: Dict[str, Set[int]]
    ) -> Tuple[int, Dict[int, int]]:
        """
        Save matched articles to ALL users who have the matching keyword.
        
        For each match:
        1. Translate/prepare the article ONCE (expensive)
        2. Save to each user who has that keyword (cheap DB insert)
        
        Returns: (total_saved, {user_id: count})
        """
        from models import Article
        from multilingual_matcher import detect_article_language
        from translation_cache import translate_article_to_arabic
        from async_monitor_wrapper import extract_all_match_contexts, translate_snippet_preserve_keyword
        from config import get_effective_save_limit, BALANCING_STRATEGY
        
        total_saved = 0
        user_save_counts: Dict[int, int] = {}
        duplicates = 0
        
        # Apply save limit
        limit = get_effective_save_limit()
        if limit and len(matches) > limit:
            print(f"[GLOBAL-SCHED] Applying save limit: {limit} (from {len(matches)} matches)")
            matches = matches[:limit]
        
        for article, source, matched_keywords in matches:
            # ── Prepare article ONCE (expensive translation) ──────────
            detected_lang = detect_article_language(article['title'], article['summary'])
            
            translation_result = translate_article_to_arabic(
                article['title'],
                article['summary'],
                detected_lang
            )
            
            title_ar = strip_html_tags(translation_result['title_ar'])
            summary_ar = strip_html_tags(translation_result['summary_ar'])
            
            primary_keyword = matched_keywords[0]['keyword_ar']
            
            # Extract and translate match contexts
            match_contexts = extract_all_match_contexts(
                article, matched_keywords, words_before=20, words_after=20
            )
            
            for context in match_contexts:
                snippet = strip_html_tags(context.get('full_snippet', ''))
                context['full_snippet'] = snippet
                preserve_text = context.get('preserve_text', '')
                keyword_arabic = context.get('keyword_ar', '')
                
                if snippet and detected_lang != 'ar':
                    try:
                        translated_snippet = translate_snippet_preserve_keyword(
                            snippet, preserve_text, detected_lang, 'ar',
                            keyword_ar=keyword_arabic
                        )
                        context['full_snippet_ar'] = strip_html_tags(translated_snippet)
                        context['original_matched_text'] = preserve_text
                    except Exception:
                        context['full_snippet_ar'] = snippet
                else:
                    context['full_snippet_ar'] = snippet
            
            keywords_info = json.dumps({
                'primary': primary_keyword,
                'all_matched': [m['keyword_ar'] for m in matched_keywords],
                'match_details': matched_keywords,
                'match_contexts': match_contexts
            }, ensure_ascii=False)
            
            # Parse published date
            published_datetime = self._parse_published_date(article.get('published_at'))
            
            # ── Save to EACH user who has this keyword (cheap) ────────
            target_user_ids = keyword_user_map.get(primary_keyword, set())
            
            # Also check other matched keywords for additional users
            for mk in matched_keywords:
                kw_ar = mk.get('keyword_ar', '')
                if kw_ar in keyword_user_map:
                    target_user_ids = target_user_ids | keyword_user_map[kw_ar]
            
            for user_id in target_user_ids:
                # Per-user duplicate check (composite unique: url + user_id)
                exists = db.query(Article).filter(
                    Article.url == article['url'],
                    Article.user_id == user_id
                ).first()
                
                if exists:
                    duplicates += 1
                    continue
                
                new_article = Article(
                    country=source['country_name'],
                    source_name=source['name'],
                    url=article['url'],
                    title_original=strip_html_tags(article['title']),
                    summary_original=strip_html_tags(article['summary']),
                    original_language=detected_lang,
                    image_url=article.get('image_url'),
                    title_ar=title_ar,
                    summary_ar=summary_ar,
                    arabic_text=f"{title_ar} {summary_ar}",
                    keyword=primary_keyword,
                    keyword_original=primary_keyword,
                    keywords_translations=keywords_info,
                    sentiment_label="محايد",
                    sentiment_score=None,
                    published_at=published_datetime,
                    fetched_at=datetime.utcnow(),
                    user_id=user_id,
                )
                
                db.add(new_article)
                try:
                    db.commit()
                    total_saved += 1
                    user_save_counts[user_id] = user_save_counts.get(user_id, 0) + 1
                except Exception as e:
                    db.rollback()
                    print(f"[GLOBAL-SCHED] ⚠️ Save error for user {user_id}: {str(e)[:80]}")
        
        print(f"[GLOBAL-SCHED] Saved {total_saved} articles, skipped {duplicates} duplicates")
        return total_saved, user_save_counts
    
    @staticmethod
    def _parse_published_date(date_val) -> Optional[datetime]:
        """Parse published date from various formats"""
        if not date_val:
            return None
        if isinstance(date_val, datetime):
            return date_val
        if isinstance(date_val, str):
            for fmt in ('%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                try:
                    return datetime.strptime(date_val[:19], fmt)
                except (ValueError, IndexError):
                    continue
            # Try ISO format
            try:
                return datetime.fromisoformat(date_val.replace('Z', '+00:00').replace('+00:00', ''))
            except Exception:
                pass
        return None


# Global singleton instance
global_scheduler = GlobalMonitoringScheduler()
