# Ain News Monitor

Full-stack Arabic news monitoring system with per-user sessions, role-based access control (ADMIN/USER), and a React dashboard.

## Project structure

- `backend/` – Flask API, SQLite DB, monitoring pipeline
- `frontend-v2/` – React SPA (Vite/Tailwind setup)

## Backend setup

```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt

# Configure environment
copy ..\.env.example ..\.env  # or create .env manually

# Run DB migrations (only once, if not already done)
python migrate_keywords_per_user.py

# Start API
python app.py
```

The API runs by default on `http://127.0.0.1:5000`.

## Frontend setup

```bash
cd frontend-v2
npm install
npm run dev
```

The SPA runs by default on `http://127.0.0.1:5173` and talks to the Flask API.

## Auth & roles

- Session-based auth using cookies (Flask-Login).
- Roles: `ADMIN`, `USER`.
- Admins can manage users and view audit logs; normal users only see their own data.

## Multi-tenancy & privacy

- **Shared globally:**
  - Countries list
  - Sources list
- **Private per user:**
  - Keywords (unique per user)
  - Article feed (results from monitoring)
  - Export history ("My Files")

## One-time keyword migration

If you are starting from an old DB where `keywords.text_ar` was globally unique, run:

```bash
cd backend
python migrate_keywords_per_user.py
```

This recreates the `keywords` table so that keywords are unique per `(user_id, text_ar)` instead of globally.

## GitHub safety

- Real secrets should go into `.env`, which is ignored by git.
- `ain_news.db` and other `.db` files are ignored and should not be committed.
- `node_modules/` and `frontend-v2/dist/` are ignored.
