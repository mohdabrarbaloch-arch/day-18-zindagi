# Setup Guide

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

cp .env.example .env               # then edit SECRET_KEY, DATABASE_URL
python -m scripts.seed             # optional demo data
uvicorn app.main:app --reload      # http://localhost:8000
```

## Running tests

```bash
pytest -q
ruff check .
ruff format --check .
```

## Docker (PostgreSQL + app)

```bash
docker compose up --build
```

- App → http://localhost:8000
- Postgres → localhost:5432 (user/password/db all `zindagi`)
- The app container runs `scripts.seed` on first boot automatically.

## Deploying to Vercel

The repo ships `vercel.json` and `api/index.py` (serverless entry). To deploy:

1. Push to GitHub (repo is already public).
2. `npm i -g vercel` and run `vercel login` (or use `vercel --token $VERCEL_TOKEN` in CI).
3. `vercel --prod --yes`
4. In the Vercel dashboard set environment variables:
   - `DATABASE_URL` → a managed PostgreSQL connection string
   - `SECRET_KEY` → a long random string (`python -c "import secrets; print(secrets.token_hex(32))"`)
   - `CORS_ORIGINS` → your deployed domain
5. Redeploy — done.

> Note: this sandbox had no Vercel token and interactive `vercel login` is
> impossible in a headless environment, so the live deploy was not performed.
> All routes were verified locally with a production-style uvicorn run.
