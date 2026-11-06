# Deploying SkillTrack AI publicly (free)

The app is a Flask server plus MySQL. Free hosts rarely give both, so the
recommended free setup is:

| Part | Service | Free allowance |
|------|---------|----------------|
| Web app | **Render** Free web service | 512 MB RAM, 0.1 CPU, spins down after 15 min idle, 750 instance hours/month |
| Database | **TiDB Cloud Starter** (MySQL-compatible) | 25 GiB row storage, 250M request units/month |

Both have a free tier that does not require a credit card at the time of
writing. Free allowances can change — check the provider's pricing page before
relying on them.

> **Account signup is required.** Render and TiDB authenticate through GitHub
> or email, so the final "create account" click must be done by you. Everything
> else is prepared in this repository.

---

## Option A — Instant public URL (temporary, no account)

Useful for a quick demo or viva. Your laptop must stay on, and the URL changes
every time you restart the tunnel.

### Cloudflare Quick Tunnel

```powershell
winget install --id Cloudflare.cloudflared
# new terminal, with the app already running on port 5000:
cloudflared tunnel --url http://127.0.0.1:5000
```

Cloudflare prints a URL like:

```
https://random-words-here.trycloudflare.com
```

Open it from any phone or another network. Press `Ctrl + C` to stop.

### SSH alternative (nothing to install)

```powershell
ssh -R 80:localhost:5000 nokey@localhost.run
```

The service prints a public `https://...lhr.life` URL. Keep the SSH window open.

**Limitations:** temporary URL, laptop must stay awake, no custom domain.

---

## Option B — Permanent free deployment (Render + TiDB Cloud)

### 1. Create the free MySQL-compatible database

1. Open <https://tidbcloud.com/free-trial/> and sign in with GitHub (or email).
2. Create a **Starter** cluster. Choose the region closest to you
   (`Singapore` for India).
3. Wait for the cluster to become **Available**.
4. Click **Connect** and copy:
   * host, e.g. `gateway01.ap-southeast-1.prod.aws.tidbcloud.com`
   * port, normally `4000`
   * user, e.g. `3xAbC123.root`
   * password (click **Generate** / **Reset password** if needed)
5. Keep TLS on. The app connects with `DB_SSL_MODE=required` (encrypted,
   certificate not verified), which is what TiDB expects.

The schema uses `utf8mb4_general_ci`, `AUTO_INCREMENT`, `JSON`, `ENUM`,
foreign keys and `CHECK` constraints — all supported by TiDB.

### 2. Deploy the web service on Render

1. Open the one-click blueprint:

   <https://render.com/deploy?repo=https://github.com/devsodage7/skilltrack-ai>

2. Sign in with GitHub and authorize the repository.
3. Render reads `render.yaml` and asks for the values marked `sync: false`:
   * `DB_HOST` — TiDB host
   * `DB_USER` — TiDB user
   * `DB_PASSWORD` — TiDB password
4. Keep the defaults:
   * `DB_PORT=4000`
   * `DB_NAME=skilltrack_ai`
   * `DB_SSL_MODE=required`
5. Click **Apply** / **Create Web Service** and wait for the build.

The first deploy can take 3–6 minutes because scikit-learn, pandas and PyMuPDF
are compiled/downloaded. The service gets a URL like:

```
https://skilltrack-ai-xxxx.onrender.com
```

### 3. Create the tables and seed data

Render Free does not provide shell access, so run the bootstrap from your
laptop against the cloud database. In PowerShell:

```powershell
cd D:\projects\CODE

# Use single quotes so @, $ and ! stay literal
$env:DB_HOST = 'gateway01.ap-southeast-1.prod.aws.tidbcloud.com'
$env:DB_PORT = '4000'
$env:DB_USER = '3xAbC123.root'
$env:DB_PASSWORD = 'paste-password-here'
$env:DB_NAME = 'skilltrack_ai'
$env:DB_SSL_MODE = 'required'

.\.venv\Scripts\python.exe database\init_db.py --reset
```

`--reset` drops and recreates the tables, then seeds all 11 tables. It prints
`Validation: OK` when the data is healthy.

