-- Run as root in MariaDB after installation (adjust passwords and user names)
-- Remove anonymous users / test DB / remote root login
DELETE FROM mysql.user WHERE User='';
DROP DATABASE IF EXISTS test;
DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';
UPDATE mysql.user SET Password=PASSWORD('CHANGE_ROOT_PASSWORD_NOW') WHERE User='root';
DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost','127.0.0.1','::1');
FLUSH PRIVILEGES;

-- App DB + least privilege user
CREATE DATABASE IF NOT EXISTS secure_login CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'securelogin_app'@'127.0.0.1' IDENTIFIED BY 'CHANGE_APP_DB_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, ALTER, INDEX ON secure_login.* TO 'securelogin_app'@'127.0.0.1';
FLUSH PRIVILEGES;
