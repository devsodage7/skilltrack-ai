-- =====================================================================
--  SkillTrack AI  -  database/create_app_user.sql
--
--  Run this ONCE in MySQL Workbench while logged in as root.
--  It creates a limited account that can only touch skilltrack_ai.
--
--  How to run:
--    1. Open MySQL Workbench, click the "Local instance MySQL80" tile.
--    2. Paste this whole file into the query editor.
--    3. Press Ctrl + Shift + Enter (execute all).
-- =====================================================================

CREATE USER IF NOT EXISTS 'skilltrack_user'@'localhost'
    IDENTIFIED BY 'SkillTrack@2026';

-- Make sure the password is exactly this value even if the user existed
ALTER USER 'skilltrack_user'@'localhost'
    IDENTIFIED BY 'SkillTrack@2026';

-- Only this project database, nothing else on the server
GRANT ALL PRIVILEGES ON skilltrack_ai.* TO 'skilltrack_user'@'localhost';

FLUSH PRIVILEGES;

-- Confirmation (should return one row)
SELECT user, host, plugin FROM mysql.user WHERE user = 'skilltrack_user';
