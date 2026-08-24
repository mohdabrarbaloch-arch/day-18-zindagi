# Usage Guide

## Roles

| Role | What you can do |
|---|---|
| Donor | Create/edit donor profile, toggle availability, see open requests |
| Requester | Post blood requests, find compatible donors, mark requests fulfilled |
| Admin | View platform stats, verify donor profiles |

## As a Donor

1. **Register** with role "Donor" (or log in).
2. Go to **Dashboard** and fill your profile: blood group, city, area, birth
   year, weight. Under-age / under-weight donors are rejected with a clear
   message.
3. Toggle **availability** — you only appear in matches when available.
4. Browse **Open requests near you** and hit *Matches* to see compatible
   patients. Contact the requester directly (phone is shown).

## As a Requester

1. Register with role "Requester".
2. **Post a blood request**: patient name, blood group, units, hospital, city,
   area, urgency.
   - `emergency` expires in **6 hours**
   - `urgent` expires in **24 hours**
   - `normal` expires in **72 hours**
3. Open your request and hit **Find donors** — Zindagi lists compatible,
   eligible, available donors (verified first, same-city first).
4. When a donor delivers, click **Got blood** — the request is marked
   fulfilled, the donor's donation count increments, and they enter the
   90-day cooldown automatically.

## Compatibility cheat sheet

| Patient | Can receive from |
|---|---|
| O- | O- |
| O+ | O-, O+ |
| A- | O-, A- |
| A+ | O-, O+, A-, A+ |
| B- | O-, B- |
| B+ | O-, O+, B-, B+ |
| AB- | O-, A-, B-, AB- |
| AB+ | everyone (universal recipient) |

O- is the **universal donor**; AB+ is the **universal recipient**.

## Admin

Use `admin@zindagi.pk / admin12345` (seeded) to view stats and verify donor
profiles. Verification is a trust badge — verified donors rank first in matches.
