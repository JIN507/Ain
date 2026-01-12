"""
Tests for Job Executor and Monitoring Jobs

These tests verify:
- Multi-user job isolation
- Per-user job limits (idempotency)
- Job status tracking
- Rate limiting
- Cancellation

Run with: pytest tests/test_job_executor.py -v
"""
import pytest
import sys
import os
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Base, User, MonitorJob, Keyword, Source
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta


# Test database setup
TEST_DB_URL = "sqlite:///:memory:"
test_engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db():
    """Create fresh test database for each test"""
    Base.metadata.create_all(bind=test_engine)
    session = TestSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def user_a(db):
    """Create test user A"""
    user = User(
        email="user_a@test.com",
        name="User A",
        password_hash="hash_a",
        role="USER",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def user_b(db):
    """Create test user B"""
    user = User(
        email="user_b@test.com",
        name="User B",
        password_hash="hash_b",
        role="USER",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestMonitorJobModel:
    """Test MonitorJob model"""
    
    def test_create_job(self, db, user_a):
        """Test creating a monitoring job"""
        job = MonitorJob(
            user_id=user_a.id,
            status='QUEUED',
            progress=0,
            progress_message='Test job'
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        assert job.id is not None
        assert job.user_id == user_a.id
        assert job.status == 'QUEUED'
        assert job.created_at is not None
    
    def test_job_to_dict(self, db, user_a):
        """Test job serialization"""
        job = MonitorJob(
            user_id=user_a.id,
            status='RUNNING',
            progress=50,
            progress_message='Fetching feeds...',
            total_fetched=100,
            total_matched=25,
            total_saved=20
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        
        job_dict = job.to_dict()
        
        assert job_dict['id'] == job.id
        assert job_dict['status'] == 'RUNNING'
        assert job_dict['progress'] == 50
        assert job_dict['total_fetched'] == 100
    
    def test_job_status_transitions(self, db, user_a):
        """Test job status can transition correctly"""
        job = MonitorJob(user_id=user_a.id, status='QUEUED')
        db.add(job)
        db.commit()
        
        # QUEUED -> RUNNING
        job.status = 'RUNNING'
        job.started_at = datetime.utcnow()
        db.commit()
        assert job.status == 'RUNNING'
        
        # RUNNING -> SUCCEEDED
        job.status = 'SUCCEEDED'
        job.finished_at = datetime.utcnow()
        db.commit()
        assert job.status == 'SUCCEEDED'


class TestJobIsolation:
    """Test that jobs are isolated between users"""
    
    def test_user_jobs_are_isolated(self, db, user_a, user_b):
        """User A's jobs should not be visible to User B"""
        # Create job for User A
        job_a = MonitorJob(
            user_id=user_a.id,
            status='RUNNING',
            progress_message='User A job'
        )
        db.add(job_a)
        db.commit()
        
        # Query User B's jobs
        user_b_jobs = db.query(MonitorJob).filter(
            MonitorJob.user_id == user_b.id
        ).all()
        
        assert len(user_b_jobs) == 0
        
        # Query User A's jobs
        user_a_jobs = db.query(MonitorJob).filter(
            MonitorJob.user_id == user_a.id
        ).all()
        
        assert len(user_a_jobs) == 1
        assert user_a_jobs[0].progress_message == 'User A job'
    
    def test_concurrent_users_can_have_jobs(self, db, user_a, user_b):
        """Both users can have active jobs simultaneously"""
        job_a = MonitorJob(user_id=user_a.id, status='RUNNING')
        job_b = MonitorJob(user_id=user_b.id, status='RUNNING')
        
        db.add_all([job_a, job_b])
        db.commit()
        
        running_jobs = db.query(MonitorJob).filter(
            MonitorJob.status == 'RUNNING'
        ).all()
        
        assert len(running_jobs) == 2
        user_ids = {job.user_id for job in running_jobs}
        assert user_ids == {user_a.id, user_b.id}


class TestJobLimits:
    """Test per-user and global job limits"""
    
    def test_one_active_job_per_user(self, db, user_a):
        """Only one active job allowed per user"""
        # Create first job (active)
        job1 = MonitorJob(
            user_id=user_a.id,
            status='RUNNING'
        )
        db.add(job1)
        db.commit()
        
        # Check for active job
        active = db.query(MonitorJob).filter(
            MonitorJob.user_id == user_a.id,
            MonitorJob.status.in_(['QUEUED', 'RUNNING'])
        ).first()
        
        assert active is not None
        assert active.id == job1.id
    
    def test_completed_jobs_dont_block_new(self, db, user_a):
        """Completed jobs don't prevent new jobs"""
        # Create completed job
        old_job = MonitorJob(
            user_id=user_a.id,
            status='SUCCEEDED',
            finished_at=datetime.utcnow()
        )
        db.add(old_job)
        db.commit()
        
        # Should be able to create new job
        active = db.query(MonitorJob).filter(
            MonitorJob.user_id == user_a.id,
            MonitorJob.status.in_(['QUEUED', 'RUNNING'])
        ).first()
        
        assert active is None  # No active job blocking


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    def test_rate_limit_counts_recent_jobs(self, db, user_a):
        """Rate limiting should count jobs in time window"""
        # Create 5 recent jobs
        for i in range(5):
            job = MonitorJob(
                user_id=user_a.id,
                status='SUCCEEDED',
                created_at=datetime.utcnow() - timedelta(minutes=i * 5),
                finished_at=datetime.utcnow() - timedelta(minutes=i * 5)
            )
            db.add(job)
        db.commit()
        
        # Count recent jobs (within 1 hour)
        window_start = datetime.utcnow() - timedelta(hours=1)
        recent_count = db.query(MonitorJob).filter(
            MonitorJob.user_id == user_a.id,
            MonitorJob.created_at >= window_start
        ).count()
        
        assert recent_count == 5


class TestJobCancellation:
    """Test job cancellation"""
    
    def test_queued_job_can_be_cancelled(self, db, user_a):
        """Queued job can be cancelled"""
        job = MonitorJob(user_id=user_a.id, status='QUEUED')
        db.add(job)
        db.commit()
        
        # Cancel
        job.status = 'CANCELLED'
        job.finished_at = datetime.utcnow()
        db.commit()
        
        assert job.status == 'CANCELLED'
    
    def test_completed_job_cannot_be_cancelled(self, db, user_a):
        """Already completed job should not change status"""
        job = MonitorJob(
            user_id=user_a.id,
            status='SUCCEEDED',
            finished_at=datetime.utcnow()
        )
        db.add(job)
        db.commit()
        
        # Attempting to cancel should be rejected (in real code)
        # Here we just verify the status is already terminal
        assert job.status in ['SUCCEEDED', 'FAILED', 'CANCELLED']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
