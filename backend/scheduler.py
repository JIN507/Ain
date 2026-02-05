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
    
    def stop(self, wait_for_completion: bool = True) -> Dict[str, Any]:
        """Stop the monitoring scheduler and optionally wait for current operation"""
        with self._status_lock:
            if not self._running:
                return {"success": False, "message": "Scheduler not running"}
            
            self._running = False
            self._stop_event.set()
        
        # Wait for current monitoring to complete if requested
        if wait_for_completion:
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
    
    def trigger_now(self) -> Dict[str, Any]:
        """Trigger an immediate monitoring run (used when new keyword added)"""
        with self._status_lock:
            if not self._running:
                return {"success": False, "message": "Scheduler not running"}
        
        print(f"[SCHEDULER] User {self.user_id}: Triggered immediate run (new keyword added)")
        self._trigger_event.set()
        return {"success": True, "message": "Immediate run triggered"}
    
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
            
            result = {
                "success": True,
                "total_fetched": monitoring_result.get('total_fetched', 0),
                "total_matches": len(monitoring_result.get('matches', [])),
                "total_saved": saved_count,
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
    
    def stop(self, user_id: int) -> Dict[str, Any]:
        """Stop monitoring for a specific user"""
        return self.get_scheduler(user_id).stop()
    
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
