# 🩸 Zindagi (زندگی) — Blood Donor Network

Find a compatible blood donor in minutes. Zindagi connects verified donors to
emergency requests across Pakistan — no more WhatsApp forwards, no more
guessing who can donate to whom.

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00)
![Tests](https://img.shields.io/badge/tests-59%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)

---

## Why Zindagi?

Every few seconds someone in Pakistan needs blood — an accident victim, a
surgery patient, a thalassemia child. Families scramble through phone calls
and WhatsApp forwards, often reaching out hours after the window closes.

Zindagi is a **public donor registry with a compatibility engine**. Donors
register once (blood group, city, area, availability, last donation date).
Anyone can post an emergency request — and the platform instantly lists
**compatible, eligible, available** donors near them.

## ✨ Features

- **Compatibility engine** — ABO/Rh rules encoded and unit-tested; no guessing
- **Smart matching** — finds donors who are compatible, within age/weight rules,
  past the 90-day cooldown, and currently available; verified donors rank first
- **Emergency requests** — urgency-based expiry (6h emergency / 24h urgent / 72h normal)
- **Full request lifecycle** — open → fulfilled | cancelled | expired, with lazy expiry
- **Donor profiles** — availability toggle, verification badge, donation history
- **Auth** — JWT (24h) + bcrypt (12 rounds) + rate-limited login, 3 roles
  (donor / requester / admin)
- **Admin** — platform stats, donor verification
- **Public compatibility guide** — the ABO cheat sheet on the landing page
- **Mobile-first dark SPA** — zero build step, works on any phone
- **Docker-ready** — PostgreSQL 16 via docker-compose, SQLite fallback for dev

## 🖼️ Screenshots

| Landing & compatibility guide | Auth | Donor dashboard |
|---|---|---|
| ![Landing](https://static.teamily.ai/sites/693b4282-077f-4bcf-815f-eaa3ea0ec6f3/documents/landing/landing.png) | ![Auth](https://static.teamily.ai/sites/693b4282-077f-4bcf-815f-eaa3ea0ec6f3/documents/auth/auth.png) | ![Donor](https://static.teamily.ai/sites/693b4282-077f-4bcf-815f-eaa3ea0ec6f3/documents/donor/donor.png) |

## 🚀 Quick Start (local)

```bash
git clone https://github.com/mohdabrarbaloch-arch/day-18-zindagi.git
cd day-18-zindagi

# 1. Set up Python
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env

# 3. Seed demo data (admin, 8 donors, requester, 2 open requests)
python -m scripts.seed

# 4. Run
uvicorn app.main:app --reload
```

Open **http://localhost:8000** — the SPA is served from the same origin.

### Demo accounts (after seeding)

| Role | Email | Password |
|---|---|---|
| Admin | admin@zindagi.pk | admin12345 |
| Donor | donor1@zindagi.pk | donor12345 |
| Requester | requester@zindagi.pk | requester12345 |

## 🐳 Docker (PostgreSQL)

```bash
docker compose up --build
# App: http://localhost:8000  ·  Postgres: localhost:5432
```

## 📚 Documentation

- [Setup guide](docs/setup.md)
- [Usage guide](docs/usage.md)
- [API reference](docs/api.md)
- [Architecture](ARCHITECTURE.md)

## 🧪 Tests & Quality

```bash
pytest -q          # 59 tests — compatibility matrix, eligibility, full API flow
ruff check .       # lint clean
ruff format .      # format clean
```

## 🔒 Security

- bcrypt password hashing (12 rounds), JWT 24h expiry, rate-limited auth
- Role-scoped access; foreign resources return 404 (no existence leaks)
- CORS allow-list, Pydantic input validation on every endpoint
- Secrets only via environment variables — nothing hardcoded

## 🧰 Tech Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI · SQLAlchemy 2.0 · Pydantic v2 · Python 3.11 |
| Auth | JWT (HS256) · bcrypt · SlowAPI |
| Database | SQLite (WAL, dev) / PostgreSQL 16 (prod) |
| Frontend | Vanilla JS · mobile-first dark SPA |
| Infra | Docker · docker-compose · Vercel-ready (`api/index.py`) |

## ☁️ Deployment

The repo is **Vercel-ready** — see [docs/setup.md](docs/setup.md) for the exact
steps (set `DATABASE_URL` to a managed Postgres, `SECRET_KEY` to a long random
string). *Current status: not deployed — no Vercel token available in the build
environment. Production build verified locally (all routes 200, 59 tests).*

## 📄 License

MIT — see [LICENSE](LICENSE). Built by ABraz Baloch as part of a 30-day
build challenge.
