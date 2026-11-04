-- ============================================================
-- Prosperia V2 — Seed Data (Fase 1)
-- ============================================================

-- 1. Admin User (Wachtwoord: Admin123! -> hash moet nog gegenereerd worden in PHP, dit is een placeholder)
INSERT IGNORE INTO `prosperia_v2_users` (`id`, `username`, `email`, `password_hash`, `role`) VALUES
(1, 'admin', 'admin@aertsconnect.nl', '$2y$10$e0MYzXyjpJS7Pd0RVvHwHe1HlCS4bZJ18JuywdBv1lZ1c7B1lZ1c7', 'admin');

-- 2. Test Account (Pepperstone Demo)
INSERT IGNORE INTO `prosperia_v2_accounts` (`id`, `user_id`, `name`, `mt5_login`, `mt5_password_enc`, `mt5_server`, `bridge_port`) VALUES
(1, 1, 'Pepperstone Demo', '12345678', 'ENCRYPTED_PLACEHOLDER', 'Pepperstone-Demo', 8003);

-- 3. Dummy Strategie
INSERT IGNORE INTO `prosperia_v2_strategies` (`id`, `name`, `display_name`, `magic_number`, `version`) VALUES
(1, 'dummy_strategy', 'Dummy Test Strategy', 10001, '0.1.0');

-- 4. Config voor Dummy Strategie
INSERT IGNORE INTO `prosperia_v2_strategy_configs` (`strategy_id`, `config_key`, `config_value`) VALUES
(1, 'symbol', 'EURUSD'),
(1, 'timeframe', 'M15'),
(1, 'risk_percent', '1.0');

-- 5. Subscription (User 1 -> Account 1 -> Strategie 1)
INSERT IGNORE INTO `prosperia_v2_subscriptions` (`user_id`, `account_id`, `strategy_id`) VALUES
(1, 1, 1);

-- 6. Bot Status Initialisatie
INSERT IGNORE INTO `prosperia_v2_bot_status` (`instance_name`, `status`) VALUES
('main_bot', 'stopped');
