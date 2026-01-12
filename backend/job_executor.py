"""
Background Job Executor for Monitoring Jobs

This module provides a thread-based job executor that:
- Runs monitoring jobs in background threads
- Tracks job status in the database
- Enforces per-user limits (one job at a time)
- Provides global concurrency control
- Handles cancellation gracefully

Usage:
    from job_executor import job_executor
    
    # Start a job
    job = job_executor.start_monitoring_job(user_id)
    
    # Check status
    status = job_executor.get_job_status(job_id, user_id)
    
    # Cancel a job
    job_executor.cancel_job(job_id, user_id)
"""
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Set
from contextlib import contextmanager
import traceback


class JobExecutor:
    """
    Thread-based job executor with:
    - Per-user job limits
    - Global concurrency control
    - Database-backed job tracking
    - Graceful cancellation
    """
    
    # Class-level configuration
    MAX_CONCURRENT_JOBS = 5  # Max jobs running globally
    MAX_JOBS_PER_USER = 1    # Max jobs per user
    JOB_TIMEOUT_SECONDS = 300  # 5 minutes max per job
    RATE_LIMIT_WINDOW = 3600  # 1 hour window for rate limiting
    MAX_JOBS_PER_HOUR = 10    # Max jobs per user per hour
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Singleton pattern for global executor"""
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
        
        # Threading controls
        self._global_semaphore = threading.Semaphore(self.MAX_CONCURRENT_JOBS)
        self._user_locks: Dict[int, threading.Lock] = {}
        self._user_locks_lock = threading.Lock()
        
        # Active jobs tracking (for cancellation)
        self._active_jobs: Dict[int, Dict[str, Any]] = {}  # job_id -> {thread, cancel_event, user_id}
        self._active_jobs_lock = threading.Lock()
        
        # Running users (for per-user limits)
        self._running_users: Set[int] = set()
        self._running_users_lock = threading.Lock()
    
    def _get_user_lock(self, user_id: int) -> threading.Lock:
        """Get or create a lock for a specific user"""
        with self._user_locks_lock:
            if user_id not in self._user_locks:
                self._user_locks[user_id] = threading.Lock()
            return self._user_locks[user_id]
    
    def _check_rate_limit(self, db, user_id: int) -> bool:
        """Check if user has exceeded rate limit"""
        from models import MonitorJob
        
        window_start = datetime.utcnow() - timedelta(seconds=self.RATE_LIMIT_WINDOW)
        recent_jobs = db.query(MonitorJob).filter(
            MonitorJob.user_id == user_id,
            MonitorJob.created_at >= window_start
        ).count()
        
        return recent_jobs < self.MAX_JOBS_PER_HOUR
    
    def _get_active_job_for_user(self, db, user_id: int):
        """Get any active (QUEUED or RUNNING) job for a user"""
        from models import MonitorJob
        
        return db.query(MonitorJob).filter(
            MonitorJob.user_id == user_id,
            MonitorJob.status.in_(['QUEUED', 'RUNNING'])
        ).first()
    
    def start_monitoring_job(self, user_id: int) -> Dict[str, Any]:
        """
        Start a new monitoring job for a user.
        
        Returns:
            Dict with job info or error
        """
        from models import get_db, MonitorJob
        
        db = get_db()
        try:
            # Check for existing active job (idempotency)
            existing_job = self._get_active_job_for_user(db, user_id)
            if existing_job:
                return {
                    'success': True,
                    'job_id': existing_job.id,
                    'status': existing_job.status,
                    'message': 'Job already running',
                    'existing': True
                }
            
            # Check rate limit
            if not self._check_rate_limit(db, user_id):
                return {
                    'success': False,
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {self.MAX_JOBS_PER_HOUR} jobs per hour allowed'
                }
            
            # Check global capacity
            with self._running_users_lock:
                if len(self._running_users) >= self.MAX_CONCURRENT_JOBS:
                    return {
                        'success': False,
                        'error': 'Server busy',
                        'message': 'Too many jobs running. Please try again shortly.'
                    }
            
            # Create job record
            job = MonitorJob(
                user_id=user_id,
                status='QUEUED',
                progress=0,
                progress_message='Job queued...'
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            
            job_id = job.id
            
            # Create cancel event for this job
            cancel_event = threading.Event()
            
            # Start background thread
            thread = threading.Thread(
                target=self._execute_job,
                args=(job_id, user_id, cancel_event),
                daemon=True,
                name=f"MonitorJob-{job_id}"
            )
            
            # Track active job
            with self._active_jobs_lock:
                self._active_jobs[job_id] = {
                    'thread': thread,
                    'cancel_event': cancel_event,
                    'user_id': user_id,
                    'started': datetime.utcnow()
                }
            
            # Mark user as running
            with self._running_users_lock:
                self._running_users.add(user_id)
            
            thread.start()
            
            return {
                'success': True,
                'job_id': job_id,
                'status': 'QUEUED',
                'message': 'Monitoring job started',
                'existing': False
            }
            
        except Exception as e:
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to start job'
            }
        finally:
            db.close()
    
    def _execute_job(self, job_id: int, user_id: int, cancel_event: threading.Event):
        """
        Execute the monitoring job in a background thread.
        
        This is where the actual monitoring work happens.
        """
        from models import get_db, MonitorJob, Source, Keyword, Article
        from keyword_expansion import load_expansions_from_keywords
        from async_monitor_wrapper import run_optimized_monitoring, save_matched_articles_sync
        
        # Acquire global semaphore
        acquired = self._global_semaphore.acquire(timeout=60)
        if not acquired:
            self._fail_job(job_id, "Could not acquire execution slot")
            self._cleanup_job(job_id, user_id)
            return
        
        db = get_db()
        try:
            # Update status to RUNNING
            job = db.query(MonitorJob).filter(MonitorJob.id == job_id).first()
            if not job:
                return
            
            job.status = 'RUNNING'
            job.started_at = datetime.utcnow()
            job.progress = 5
            job.progress_message = 'Loading sources and keywords...'
            db.commit()
            
            # Check cancellation
            if cancel_event.is_set():
                self._cancel_job_internal(db, job)
                return
            
            # Get sources and keywords
            sources = db.query(Source).filter(Source.enabled == True).all()
            keywords = db.query(Keyword).filter(
                Keyword.enabled == True,
                Keyword.user_id == user_id
            ).all()
            
            if not sources:
                job.status = 'FAILED'
                job.error_message = 'No enabled sources'
                job.finished_at = datetime.utcnow()
                db.commit()
                return
            
            if not keywords:
                job.status = 'FAILED'
                job.error_message = 'No enabled keywords'
                job.finished_at = datetime.utcnow()
                db.commit()
                return
            
            # Update progress
            job.progress = 10
            job.progress_message = f'Loaded {len(sources)} sources, {len(keywords)} keywords'
            db.commit()
            
            if cancel_event.is_set():
                self._cancel_job_internal(db, job)
                return
            
            # Convert to dicts
            sources_list = [{
                'id': s.id,
                'country_name': s.country_name,
                'name': s.name,
                'url': s.url,
                'enabled': s.enabled
            } for s in sources]
            
            # Load keyword expansions
            job.progress = 15
            job.progress_message = 'Loading keyword expansions...'
            db.commit()
            
            keyword_expansions = load_expansions_from_keywords(keywords)
            
            if not keyword_expansions:
                job.status = 'FAILED'
                job.error_message = 'No keyword expansions found'
                job.finished_at = datetime.utcnow()
                db.commit()
                return
            
            if cancel_event.is_set():
                self._cancel_job_internal(db, job)
                return
            
            # Fetch feeds (this is the slow part)
            job.progress = 20
            job.progress_message = f'Fetching {len(sources_list)} RSS feeds...'
            db.commit()
            
            print(f"[JOB {job_id}] Starting RSS fetch for user {user_id}")
            
            monitoring_result = run_optimized_monitoring(
                sources_list,
                keyword_expansions,
                max_concurrent=50,
                max_per_source=30
            )
            
            if cancel_event.is_set():
                self._cancel_job_internal(db, job)
                return
            
            # Update with fetch results
            job.total_fetched = monitoring_result.get('total_fetched', 0)
            job.progress = 60
            job.progress_message = f'Fetched {job.total_fetched} articles, matching keywords...'
            db.commit()
            
            matches = monitoring_result.get('matches', [])
            job.total_matched = len(matches)
            
            if not matches:
                job.status = 'SUCCEEDED'
                job.progress = 100
                job.progress_message = 'No matching articles found'
                job.finished_at = datetime.utcnow()
                db.commit()
                print(f"[JOB {job_id}] Completed - no matches")
                return
            
            if cancel_event.is_set():
                self._cancel_job_internal(db, job)
                return
            
            # Save matched articles
            job.progress = 70
            job.progress_message = f'Saving {len(matches)} matched articles...'
            db.commit()
            
            saved_ids, save_stats = save_matched_articles_sync(
                db,
                matches,
                apply_limit=True,
                user_id=user_id
            )
            
            # Final update
            job.total_saved = len(saved_ids)
            job.status = 'SUCCEEDED'
            job.progress = 100
            job.progress_message = f'Completed: {len(saved_ids)} articles saved'
            job.finished_at = datetime.utcnow()
            db.commit()
            
            print(f"[JOB {job_id}] Completed - saved {len(saved_ids)} articles")
            
        except Exception as e:
            traceback.print_exc()
            print(f"[JOB {job_id}] Failed: {str(e)}")
            
            try:
                job = db.query(MonitorJob).filter(MonitorJob.id == job_id).first()
                if job:
                    job.status = 'FAILED'
                    job.error_message = str(e)[:500]  # Truncate long errors
                    job.finished_at = datetime.utcnow()
                    db.commit()
            except:
                pass
                
        finally:
            db.close()
            self._global_semaphore.release()
            self._cleanup_job(job_id, user_id)
    
    def _cancel_job_internal(self, db, job):
        """Internal method to mark job as cancelled"""
        job.status = 'CANCELLED'
        job.progress_message = 'Job cancelled by user'
        job.finished_at = datetime.utcnow()
        db.commit()
        print(f"[JOB {job.id}] Cancelled")
    
    def _fail_job(self, job_id: int, error_message: str):
        """Mark a job as failed"""
        from models import get_db, MonitorJob
        
        db = get_db()
        try:
            job = db.query(MonitorJob).filter(MonitorJob.id == job_id).first()
            if job:
                job.status = 'FAILED'
                job.error_message = error_message
                job.finished_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()
    
    def _cleanup_job(self, job_id: int, user_id: int):
        """Clean up after job completion"""
        with self._active_jobs_lock:
            if job_id in self._active_jobs:
                del self._active_jobs[job_id]
        
        with self._running_users_lock:
            self._running_users.discard(user_id)
    
    def get_job_status(self, job_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Get status of a specific job (must belong to user)"""
        from models import get_db, MonitorJob
        
        db = get_db()
        try:
            job = db.query(MonitorJob).filter(
                MonitorJob.id == job_id,
                MonitorJob.user_id == user_id
            ).first()
            
            if not job:
                return None
            
            return job.to_dict()
        finally:
            db.close()
    
    def get_user_jobs(self, user_id: int, limit: int = 10) -> list:
        """Get recent jobs for a user"""
        from models import get_db, MonitorJob
        
        db = get_db()
        try:
            jobs = db.query(MonitorJob).filter(
                MonitorJob.user_id == user_id
            ).order_by(MonitorJob.created_at.desc()).limit(limit).all()
            
            return [job.to_dict() for job in jobs]
        finally:
            db.close()
    
    def get_active_job(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get active job for a user (if any)"""
        from models import get_db, MonitorJob
        
        db = get_db()
        try:
            job = self._get_active_job_for_user(db, user_id)
            return job.to_dict() if job else None
        finally:
            db.close()
    
    def cancel_job(self, job_id: int, user_id: int) -> Dict[str, Any]:
        """Cancel a running job"""
        from models import get_db, MonitorJob
        
        # Check if job is in active jobs
        with self._active_jobs_lock:
            if job_id in self._active_jobs:
                job_info = self._active_jobs[job_id]
                if job_info['user_id'] != user_id:
                    return {'success': False, 'error': 'Not your job'}
                
                # Signal cancellation
                job_info['cancel_event'].set()
                
                return {
                    'success': True,
                    'message': 'Cancellation requested'
                }
        
        # Job not in memory - check DB
        db = get_db()
        try:
            job = db.query(MonitorJob).filter(
                MonitorJob.id == job_id,
                MonitorJob.user_id == user_id
            ).first()
            
            if not job:
                return {'success': False, 'error': 'Job not found'}
            
            if job.status in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
                return {
                    'success': False,
                    'error': f'Job already {job.status.lower()}'
                }
            
            # Job in QUEUED state but not in memory (server restart?)
            job.status = 'CANCELLED'
            job.finished_at = datetime.utcnow()
            db.commit()
            
            return {'success': True, 'message': 'Job cancelled'}
            
        finally:
            db.close()
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status (for admin)"""
        with self._running_users_lock:
            running_count = len(self._running_users)
        
        with self._active_jobs_lock:
            active_jobs = list(self._active_jobs.keys())
        
        return {
            'max_concurrent_jobs': self.MAX_CONCURRENT_JOBS,
            'running_jobs': running_count,
            'active_job_ids': active_jobs,
            'capacity_available': self.MAX_CONCURRENT_JOBS - running_count
        }


# Global executor instance
job_executor = JobExecutor()
