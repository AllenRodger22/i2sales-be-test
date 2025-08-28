# i2Sales API Tests (pytest)

Automated smoke + functional tests for the i2Sales Flask API.

## Setup
```bash
python -m venv .venv
source .venv/Scripts/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env  # edit BASE_URL and admin creds if needed
```

## Run
```bash
pytest              # run all tests
pytest -m smoke     # only health/login smoke checks
pytest -m "destructive"  # includes create/update/delete flows
```

These tests will:
- login and obtain JWT
- CRUD clients (and clean up if ADMIN)
- create interactions and validate side-effects
- read analytics endpoints
