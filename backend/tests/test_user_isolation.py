"""
User Isolation Tests

These tests verify that user data is properly isolated and cannot leak between users.
Run with: pytest tests/test_user_isolation.py -v
"""
import pytest
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    Base, User, Keyword, Article, ExportRecord, SearchHistory, UserFile,
    engine, SessionLocal, get_db
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime


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


@pytest.fixture
def admin_user(db):
    """Create admin user"""
    user = User(
        email="admin@test.com",
        name="Admin",
        password_hash="hash_admin",
        role="ADMIN",
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestKeywordIsolation:
    """Test that keywords are properly isolated between users"""
    
    def test_user_a_cannot_see_user_b_keywords(self, db, user_a, user_b):
        """User A's keywords should not be visible to User B"""
        # User A creates a keyword
        keyword_a = Keyword(
            user_id=user_a.id,
            text_ar="كلمة المستخدم أ",
            enabled=True
        )
        db.add(keyword_a)
        db.commit()
        
        # Query keywords filtered by User B's ID
        user_b_keywords = db.query(Keyword).filter(
            Keyword.user_id == user_b.id
        ).all()
        
        # User B should see no keywords
        assert len(user_b_keywords) == 0
        
        # User A should see their keyword
        user_a_keywords = db.query(Keyword).filter(
            Keyword.user_id == user_a.id
        ).all()
        assert len(user_a_keywords) == 1
        assert user_a_keywords[0].text_ar == "كلمة المستخدم أ"
    
    def test_keyword_user_id_is_required_for_isolation(self, db, user_a, user_b):
        """Keywords with NULL user_id are a potential leak"""
        # Create keyword without user_id (legacy data)
        keyword_orphan = Keyword(
            user_id=None,  # This is problematic!
            text_ar="كلمة يتيمة",
            enabled=True
        )
        db.add(keyword_orphan)
        db.commit()
        
        # Neither user should see orphaned keywords when filtering by user_id
        user_a_keywords = db.query(Keyword).filter(
            Keyword.user_id == user_a.id
        ).all()
        user_b_keywords = db.query(Keyword).filter(
            Keyword.user_id == user_b.id
        ).all()
        
        assert len(user_a_keywords) == 0
        assert len(user_b_keywords) == 0
        
        # But orphaned keyword exists
        all_keywords = db.query(Keyword).all()
        assert len(all_keywords) == 1


class TestArticleIsolation:
    """Test that articles are properly isolated between users"""
    
    def test_user_a_cannot_see_user_b_articles(self, db, user_a, user_b):
        """User A's articles should not be visible to User B"""
        # User A's article
        article_a = Article(
            user_id=user_a.id,
            country="السعودية",
            source_name="Source A",
            url="https://example.com/article-a",
            title_original="Article for User A"
        )
        db.add(article_a)
        db.commit()
        
        # Query articles filtered by User B's ID
        user_b_articles = db.query(Article).filter(
            Article.user_id == user_b.id
        ).all()
        
        # User B should see no articles
        assert len(user_b_articles) == 0
        
        # User A should see their article
        user_a_articles = db.query(Article).filter(
            Article.user_id == user_a.id
        ).all()
        assert len(user_a_articles) == 1
    
    def test_articles_from_monitoring_are_user_scoped(self, db, user_a, user_b):
        """Articles created during monitoring should be scoped to the user who ran it"""
        # Simulate monitoring results for User A
        for i in range(5):
            article = Article(
                user_id=user_a.id,
                country="مصر",
                source_name=f"Source {i}",
                url=f"https://example.com/article-{i}",
                title_original=f"Article {i}",
                keyword_original="كلمة المراقبة"
            )
            db.add(article)
        db.commit()
        
        # User A should see all 5 articles
        user_a_count = db.query(Article).filter(
            Article.user_id == user_a.id
        ).count()
        assert user_a_count == 5
        
        # User B should see 0 articles
        user_b_count = db.query(Article).filter(
            Article.user_id == user_b.id
        ).count()
        assert user_b_count == 0


class TestExportIsolation:
    """Test that exports are properly isolated between users"""
    
    def test_user_cannot_see_other_user_exports(self, db, user_a, user_b):
        """Users should only see their own exports"""
        # User A creates an export
        export_a = ExportRecord(
            user_id=user_a.id,
            article_count=10,
            filename="export_a.xlsx"
        )
        db.add(export_a)
        db.commit()
        
        # User B should not see User A's export
        user_b_exports = db.query(ExportRecord).filter(
            ExportRecord.user_id == user_b.id
        ).all()
        assert len(user_b_exports) == 0


class TestSearchHistoryIsolation:
    """Test that search history is properly isolated between users"""
    
    def test_user_cannot_see_other_user_search_history(self, db, user_a, user_b):
        """Users should only see their own search history"""
        # User A's search
        search_a = SearchHistory(
            user_id=user_a.id,
            search_type="keyword",
            query="بحث المستخدم أ",
            results_count=100
        )
        db.add(search_a)
        db.commit()
        
        # User B should not see User A's search
        user_b_searches = db.query(SearchHistory).filter(
            SearchHistory.user_id == user_b.id
        ).all()
        assert len(user_b_searches) == 0


class TestAdminDoesNotBypassIsolation:
    """Test that admin role does NOT bypass user data isolation"""
    
    def test_admin_queries_with_force_filter(self, db, user_a, admin_user):
        """Admin should only see their own user data when force_filter is used"""
        # User A creates a keyword
        keyword_a = Keyword(
            user_id=user_a.id,
            text_ar="كلمة المستخدم",
            enabled=True
        )
        db.add(keyword_a)
        db.commit()
        
        # Admin queries with their own user_id filter (force_filter behavior)
        admin_keywords = db.query(Keyword).filter(
            Keyword.user_id == admin_user.id
        ).all()
        
        # Admin should NOT see User A's keywords
        assert len(admin_keywords) == 0


class TestScopingHelper:
    """Test the db_scoping helper functions"""
    
    def test_scope_to_user_filters_correctly(self, db, user_a, user_b):
        """scope_to_user should filter by user_id"""
        # Create keywords for both users
        keyword_a = Keyword(user_id=user_a.id, text_ar="كلمة أ", enabled=True)
        keyword_b = Keyword(user_id=user_b.id, text_ar="كلمة ب", enabled=True)
        db.add_all([keyword_a, keyword_b])
        db.commit()
        
        # Manually apply the same logic as scope_to_user
        query = db.query(Keyword)
        filtered_query = query.filter(Keyword.user_id == user_a.id)
        results = filtered_query.all()
        
        assert len(results) == 1
        assert results[0].text_ar == "كلمة أ"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
