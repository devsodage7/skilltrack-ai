# MySQL setup for SkillTrack AI (Windows)

Project: `D:\projects\CODE`
MySQL: 8.0.46, service name **MySQL80**, config `C:\ProgramData\MySQL\MySQL Server 8.0\my.ini`

The app reads credentials from `.env`. Nothing is hardcoded.

---

## Case 1 — You know the root password

1. Open `.env`:

   ```powershell
   cd D:\projects\CODE
   notepad .env
   ```

2. Set the two lines:

   ```
   DB_USER=root
   DB_PASSWORD=your_actual_password
   ```

3. Test the login:

   ```powershell
   & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -e "SELECT VERSION();"
   ```

4. Create the database:

   ```powershell
   .\.venv\Scripts\python.exe database\init_db.py --reset
   ```

---

## Case 2 — You forgot the root password (reset it)

Needs **PowerShell as Administrator** (the service must be stoppable).

1. Open PowerShell as Administrator: Start menu -> type `PowerShell` -> right click -> Run as administrator.

2. Stop the server:

   ```powershell
   net stop MySQL80
   ```

3. Write a one-line reset script (ASCII, no BOM):

   ```powershell
   @'
   ALTER USER 'root'@'localhost' IDENTIFIED BY 'NewRoot@123';
   '@ | Set-Content "C:\Users\devra\mysql_reset.sql" -Encoding ascii
   ```

   Change `NewRoot@123` to whatever you want to keep.

4. Start MySQL once with that script:

   ```powershell
   & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe" --defaults-file="C:\ProgramData\MySQL\MySQL Server 8.0\my.ini" --init-file="C:\Users\devra\mysql_reset.sql" --console
   ```

   Wait until the console prints `ready for connections`, then press **Ctrl + C**.

5. Start the service again:

   ```powershell
   net start MySQL80
   ```

6. Verify and clean up:

   ```powershell
   & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -e "SELECT VERSION();"
   Remove-Item C:\Users\devra\mysql_reset.sql
   ```

7. Put the new password into `.env` (Case 1, step 2) and run `init_db.py --reset`.

If `net stop` says access denied, you are not in an elevated shell.

---

## Case 3 — Recommended: a dedicated app user

Never let a college project run as `root`. After root works:

```sql
CREATE USER IF NOT EXISTS 'skilltrack_user'@'localhost' IDENTIFIED BY 'SkillTrack@2026';
GRANT ALL PRIVILEGES ON skilltrack_ai.* TO 'skilltrack_user'@'localhost';
FLUSH PRIVILEGES;
```

Run it with root:

```powershell
& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p -e "CREATE USER IF NOT EXISTS 'skilltrack_user'@'localhost' IDENTIFIED BY 'SkillTrack@2026'; GRANT ALL PRIVILEGES ON skilltrack_ai.* TO 'skilltrack_user'@'localhost'; FLUSH PRIVILEGES;"
```

Then `.env`:

```
DB_USER=skilltrack_user
DB_PASSWORD=SkillTrack@2026
```

`ALL PRIVILEGES ON skilltrack_ai.*` is limited to this one database, which is
enough for `init_db.py` (it creates, seeds and can reset that database) and it
cannot touch any other schema on the server.

---

## Check whether everything is connected

```powershell
cd D:\projects\CODE
.\.venv\Scripts\python.exe database\init_db.py --check --validate
```

Healthy output ends with:

```
  students                 9
  careers                  8
  ...
Validation: OK
```

Then start the app:

```powershell
.\.venv\Scripts\python.exe run.py
```

Open http://127.0.0.1:5000

| Account | Email | Password |
|---|---|---|
| Admin | admin@skilltrack.local | Admin@123 |
| Student | aarav.patil@skilltrack.local | Student@123 |
| Student | sneha.kulkarni@skilltrack.local | Student@123 |
| Student | rohan.deshmukh@skilltrack.local | Student@123 |

---

## Common errors

| Error | Meaning | Fix |
|---|---|---|
| `1045 Access denied` | wrong password in `.env` | fix `DB_PASSWORD`, restart app |
| `2003 Can't connect` | MySQL service stopped | `net start MySQL80` |
| `1049 Unknown database` | DB not created yet | `python database/init_db.py --reset` |
| `1044 Access denied for user ... to database` | app user lacks grants | run Case 3 `GRANT` again |
| App shows "Setup required" page | it could not connect at startup | check `logs/app.log`, then restart |
