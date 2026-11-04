-- ============================================================
-- Prosperia V2 — Database Schema
-- Database: dbs16062089 (prefix: prosperia_v2_)
-- ============================================================

-- 1. Users (met rollen en 2FA)
CREATE TABLE IF NOT EXISTS `prosperia_v2_users` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `username` VARCHAR(50) NOT NULL UNIQUE,
  `email` VARCHAR(100) NOT NULL UNIQUE,
  `password_hash` VARCHAR(255) NOT NULL,
  `role` ENUM('admin', 'trader', 'viewer') NOT NULL DEFAULT 'viewer',
  `totp_secret` VARCHAR(255) DEFAULT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Accounts (MT5-wachtwoorden versleuteld, bridge-poorten)
CREATE TABLE IF NOT EXISTS `prosperia_v2_accounts` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT UNSIGNED NOT NULL,
  `name` VARCHAR(100) NOT NULL,
  `mt5_login` VARCHAR(50) NOT NULL,
  `mt5_password_enc` TEXT NOT NULL, -- AES-256 encrypted
  `mt5_server` VARCHAR(100) NOT NULL,
  `bridge_port` SMALLINT UNSIGNED NOT NULL,
  `risk_max_drawdown_pct` DECIMAL(5,2) DEFAULT 5.00,
  `risk_max_trades` INT UNSIGNED DEFAULT 10,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `prosperia_v2_users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 3. Strategies (plugins)
CREATE TABLE IF NOT EXISTS `prosperia_v2_strategies` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `name` VARCHAR(50) NOT NULL UNIQUE, -- module-naam (bv: momentum_btc)
  `display_name` VARCHAR(100) NOT NULL,
  `magic_number` INT UNSIGNED NOT NULL UNIQUE,
  `version` VARCHAR(20) NOT NULL DEFAULT '1.0.0',
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 4. Strategy Configs (Key-Value, GEEN JSON)
CREATE TABLE IF NOT EXISTS `prosperia_v2_strategy_configs` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `strategy_id` INT UNSIGNED NOT NULL,
  `config_key` VARCHAR(100) NOT NULL,
  `config_value` TEXT NOT NULL,
  `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_strategy_key` (`strategy_id`, `config_key`),
  FOREIGN KEY (`strategy_id`) REFERENCES `prosperia_v2_strategies`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 5. Subscriptions (strategie x account x user)
CREATE TABLE IF NOT EXISTS `prosperia_v2_subscriptions` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT UNSIGNED NOT NULL,
  `account_id` INT UNSIGNED NOT NULL,
  `strategy_id` INT UNSIGNED NOT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY `uk_sub` (`account_id`, `strategy_id`),
  FOREIGN KEY (`user_id`) REFERENCES `prosperia_v2_users`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`account_id`) REFERENCES `prosperia_v2_accounts`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`strategy_id`) REFERENCES `prosperia_v2_strategies`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Trades (volledige historie)
CREATE TABLE IF NOT EXISTS `prosperia_v2_trades` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `account_id` INT UNSIGNED NOT NULL,
  `strategy_id` INT UNSIGNED NOT NULL,
  `ticket` BIGINT UNSIGNED NOT NULL,
  `symbol` VARCHAR(20) NOT NULL,
  `direction` ENUM('buy', 'sell') NOT NULL,
  `volume` DECIMAL(10,2) NOT NULL,
  `open_price` DECIMAL(15,5) NOT NULL,
  `close_price` DECIMAL(15,5) DEFAULT NULL,
  `profit` DECIMAL(15,2) DEFAULT NULL,
  `open_time` TIMESTAMP NOT NULL,
  `close_time` TIMESTAMP NULL DEFAULT NULL,
  `status` ENUM('open', 'closed', 'cancelled') NOT NULL DEFAULT 'open',
  FOREIGN KEY (`account_id`) REFERENCES `prosperia_v2_accounts`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`strategy_id`) REFERENCES `prosperia_v2_strategies`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Signals
CREATE TABLE IF NOT EXISTS `prosperia_v2_signals` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `strategy_id` INT UNSIGNED NOT NULL,
  `symbol` VARCHAR(20) NOT NULL,
  `direction` ENUM('buy', 'sell') NOT NULL,
  `price` DECIMAL(15,5) NOT NULL,
  `sl` DECIMAL(15,5) DEFAULT NULL,
  `tp` DECIMAL(15,5) DEFAULT NULL,
  `status` ENUM('pending', 'executed', 'ignored') NOT NULL DEFAULT 'pending',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`strategy_id`) REFERENCES `prosperia_v2_strategies`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 8. Bot Status (heartbeat)
CREATE TABLE IF NOT EXISTS `prosperia_v2_bot_status` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `instance_name` VARCHAR(50) NOT NULL UNIQUE,
  `status` ENUM('running', 'stopped', 'error') NOT NULL DEFAULT 'stopped',
  `last_heartbeat` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `active_strategies` INT UNSIGNED DEFAULT 0,
  `open_positions` INT UNSIGNED DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 9. Audit Log (wie wijzigde wat)
CREATE TABLE IF NOT EXISTS `prosperia_v2_audit_log` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT UNSIGNED DEFAULT NULL,
  `action` VARCHAR(50) NOT NULL,
  `table_name` VARCHAR(50) NOT NULL,
  `record_id` INT UNSIGNED NOT NULL,
  `old_value` TEXT DEFAULT NULL,
  `new_value` TEXT DEFAULT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `prosperia_v2_users`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 10. API Tokens (SHA-256 hash)
CREATE TABLE IF NOT EXISTS `prosperia_v2_api_tokens` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT UNSIGNED NOT NULL,
  `token_name` VARCHAR(50) NOT NULL,
  `token_hash` VARCHAR(64) NOT NULL UNIQUE, -- SHA-256
  `last_used_at` TIMESTAMP NULL DEFAULT NULL,
  `expires_at` TIMESTAMP NULL DEFAULT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `prosperia_v2_users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 11. Password Resets
CREATE TABLE IF NOT EXISTS `prosperia_v2_password_resets` (
  `id` INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `user_id` INT UNSIGNED NOT NULL,
  `token_hash` VARCHAR(64) NOT NULL UNIQUE, -- SHA-256
  `expires_at` TIMESTAMP NOT NULL,
  `used` TINYINT(1) NOT NULL DEFAULT 0,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`user_id`) REFERENCES `prosperia_v2_users`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 12. Strategy Logs
CREATE TABLE IF NOT EXISTS `prosperia_v2_strategy_logs` (
  `id` BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  `strategy_id` INT UNSIGNED NOT NULL,
  `account_id` INT UNSIGNED DEFAULT NULL,
  `level` ENUM('info', 'warning', 'error', 'debug') NOT NULL DEFAULT 'info',
  `message` TEXT NOT NULL,
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (`strategy_id`) REFERENCES `prosperia_v2_strategies`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`account_id`) REFERENCES `prosperia_v2_accounts`(`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
