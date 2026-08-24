# Zindagi (زندگی) — Blood Donor Network & Emergency Request Platform

## Problem
Every few seconds someone in Pakistan needs blood — an accident victim, a surgery patient, a thalassemia child. Hospitals and families scramble through phone calls and WhatsApp forwards, often reaching out hours after the window closes. There is no public, searchable registry of verified donors, and no way to know which donors are *compatible* and *available* right now.

## Solution
Zindagi is a blood donor network where donors register once (blood group, city, area, availability, last donation date), and anyone can post an emergency blood request. The platform's compatibility engine instantly finds **compatible, eligible, available** donors near the request — no guessing ABO/Rh rules, no dead-end phone calls.

---

## System Diagram

```
┌──────────────────────────────────────────┐
│            Client (SPA — mobile-first)   │
│  Donor view: profile, availability,      │
│             matches, history             │
│  Requester view: post request, find      │
│                 compatible donors,       │
│                 fulfill                  │
│  Public view: live stats, compatibility  │
│              guide                       │
└──────────────────┬───────────────────────┘
                   │ HTTPS / JSON (REST)
┌──────────────────▼───────────────────────┐
│          FastAPI Application             │
│  ┌──────┐ ┌──────┐ ┌─────────┐ ┌──────┐ │
│  │ auth │ │donors│ │requests │ │admin │ │
│  │router│ │router│ │ router  │ │router│ │
│  └──┬───┘ └──┬───┘ └────┬────┘ └──┬───┘ │
│     └─────────┴──────────┴─────────┘     │
│  ┌─────────────────────────────────────┐ │
│  │  Services layer                     │ │
│  │  compatibility engine (pure logic)  │ │
│  │  matcher (eligibility + ranking)    │ │
│  └──────────────────┬──────────────────┘ │
└─────────────────────┼────────────────────┘
                      │ SQLAlchemy 2.0 ORM
┌─────────────────────▼────────────────────┐
│         Database (SQLite/Postgres)       │
│  users · donor_profiles · blood_requests │
│  donation_events · notifications         │
└──────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| API | FastAPI 0.115, Pydantic v2 |
| ORM | SQLAlchemy 2.0 (typed mapped_column) |
| Auth | JWT (HS256, 24h) + bcrypt (12 rounds) + SlowAPI rate limits |
| Database | SQLite (WAL, dev) / PostgreSQL 16 (prod, docker-compose) |
| Frontend | Vanilla JS, mobile-first dark SPA (zero build step) |
| Infra | Docker · docker-compose · Vercel-ready serverless |

## Data Model

- **users** — id, email (unique), password_hash, full_name, phone, role (donor/requester/admin), created_at
- **donor_profiles** — id, user_id (unique FK), blood_group, city, area, birth_year, weight_kg, last_donation_date, is_available, is_verified, donation_count, created_at
- **blood_requests** — id, requester_id FK, patient_name, blood_group, units_needed, hospital, city, area, urgency (normal/urgent/emergency), status (open/fulfilled/cancelled/expired), notes, created_at, expires_at, fulfilled_at
- **donation_events** — id, request_id FK, donor_id FK, blood_group, units, donated_at
- **notifications** — id, user_id FK, message, is_read, created_at

## Core Logic

### Compatibility engine (`app/core/compatibility.py`)
Pure, unit-tested ABO/Rh rules:

| Patient | Compatible donor groups |
|---|---|
| O- | O- |
| O+ | O-, O+ |
| A- | O-, A- |
| A+ | O-, O+, A-, A+ |
| B- | O-, B- |
| B+ | O-, O+, B-, B+ |
| AB- | O-, A-, B-, AB- |
| AB+ | all (universal recipient) |

### Eligibility rules
- Age 18–60 (configurable), weight ≥ 50 kg
- 90-day donation cooldown
- Must be currently available

### Matching (`app/services/matcher.py`)
`find_matching_donors` filters compatible groups in SQL, then eligibility in
Python, then sorts: **verified first → same-city first → longest cooldown first**.

### Request lifecycle
`open` → `fulfilled` | `cancelled` | `expired` (lazy expiry on read: past
the urgency window, an open request flips to expired automatically).

## API Surface

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | /api/auth/register | — | Register (donor/requester) → JWT |
| POST | /api/auth/login | — | Log in → JWT |
| GET | /api/auth/me | ✓ | Current user |
| PUT | /api/donors/profile | donor | Create/update donor profile |
| GET | /api/donors/profile | ✓ | Own profile |
| PATCH | /api/donors/availability | ✓ | Toggle availability |
| GET | /api/donors/{user_id} | — | Public donor profile |
| POST | /api/requests | ✓ | Post blood request |
| GET | /api/requests | — | List (filter by status/group/city) |
| GET | /api/requests/my | ✓ | Own requests |
| GET | /api/requests/{id} | — | Single request |
| GET | /api/requests/{id}/matches | ✓ | Compatible donors |
| POST | /api/requests/{id}/fulfill | requester | Mark fulfilled + record donation |
| POST | /api/requests/{id}/cancel | requester | Cancel open request |
| GET | /api/admin/stats | admin | Platform stats |
| POST | /api/admin/donors/{id}/verify | admin | Verify donor |
| GET | /api/admin/donors | admin | List all donors |
| GET | /api/health | — | Health check |
| GET | /api/blood-groups | — | Compatibility reference |

## Security

- bcrypt (12 rounds) password hashing; JWT HS256 with 24h expiry
- Rate-limited auth endpoints (SlowAPI)
- Role-scoped access; foreign resources return 404 (no existence leaks)
- CORS allow-list; Pydantic validation on every request
- Secrets only via env vars (.env.example documents all)

## Scaling Notes

- **Stateless API** — horizontal scaling behind a load balancer is trivial
- **Postgres** — move DATABASE_URL to a managed Postgres (Neon/Supabase/RDS)
- **Indexes** — blood_group, city, is_available, status are indexed; add a
  composite index on (city, blood_group, is_available) at scale
- **Search** — swap city/area filtering for PostGIS or Elasticsearch when geo-search lands
- **Notifications** — the notifications table is ready; wire an SMS/WhatsApp
  gateway (e.g. Twilio) to notify matched donors in real time
- **Rate limits** — tune SlowAPI limits per-deployment

## Local Run

```bash
pip install -e ".[dev]"
cp .env.example .env
python -m scripts.seed
uvicorn app.main:app --reload   # http://localhost:8000
```

## Docker

```bash
docker compose up --build
```