> `load_dotenv` does **not** override variables that already exist in the
> shell, so the values above win over your local `.env`.

If the command fails with `CREATE DATABASE` permission denied, set
`$env:DB_NAME` to the default database name shown in the TiDB console and run
again (the seed script will use it instead of creating a new one).

### 4. Restart and open the site

In Render: **Manual Deploy → Restart** (or push any commit; auto-deploy is on).

Open the service URL and log in with a demo account:

```
admin@skilltrack.local       / Admin@123
aarav.patil@skilltrack.local / Student@123
```

### 5. Secure the public demo

The seeded passwords are public in this repository. Before sharing the URL:

1. Register your own account through `/register`.
2. Give it the admin role:

   ```powershell
   # same DB_* environment variables as step 3
   .\.venv\Scripts\python.exe database\set_password.py your@email.com --admin
   ```

   Add `--generate` to create a random strong password and print it once
   instead of typing one:

   ```powershell
   .\.venv\Scripts\python.exe database\set_password.py admin@skilltrack.local --admin --generate
   ```

3. Deactivate the seeded admin in the TiDB SQL editor:

   ```sql
   UPDATE students SET is_active = 0
    WHERE email = 'admin@skilltrack.local';
   ```

4. Optionally rotate the demo student passwords the same way with
   `database\set_password.py`.

Also confirm `SECRET_KEY` is the random value generated by Render — never the
development default.

### 6. Updating the live site

```powershell
git add .
git commit -m "describe the change"
git push
```

Render redeploys automatically from `main`.

---

## What the free tiers do not give you

| Limitation | Effect | Workaround |
|------------|--------|------------|
| Render spins down after 15 min idle | First visit takes ~1 minute | Accept for a demo, or upgrade to a paid instance |
| Render filesystem is ephemeral | Uploaded PDFs disappear on restart; DB rows remain | Store files in S3/Cloudinary (not implemented) |
| 512 MB RAM, 0.1 CPU | Slow first request after wake-up | 1 gunicorn worker is configured; keep `SPACY_ENABLED=false` |
| TiDB free quota | 25 GiB / 250M RU per month | Plenty for a college demo |
| No Render shell on Free | Cannot run `init_db.py` inside the container | Run it from your laptop (step 3) |

The resume **text** and detected skills are stored in `resume_records`, so
history still renders after a restart; only downloading the original file is
affected. The app does not currently offer a file download route.

---

## Alternative databases

| Provider | Free MySQL? | Notes |
|----------|-------------|-------|
| TiDB Cloud Starter | Yes | MySQL-compatible, 25 GiB, TLS required → recommended |
| db4free.net | Yes | Small community MySQL 8, no SLA, good for a throwaway demo |
| Aiven for MySQL | No | Developer plan is $5/month; only PostgreSQL/Kafka/Valkey have a free tier |
| Render Postgres | Yes | PostgreSQL, **not** compatible with this MySQL schema |
| PythonAnywhere Beginner | No | Free plan explicitly excludes MySQL |

If you use another MySQL 8 provider, only `DB_HOST`, `DB_PORT`, `DB_USER`,
`DB_PASSWORD`, `DB_NAME` and `DB_SSL_MODE` change.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Render build fails on `gunicorn` | Ensure the build uses `requirements-deploy.txt`, not `requirements.txt` |
| Deploy is live but every page shows **503 Setup required** | Database not seeded or wrong `DB_*` values; check Render logs and rerun step 3 |
| `SSL is required` / `2026` errors | Set `DB_SSL_MODE=required` (or `verify_ca` with `DB_SSL_CA`) |
| `Unknown database 'skilltrack_ai'` | Run `init_db.py --reset`, or set `DB_NAME` to the database name from the provider console |
| `Access denied for user ...` | Copy the TiDB user exactly (`xxxx.root`) and reset the password in the console |
| Cold start ~1 minute | Expected on Render Free after 15 min of no traffic |
| Login works but charts are empty | Quiz/roadmap data is per student; use a seeded demo student or complete an assessment |
| `Can't connect to MySQL` after months | Free TiDB cluster may be paused; open the console and resume it |
