-- Create a dedicated DB user for the web app with least-privilege grants.
-- Run manually on the target MariaDB server as an admin user, e.g.:
--   mysql -u root -p < scripts/create-db-user.sql
-- Replace 'CHANGE_ME' with a real generated password before running,
-- then put the same password in backend/.env as DB_PASSWORD (never commit it).

CREATE USER IF NOT EXISTS 'radius_web'@'localhost' IDENTIFIED BY 'CHANGE_ME';

GRANT SELECT, INSERT, UPDATE, DELETE ON radius.radcheck      TO 'radius_web'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON radius.radreply      TO 'radius_web'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON radius.radusergroup  TO 'radius_web'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON radius.radgroupcheck TO 'radius_web'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON radius.radgroupreply TO 'radius_web'@'localhost';
GRANT SELECT, INSERT, UPDATE, DELETE ON radius.nas           TO 'radius_web'@'localhost';
GRANT SELECT                         ON radius.radacct       TO 'radius_web'@'localhost';
GRANT SELECT                         ON radius.radpostauth   TO 'radius_web'@'localhost';

-- app_* tables: Alembic needs CREATE/ALTER/DROP to manage migrations.
-- If MariaDB refuses to grant on tables that don't exist yet, run the first
-- `alembic upgrade head` as a privileged user, then re-run the grants below.
GRANT ALL PRIVILEGES ON radius.app_admin_users         TO 'radius_web'@'localhost';
GRANT ALL PRIVILEGES ON radius.app_refresh_tokens      TO 'radius_web'@'localhost';
GRANT ALL PRIVILEGES ON radius.app_audit_log           TO 'radius_web'@'localhost';
GRANT ALL PRIVILEGES ON radius.app_bandwidth_profiles  TO 'radius_web'@'localhost';
GRANT ALL PRIVILEGES ON radius.app_profile_assignments TO 'radius_web'@'localhost';
-- Alembic's own version table.
GRANT ALL PRIVILEGES ON radius.alembic_version         TO 'radius_web'@'localhost';

FLUSH PRIVILEGES;
