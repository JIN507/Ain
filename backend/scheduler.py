"""
Background Scheduler for Ain News Monitor
Runs monitoring every 10 minutes when activated
Per-user monitoring: each user has their own scheduler

Multi-worker safe: Uses DB locks to prevent duplicate runs across Gunicorn workers.
Memory-optimized: Forces garbage collection after each run to stay under 512MB.
"""
import threading
import time
import gc
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json

class UserMonitoringScheduler:
    """
    Per-user scheduler that runs monitoring at regular intervals.
    Each user has their own independent scheduler.
    """
    def __init__(self, user_id: int):
        self.user_id = user_id
        self._interval = 3600  # 60 minutes (1 hour) in seconds
        self._running = False
        self._executing = False  # True while monitoring is actively running
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._trigger_event = threading.Event()  # For triggering immediate run
        self._status_lock = threading.Lock()
        self._last_run: Optional[datetime] = None
        self._last_result: Optional[Dict[str, Any]] = None
        self._run_count = 0
        self._error_count = 0
        
    @property
    def is_running(self) -> bool:
        with self._status_lock:
            return self._running
    
    @property
    def interval_minutes(self) -> int:
        return self._interval // 60
    
    @interval_minutes.setter
    def interval_minutes(self, value: int):
        self._interval = max(1, value) * 60
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status"""
        with self._status_lock:
            return {
                "running": self._running,
                "executing": self._executing,  # True only when actively fetching news
                "interval_minutes": self._interval // 60,
                "last_run": self._last_run.isoformat() if self._last_run else None,
                "next_run": self._calculate_next_run(),
                "run_count": self._run_count,
                "error_count": self._error_count,
                "last_result": self._last_result
            }
    
    def _calculate_next_run(self) -> Optional[str]:
        if not self._running or not self._last_run:
            return None
        next_run = datetime.fromtimestamp(self._last_run.timestamp() + self._interval)
        return next_run.isoformat()
    
    def start(self) -> Dict[str, Any]:
        """Start the monitoring scheduler"""
        with self._status_lock:
            if self._running:
                return {"success": False, "message": "Scheduler already running"}
            
            self._running = True
            self._stop_event.clear()
            # Set last_run to now so next_run can be calculated immediately
            self._last_run = datetime.now()
        
        # Start background thread
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        print(f"[SCHEDULER] Started - will run every {self._interval // 60} minutes")
        return {"success": True, "message": f"Scheduler started (every {self._interval // 60} minutes)"}
    
    def stop(self, wait_for_completion: bool = True, cancel_jobs: bool = False) -> Dict[str, Any]:
        """Stop the monitoring scheduler and optionally wait for current operation
        
        Args:
            wait_for_completion: If True, wait for current monitoring to finish
            cancel_jobs: If True, mark all RUNNING jobs as CANCELLED (use when restarting)
        """
        with self._status_lock:
            if not self._running:
                return {"success": False, "message": "Scheduler not running"}
            
            self._running = False
            self._stop_event.set()
        
        # Cancel DB jobs if requested (when restarting with new keywords)
        if cancel_jobs:
            self._cancel_running_jobs()
        
        # Wait for current monitoring to complete if requested
        if wait_for_completion and not cancel_jobs:
            print(f"[SCHEDULER] User {self.user_id}: Waiting for current monitoring to complete...")
            wait_count = 0
            while self._executing and wait_count < 120:  # Max 2 minutes wait
                time.sleep(1)
                wait_count += 1
            if self._executing:
                print(f"[SCHEDULER] User {self.user_id}: Timeout waiting for monitoring to complete")
        
        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        print(f"[SCHEDULER] User {self.user_id}: Stopped")
        return {"success": True, "message": "Scheduler stopped"}
    
    def _cancel_running_jobs(self):
        """Cancel all RUNNING jobs for this user in DB (used when restarting with new keywords)"""
        from models import get_db, MonitorJob
        
        db = get_db()
        try:
            running_jobs = db.query(MonitorJob).filter(
                MonitorJob.user_id == self.user_id,
                MonitorJob.status == 'RUNNING'
            ).all()
            
            for job in running_jobs:
                job.status = 'CANCELLED'
                job.finished_at = datetime.utcnow()
                job.error_message = 'Cancelled: New keyword added, restarting monitoring'
                print(f"[SCHEDULER] User {self.user_id}: Cancelled job {job.id} for restart")
            
            db.commit()
        finally:
            db.close()
    
    def trigger_now(self) -> Dict[str, Any]:
        """Trigger an immediate monitoring run (used when new keyword added)"""
        with self._status_lock:
            if not self._running:
                return {"success": False, "message": "Scheduler not running"}
        
        print(f"[SCHEDULER] User {self.user_id}: Triggered immediate run (new keyword added)")
        self._trigger_event.set()
        return {"success": True, "message": "Immediate run triggered"}
    
    def _share_results_with_matching_users(self, db, source_user_id: int) -> int:
        """
        Share monitoring results with other users who have the same keywords.
        This reduces server load by avoiding duplicate fetching.
        Returns total articles shared.
        """
        from models import Keyword, Article
        
        # Get this user's keywords
        my_keywords = db.query(Keyword).filter(
            Keyword.user_id == source_user_id,
            Keyword.enabled == True
        ).all()
        
        if not my_keywords:
            return 0
        
        my_keyword_texts = [k.text_ar for k in my_keywords]
        
        # Find other users with matching keywords
        other_keywords = db.query(Keyword).filter(
            Keyword.text_ar.in_(my_keyword_texts),
            Keyword.user_id != source_user_id,
            Keyword.enabled == True
        ).all()
        
        if not other_keywords:
            return 0
        
        # Group by user and their matching keywords
        user_keywords = {}
        for k in other_keywords:
            if k.user_id not in user_keywords:
                user_keywords[k.user_id] = set()
            user_keywords[k.user_id].add(k.text_ar)
        
        total_shared = 0
        
        # For each user with matching keywords, copy new articles
        for target_user_id, matching_keywords in user_keywords.items():
            # Get articles from source user for matching keywords (last 24 hours)
            from datetime import timedelta
            cutoff = datetime.now() - timedelta(hours=24)
            
            source_articles = db.query(Article).filter(
                Article.user_id == source_user_id,
                Article.keyword.in_(matching_keywords),
                Article.fetched_at >= cutoff
            ).all()
            
            if not source_articles:
                continue
            
            # Get existing URLs for target user to avoid duplicates
            existing_urls = set(
                a.url for a in db.query(Article).filter(
                    Article.user_id == target_user_id
                ).all()
            )
            
            # Copy new articles
            for article in source_articles:
                if article.url in existing_urls:
                    continue
                
                new_article = Article(
                    country=article.country,
                    source_name=article.source_name,
                    url=article.url,
                    title_original=article.title_original,
                    summary_original=article.summary_original,
                    original_language=article.original_language,
                    image_url=article.image_url,
                    title_ar=article.title_ar,
                    summary_ar=article.summary_ar,
                    arabic_text=article.arabic_text,
                    keyword=article.keyword,
                    keyword_original=article.keyword_original,
                    keywords_translations=article.keywords_translations,
                    sentiment_label=article.sentiment_label,
                    sentiment_score=article.sentiment_score,
                    published_at=article.published_at,
                    fetched_at=article.fetched_at,
                    user_id=target_user_id
                )
                db.add(new_article)
                existing_urls.add(article.url)
                total_shared += 1
        
        if total_shared > 0:
            db.commit()
        
        return total_shared
    
    def _run_loop(self):
        """Main scheduler loop"""
        # Run immediately on start
        self._execute_monitoring()
        
        while not self._stop_event.is_set():
            # Wait for interval, stop event, or trigger event
            self._trigger_event.clear()
            
            # Wait with ability to be interrupted by trigger
            for _ in range(self._interval):
                if self._stop_event.is_set():
                    return
                if self._trigger_event.is_set():
                    self._trigger_event.clear()
                    break
                time.sleep(1)
            
            # Check if still running (could have been stopped)
            if not self._running:
                break
                
            # Execute monitoring
            self._execute_monitoring()
    
    def _acquire_db_lock(self, db) -> Optional[int]:
        """
        Try to acquire a DB-based lock for this user's monitoring run.
        Returns job_id if lock acquired, None if another worker is already running.
        
        This prevents duplicate runs across multiple Gunicorn workers.
        """
        from models import MonitorJob
        
        # Check if there's already a RUNNING job for this user (from any worker)
        active_job = db.query(MonitorJob).filter(
            MonitorJob.user_id == self.user_id,
            MonitorJob.status == 'RUNNING'
        ).first()
        
        if active_job:
            # Check if it's stale (running for more than 10 minutes = likely crashed worker)
            if active_job.started_at:
                age = datetime.utcnow() - active_job.started_at
                if age > timedelta(minutes=10):
                    # Mark stale job as failed and proceed
                    active_job.status = 'FAILED'
                    active_job.error_message = 'Stale job (worker timeout)'
                    active_job.finished_at = datetime.utcnow()
                    db.commit()
                    print(f"[SCHEDULER] User {self.user_id}: Cleaned up stale job {active_job.id}")
                else:
                    # Another worker is actively running - skip this run
                    print(f"[SCHEDULER] User {self.user_id}: Another worker running job {active_job.id} - skipping")
                    return None
        
        # Create new job record to claim the lock
        new_job = MonitorJob(
            user_id=self.user_id,
            status='RUNNING',
            started_at=datetime.utcnow(),
            progress=0,
            progress_message='Starting monitoring...'
        )
        db.add(new_job)
        db.commit()
        
        return new_job.id
    
    def _release_db_lock(self, db, job_id: int, success: bool, result: Dict[str, Any]):
        """Release the DB lock and update job status"""
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
    
    def _execute_monitoring(self):
        """Execute a single monitoring run for this specific user"""
        from models import get_db, Source, Keyword, Article
        from keyword_expansion import load_expansions_from_keywords
        from async_monitor_wrapper import run_optimized_monitoring, save_matched_articles_sync
        
        # Mark as executing
        self._executing = True
        job_id = None
        
        print(f"\n[SCHEDULER] User {self.user_id}: Starting monitoring at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        db = get_db()
        try:
            # MULTI-WORKER SAFETY: Acquire DB lock before running
            job_id = self._acquire_db_lock(db)
            if job_id is None:
                # Another worker is already running for this user - skip
                with self._status_lock:
                    self._last_run = datetime.now()
                    self._last_result = {"skipped": True, "reason": "Another worker running"}
                return
            
            print(f"[SCHEDULER] User {self.user_id}: Acquired DB lock (job {job_id})")
            
            # Get ALL enabled sources (shared across users)
            sources = db.query(Source).filter(Source.enabled == True).all()
            
            # Get ONLY this user's enabled keywords
            keywords = db.query(Keyword).filter(
                Keyword.enabled == True,
                Keyword.user_id == self.user_id
            ).all()
            
            if not sources or not keywords:
                print(f"[SCHEDULER] User {self.user_id}: No enabled sources or keywords - skipping")
                self._release_db_lock(db, job_id, True, {"skipped": True})
                with self._status_lock:
                    self._last_run = datetime.now()
                    self._last_result = {"skipped": True, "reason": "No sources or keywords"}
                return
            
            # Convert to dicts
            sources_list = [{
                'id': s.id,
                'country_name': s.country_name,
                'name': s.name,
                'url': s.url,
                'enabled': s.enabled
            } for s in sources]
            
            # Load cached keyword expansions for this user's keywords only
            keyword_expansions = load_expansions_from_keywords(keywords)
            
            if not keyword_expansions:
                print(f"[SCHEDULER] User {self.user_id}: No keyword expansions - skipping")
                self._release_db_lock(db, job_id, True, {"skipped": True})
                with self._status_lock:
                    self._last_run = datetime.now()
                    self._last_result = {"skipped": True, "reason": "No keyword expansions"}
                return
            
            # Run monitoring
            monitoring_result = run_optimized_monitoring(
                sources_list,
                keyword_expansions,
                max_concurrent=50,
                max_per_source=30
            )
            
            # Save results with this user's ID
            saved_count = 0
            if monitoring_result.get('success') and monitoring_result.get('matches'):
                matches = monitoring_result['matches']
                saved_ids, save_stats = save_matched_articles_sync(
                    db,
                    matches,
                    apply_limit=True,
                    user_id=self.user_id  # Save with user's ID for personal data
                )
                saved_count = len(saved_ids)
            
            # Share results with other users who have the same keywords
            shared_count = self._share_results_with_matching_users(db, self.user_id)
            if shared_count > 0:
                print(f"[SCHEDULER] User {self.user_id}: Shared {shared_count} articles with other users")
            
            result = {
                "success": True,
                "total_fetched": monitoring_result.get('total_fetched', 0),
                "total_matches": len(monitoring_result.get('matches', [])),
                "total_saved": saved_count,
                "shared_with_others": shared_count,
                "timestamp": datetime.now().isoformat()
            }
            
            # Release DB lock with success
            if job_id:
                self._release_db_lock(db, job_id, True, result)
            
            with self._status_lock:
                self._last_run = datetime.now()
                self._run_count += 1
                self._last_result = result
            
            print(f"[SCHEDULER] User {self.user_id}: Completed - fetched: {monitoring_result.get('total_fetched', 0)}, saved: {saved_count}")
            
        except Exception as e:
            print(f"[SCHEDULER] User {self.user_id}: Error: {str(e)}")
            import traceback
            traceback.print_exc()
            
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            
            # Release DB lock with failure
            if job_id:
                self._release_db_lock(db, job_id, False, error_result)
            
            with self._status_lock:
                self._error_count += 1
                self._last_run = datetime.now()
                self._last_result = error_result
        finally:
            db.close()
            # Mark as not executing
            self._executing = False
            # MEMORY CLEANUP: Force garbage collection after each run
            gc.collect()
            print(f"[SCHEDULER] User {self.user_id}: Memory cleaned (gc.collect)")


class SchedulerManager:
    """
    Manages per-user schedulers.
    Thread-safe singleton that creates/retrieves schedulers for each user.
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
        self._schedulers: Dict[int, UserMonitoringScheduler] = {}
        self._schedulers_lock = threading.Lock()
    
    def get_scheduler(self, user_id: int) -> UserMonitoringScheduler:
        """Get or create a scheduler for a specific user"""
        with self._schedulers_lock:
            if user_id not in self._schedulers:
                self._schedulers[user_id] = UserMonitoringScheduler(user_id)
            return self._schedulers[user_id]
    
    def get_status(self, user_id: int) -> Dict[str, Any]:
        """Get status for a specific user's scheduler"""
        return self.get_scheduler(user_id).get_status()
    
    def start(self, user_id: int) -> Dict[str, Any]:
        """Start monitoring for a specific user"""
        return self.get_scheduler(user_id).start()
    
    def stop(self, user_id: int, wait_for_completion: bool = True, cancel_jobs: bool = False) -> Dict[str, Any]:
        """Stop monitoring for a specific user"""
        return self.get_scheduler(user_id).stop(wait_for_completion=wait_for_completion, cancel_jobs=cancel_jobs)
    
    def trigger_now(self, user_id: int) -> Dict[str, Any]:
        """Trigger immediate monitoring run for a specific user"""
        return self.get_scheduler(user_id).trigger_now()
    
    def get_all_running(self) -> Dict[int, Dict[str, Any]]:
        """Get status of all running schedulers (for admin)"""
        with self._schedulers_lock:
            return {
                user_id: sched.get_status()
                for user_id, sched in self._schedulers.items()
                if sched.is_running
            }


# Global scheduler manager instance
scheduler_manager = SchedulerManager()
