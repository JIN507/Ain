"""
Background Scheduler for Ain News Monitor
Runs monitoring every 10 minutes when activated
Per-user monitoring: each user has their own scheduler
"""
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any
import json

class UserMonitoringScheduler:
    """
    Per-user scheduler that runs monitoring at regular intervals.
    Each user has their own independent scheduler.
    """
    def __init__(self, user_id: int):
        self.user_id = user_id
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._interval = 3600  # 60 minutes (1 hour) in seconds
        self._last_run: Optional[datetime] = None
        self._last_result: Optional[Dict[str, Any]] = None
        self._run_count = 0
        self._error_count = 0
        self._stop_event = threading.Event()
        self._status_lock = threading.Lock()
        
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
        
        # Start background thread
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        
        print(f"[SCHEDULER] Started - will run every {self._interval // 60} minutes")
        return {"success": True, "message": f"Scheduler started (every {self._interval // 60} minutes)"}
    
    def stop(self) -> Dict[str, Any]:
        """Stop the monitoring scheduler"""
        with self._status_lock:
            if not self._running:
                return {"success": False, "message": "Scheduler not running"}
            
            self._running = False
            self._stop_event.set()
        
        # Wait for thread to finish (with timeout)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        
        print("[SCHEDULER] Stopped")
        return {"success": True, "message": "Scheduler stopped"}
    
    def _run_loop(self):
        """Main scheduler loop"""
        # Run immediately on start
        self._execute_monitoring()
        
        while not self._stop_event.is_set():
            # Wait for interval or stop event
            if self._stop_event.wait(timeout=self._interval):
                break  # Stop event was set
            
            # Check if still running (could have been stopped)
            if not self._running:
                break
                
            # Execute monitoring
            self._execute_monitoring()
    
    def _execute_monitoring(self):
        """Execute a single monitoring run for this specific user"""
        from models import get_db, Source, Keyword, Article
        from keyword_expansion import load_expansions_from_keywords
        from async_monitor_wrapper import run_optimized_monitoring, save_matched_articles_sync
        
        print(f"\n[SCHEDULER] User {self.user_id}: Starting monitoring at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        db = get_db()
        try:
            # Get ALL enabled sources (shared across users)
            sources = db.query(Source).filter(Source.enabled == True).all()
            
            # Get ONLY this user's enabled keywords
            keywords = db.query(Keyword).filter(
                Keyword.enabled == True,
                Keyword.user_id == self.user_id
            ).all()
            
            if not sources or not keywords:
                print(f"[SCHEDULER] User {self.user_id}: No enabled sources or keywords - skipping")
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
            
            with self._status_lock:
                self._last_run = datetime.now()
                self._run_count += 1
                self._last_result = {
                    "success": True,
                    "total_fetched": monitoring_result.get('total_fetched', 0),
                    "total_matches": len(monitoring_result.get('matches', [])),
                    "total_saved": saved_count,
                    "timestamp": self._last_run.isoformat()
                }
            
            print(f"[SCHEDULER] User {self.user_id}: Completed - fetched: {monitoring_result.get('total_fetched', 0)}, saved: {saved_count}")
            
        except Exception as e:
            print(f"[SCHEDULER] User {self.user_id}: Error: {str(e)}")
            import traceback
            traceback.print_exc()
            
            with self._status_lock:
                self._error_count += 1
                self._last_run = datetime.now()
                self._last_result = {
                    "success": False,
                    "error": str(e),
                    "timestamp": self._last_run.isoformat()
                }
        finally:
            db.close()


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
