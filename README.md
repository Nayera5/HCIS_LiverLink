# HCIS LiverLink – Healthcare Information System

A web-based Healthcare Information System built with Django, React, and PostgreSQL (Neon).

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 6.1 + Django REST Framework + SimpleJWT |
| Frontend | React 19 + Vite |
| Database | PostgreSQL on Neon (via Django ORM) |
| Version Control | Git & GitHub |

---

## Project Structure

```text
HCIS_LiverLink/
├── Backend/
│   ├── config/            # Django settings, root URLs, WSGI/ASGI
│   ├── apps/              # One Django app per module
│   │   ├── accounts/      ├── labs/            ├── registry/
│   │   ├── ai_analysis/   ├── notifications/   ├── reporting/
│   │   ├── billing/       ├── prescriptions/   ├── scheduling/
│   │   ├── cdss/          ├── radiology/       └── transplant/
│   │   ├── emr/           └── hl7/
│   ├── manage.py
│   ├── requirements.txt
│   └── .env.example       # Template for Backend/.env
│
├── Frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── .env.example       # Template for Frontend/.env
│
├── .gitignore
└── README.md
```

## Prerequisites

- **Python 3.12 or newer** (required by Django 6.1). Check with `python --version`.
- **Node.js 20 LTS or newer** and npm. Check with `node --version`.
- Git
- VS Code (recommended)
- A **Neon connection string**, which you get privately from the team lead (see [Database](#database))

---

## 1. Clone the Repository

```bash
git clone YOUR_REPOSITORY_URL
cd HCIS_LiverLink
```

## 2. Backend Setup

```bash
cd Backend
python -m venv venv
```

Activate the virtual environment:

| OS | Command |
|---|---|
| Windows (PowerShell) | `.\venv\Scripts\Activate.ps1` |
| Windows (cmd) | `venv\Scripts\activate.bat` |
| macOS / Linux | `source venv/bin/activate` |

> If PowerShell says *"running scripts is disabled on this system"*, run this once and try again:
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

When it's active, `(venv)` appears at the start of your terminal prompt. Then install the dependencies:

```bash
pip install -r requirements.txt
```

Create your local environment file:

```powershell
# Windows
Copy-Item .env.example .env
```
```bash
# macOS / Linux
cp .env.example .env
```

Open `Backend/.env` and fill in:

- `DATABASE_URL`: paste the Neon connection string **exactly as shown below**, with no quotes, no spaces and no repeated `DATABASE_URL=`:
  ```
  DATABASE_URL=postgresql://USER:PASSWORD@ep-xxxx.neon.tech/neondb?sslmode=require
  ```
- `DJANGO_SECRET_KEY`: any long random string. To generate one:
  ```bash
  python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
  ```

> If `DATABASE_URL` is left empty, Django uses a local SQLite file (`db.sqlite3`) instead. That's handy for offline work, but your data won't be shared with the team.

## 3. Check the Setup and Migrate

```bash
python manage.py check      # should print: System check identified no issues
python manage.py migrate    # creates or updates the tables in the database
```

Create an admin account for yourself (one per developer):

```bash
python manage.py createsuperuser
```

## 4. Run the Backend

```bash
python manage.py runserver
```

| URL | What it is |
|---|---|
| http://127.0.0.1:8000/admin/ | Django admin (log in with your superuser) |
| http://127.0.0.1:8000/api/auth/token/ | POST `username` + `password` to get a JWT |
| http://127.0.0.1:8000/api/auth/token/refresh/ | POST `refresh` to get a new access token |

## 5. Frontend Setup

Open a **second** terminal, leaving the backend running:

```bash
cd Frontend
npm install
```

Create the environment file (`Copy-Item .env.example .env` on Windows, `cp .env.example .env` on macOS/Linux), then start the dev server:

```bash
npm run dev
```

Frontend: http://localhost:5173/

The frontend reads the backend address from `VITE_API_URL` in `Frontend/.env` (default `http://127.0.0.1:8000/api`). Access it in code with `import.meta.env.VITE_API_URL`.

---

## Database

The database is PostgreSQL hosted on [Neon](https://neon.tech). We use the **Django ORM**: tables are defined as Python models in each app's `models.py`, and Django creates or changes them through migrations.

### Golden rules

1. **Never create, alter or drop tables by hand** in the Neon console or with SQL. Always change `models.py`, then run `makemigrations` and `migrate`. Otherwise Django's migration history stops matching the real database.
2. **Never share the connection string in Git, chat groups or screenshots.** It contains the database password. Get it privately from the team lead.
3. **Always commit migration files** (`apps/<app>/migrations/0001_….py` and so on).

### Default Django tables

After the first `migrate`, the database contains Django's built-in tables (`auth_user`, `auth_group`, `auth_permission`, `django_migrations`, `django_session`, `django_content_type`, `django_admin_log`, …). These are needed for logins, permissions and the admin site. **Do not delete them.**

### Changing models (developers)

```bash
python manage.py makemigrations <app_name>   # e.g. makemigrations registry
python manage.py migrate
```

After pulling changes from GitHub:

```bash
git pull
python manage.py migrate
```

### Working safely on a shared database

Because the whole team uses one Neon database, **a migration you apply affects everyone immediately**.

- **Recommended:** each developer creates their own **Neon branch** (Neon console → *Branches* → *Create branch* from `main`) and puts that branch's connection string in their own `.env`. A branch is a full copy of the database, so you can experiment freely.
- **On the main/shared database**, only run `migrate` with migrations that are **already merged into `main`** on GitHub. Don't migrate it from an unfinished feature branch.
- If two people change the same app at the same time and Django reports *"Conflicting migrations detected"*, run `python manage.py makemigrations --merge`.

---

## Git Workflow

```bash
git pull origin main                       # before starting work
git checkout -b feature/your-feature-name  # one branch per task
```

When finished:

```bash
git add .
git commit -m "Add your feature description"
git push -u origin feature/your-feature-name
```

Open a Pull Request on GitHub and merge after review.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `running scripts is disabled on this system` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then activate again |
| `ModuleNotFoundError: No module named 'django'` | The venv isn't active. Activate it (you should see `(venv)`), then `pip install -r requirements.txt` |
| `pip install` fails on Django 6.1 | Your Python is older than 3.12. Install Python 3.12+ and recreate the venv |
| `UnknownSchemeError: Scheme '://' is unknown` | `DATABASE_URL` in `Backend/.env` is badly formatted. It must be one line starting `DATABASE_URL=postgresql://` with no quotes |
| `connection ... failed` / timeout | Check your internet connection and that the connection string is correct. The Neon project may also be suspended, so open the Neon console to wake it |
| `relation "..." does not exist` | Run `python manage.py migrate` |
| Frontend gets a CORS error | Make sure `CORS_ALLOWED_ORIGINS` in `Backend/.env` includes `http://localhost:5173` |
| Port 8000 already in use | `python manage.py runserver 8001` (and update `VITE_API_URL`) |

---

## Important Notes

- Never commit `.env` files, connection strings or passwords.
- Never commit `venv/`, `node_modules/` or `db.sqlite3`.
- Always commit Django migration files.
- Coordinate before changing another developer's app.
- Pull the latest changes before starting new work.
