# Retirement Calculator (Local)

A local-only version of a personal retirement projection dashboard built with FastAPI, SQLAlchemy, Jinja2, and Chart.js.

It answers one question: **How is the plan holding up over time?**

> Estimates only. Projections and Monte Carlo simulations are illustrative, not financial advice.

---

## Sample data

This repository ships with **fictional base-case data** in `data/users.json`:

- Two sample household members (`Steven` and `Alyssa`) with made-up balances, salaries, and assets
- Generic household debts, a sample residence, and sample spending

Replace the sample data with your own by editing `data/users.json` or by creating a `data/users.local.json` file (ignored by git) that takes precedence.

---

## Quick start (Windows PowerShell)

Requires [uv](https://docs.astral.sh/uv/) (`winget install --id astral-sh.uv -e`).

```powershell
cd retirement-calculator-local
Copy-Item .env.example .env   # then edit SECRET_KEY and any auth passwords
.\start_web.ps1
```

Or run it manually:

```powershell
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Open:

- `http://localhost:8000/`
- `http://localhost:8000/health`

---

## Configuration

Copy `.env.example` to `.env` and adjust:

- `DATABASE_URL` defaults to a local SQLite file (`sqlite:///retirement.db`). The database file is created locally and is never committed.
- `SECRET_KEY` should be a long random string.
- `AUTH_*_PASSWORD` values enable HTTP Basic Auth for each user. A blank password disables that account.
- `UPLOAD_DIR` optionally changes where uploaded documents are stored (defaults to `data/uploads/`).

---

## Tests

```powershell
uv run pytest
```
