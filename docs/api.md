# API Reference

Base URL: `http://localhost:8000/api` (production: your deployed domain `/api`)

Auth: `Authorization: Bearer <token>` on protected endpoints.

## Auth

### POST /auth/register
Create an account and get a token.

```json
{
  "email": "ali@example.com",
  "password": "password123",
  "full_name": "Ali Raza",
  "phone": "0311-1234567",
  "role": "donor"
}
```
→ `201` `{access_token, token_type, role, user_id, full_name}`

Errors: `409` email taken · `422` validation

### POST /auth/login
```json
{"email": "ali@example.com", "password": "password123"}
```
→ `200` token payload · `401` bad credentials

### GET /auth/me *(auth)*
→ `200` `{id, email, full_name, phone, role, created_at}`

## Donors

### PUT /donors/profile *(auth, donor)*
Create or update your donor profile.

```json
{
  "blood_group": "O-",
  "city": "Karachi",
  "area": "Clifton",
  "birth_year": 1995,
  "weight_kg": 70,
  "is_available": true
}
```
→ `200` profile · `400` ineligible (age/weight) · `422` invalid blood group

### GET /donors/profile *(auth)*
→ `200` your profile

### PATCH /donors/availability *(auth)*
```json
{"is_available": false}
```
→ `200` updated profile

### GET /donors/{user_id}
→ `200` public profile · `404` not found

## Blood Requests

### POST /requests *(auth)*
```json
{
  "patient_name": "Fatima Ahmed",
  "blood_group": "O-",
  "units_needed": 2,
  "hospital": "Aga Khan University Hospital",
  "city": "Karachi",
  "area": "Clifton",
  "urgency": "emergency",
  "notes": "Accident victim"
}
```
→ `201` request with `expires_at` based on urgency · `422` invalid

### GET /requests
Public list. Query params: `status_filter`, `blood_group`, `city`.

### GET /requests/my *(auth)*
Your requests, newest first.

### GET /requests/{id}
→ `200` single request (lazy-expired if past window)

### GET /requests/{id}/matches *(auth)*
→ `200` `[{donor_id, name, phone, blood_group, city, area, is_verified, donation_count, last_donation_date, age}]`
- `409` request not open

### POST /requests/{id}/fulfill *(auth, requester/admin)*
```json
{"donor_id": 3, "units": 1}
```
→ `200` fulfilled request · `403` not the requester · `409` incompatible donor or not open

### POST /requests/{id}/cancel *(auth, requester/admin)*
→ `200` cancelled · `409` not open

## Admin *(role: admin)*

### GET /admin/stats
→ `200` `{donors, available_donors, verified_donors, open_requests, fulfilled_requests, total_donations}`

### POST /admin/donors/{user_id}/verify
→ `200` verified profile · `404` not found

### GET /admin/donors
→ `200` list of all donor profiles

## Public

### GET /health
→ `200` `{status: "ok", app, version}`

### GET /blood-groups
→ `200` `{groups, universal_donor, universal_recipient, compatibility}`
