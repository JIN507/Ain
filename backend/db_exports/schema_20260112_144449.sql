-- Ain News Monitor - Database Schema Export
-- Generated: 2026-01-12T14:44:49.028733
-- Engine: SQLite 3

-- Table: articles
CREATE TABLE articles (
                id INTEGER PRIMARY KEY,
                country VARCHAR(100) NOT NULL,
                source_name VARCHAR(200) NOT NULL,
                url VARCHAR(500) NOT NULL UNIQUE,
                
                -- Original content
                title_original TEXT NOT NULL,
                summary_original TEXT,
                original_language VARCHAR(10),
                
                -- Arabic translation
                title_ar TEXT,
                summary_ar TEXT,
                arabic_text TEXT,
                
                -- Keywords (both old and new)
                keyword VARCHAR(200),
                keyword_original VARCHAR(200),
                keywords_translations TEXT,
                
                -- Sentiment (both old and new)
                sentiment VARCHAR(50),
                sentiment_label VARCHAR(50),
                sentiment_score VARCHAR(20),
                
                -- Language (old column)
                language VARCHAR(10),
                
                -- Timestamps
                published_at DATETIME,
                fetched_at DATETIME,
                created_at DATETIME
            , image_url TEXT, user_id INTEGER, source_id INTEGER);


-- Table: articles_new
CREATE TABLE articles_new (
                id INTEGER PRIMARY KEY,
                country VARCHAR(100) NOT NULL,
                source_name VARCHAR(200) NOT NULL,
                url VARCHAR(500) NOT NULL UNIQUE,
                
                -- Original content
                title_original TEXT NOT NULL,
                summary_original TEXT,
                original_language VARCHAR(10),
                
                -- Arabic translation
                title_ar TEXT,
                summary_ar TEXT,
                arabic_text TEXT,
                
                -- Keywords
                keyword VARCHAR(200),  -- OLD (nullable for backward compat)
                keyword_original VARCHAR(200),  -- NEW
                keywords_translations TEXT,
                
                -- Sentiment
                sentiment VARCHAR(50),  -- OLD (nullable for backward compat)
                sentiment_label VARCHAR(50),  -- NEW
                sentiment_score VARCHAR(20),
                
                -- Timestamps
                published_at DATETIME,
                fetched_at DATETIME,
                created_at DATETIME,
                
                -- Old language column (deprecated)
                language VARCHAR(10)
            );


-- Table: audit_log
CREATE TABLE audit_log (
	id INTEGER NOT NULL, 
	user_id INTEGER, 
	admin_id INTEGER, 
	action VARCHAR(100) NOT NULL, 
	meta_json TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(admin_id) REFERENCES users (id)
);

CREATE INDEX ix_audit_log_admin_id ON audit_log (admin_id);
CREATE INDEX ix_audit_log_user_id ON audit_log (user_id);

-- Table: countries
CREATE TABLE countries (
	id INTEGER NOT NULL, 
	name_ar VARCHAR(100) NOT NULL, 
	enabled BOOLEAN, 
	created_at DATETIME, user_id INTEGER, 
	PRIMARY KEY (id)
);


-- Table: exports
CREATE TABLE exports (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	filters_json TEXT, 
	article_count INTEGER, 
	created_at DATETIME, filename TEXT, stored_filename TEXT, file_size INTEGER, source_type TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_exports_user_id ON exports (user_id);

-- Table: keywords
CREATE TABLE "keywords" (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            text_ar VARCHAR(200) NOT NULL,
            text_en VARCHAR(200),
            text_fr VARCHAR(200),
            text_tr VARCHAR(200),
            text_ur VARCHAR(200),
            text_zh VARCHAR(200),
            text_ru VARCHAR(200),
            text_es VARCHAR(200),
            enabled BOOLEAN DEFAULT 1,
            created_at DATETIME,
            UNIQUE(user_id, text_ar)
        );


-- Table: search_history
CREATE TABLE search_history (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	search_type VARCHAR(50) NOT NULL, 
	"query" TEXT, 
	filters_json TEXT, 
	results_count INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_search_history_user_id ON search_history (user_id);

-- Table: sources
CREATE TABLE sources (
	id INTEGER NOT NULL, 
	country_id INTEGER NOT NULL, 
	country_name VARCHAR(100) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	url VARCHAR(500) NOT NULL, 
	enabled BOOLEAN, 
	last_checked DATETIME, 
	fail_count INTEGER, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (url)
);


-- Table: user_articles
CREATE TABLE user_articles (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	article_id INTEGER NOT NULL, 
	keyword_id INTEGER, 
	keyword_original VARCHAR(200), 
	keywords_translations TEXT, 
	sentiment_label VARCHAR(50), 
	sentiment_score VARCHAR(20), 
	is_read BOOLEAN, 
	is_starred BOOLEAN, 
	notes TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_article UNIQUE (user_id, article_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(article_id) REFERENCES articles (id), 
	FOREIGN KEY(keyword_id) REFERENCES keywords (id)
);

CREATE INDEX ix_user_articles_article_id ON user_articles (article_id);
CREATE INDEX ix_user_articles_user_id ON user_articles (user_id);

-- Table: user_countries
CREATE TABLE user_countries (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	country_id INTEGER NOT NULL, 
	enabled BOOLEAN, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_country UNIQUE (user_id, country_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(country_id) REFERENCES countries (id)
);

CREATE INDEX ix_user_countries_country_id ON user_countries (country_id);
CREATE INDEX ix_user_countries_user_id ON user_countries (user_id);

-- Table: user_files
CREATE TABLE user_files (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	stored_filename VARCHAR(255) NOT NULL, 
	file_type VARCHAR(50), 
	file_size INTEGER, 
	description TEXT, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_user_files_user_id ON user_files (user_id);

-- Table: user_sources
CREATE TABLE user_sources (
	id INTEGER NOT NULL, 
	user_id INTEGER NOT NULL, 
	source_id INTEGER NOT NULL, 
	enabled BOOLEAN, 
	created_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_source UNIQUE (user_id, source_id), 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(source_id) REFERENCES sources (id)
);

CREATE INDEX ix_user_sources_source_id ON user_sources (source_id);
CREATE INDEX ix_user_sources_user_id ON user_sources (user_id);

-- Table: users
CREATE TABLE users (
	id INTEGER NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	name VARCHAR(255), 
	password_hash VARCHAR(255) NOT NULL, 
	role VARCHAR(20) NOT NULL, 
	is_active BOOLEAN, 
	must_change_password BOOLEAN, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (email)
);


