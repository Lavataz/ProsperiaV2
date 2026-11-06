-- Voeg rollen en goedkeurings-status toe aan users
ALTER TABLE prosperia_v2_users 
  ADD COLUMN role ENUM('admin', 'user') NOT NULL DEFAULT 'user',
  ADD COLUMN is_approved TINYINT(1) NOT NULL DEFAULT 0;

-- Zet de bot-user en admin op admin/approved
UPDATE prosperia_v2_users SET role = 'admin', is_approved = 1 WHERE username = 'Lavataz';
-- (vervang 'bot@prosperia.local' door jouw eigen admin-username)

-- Voeg goedkeuring toe aan accounts (voor het geval je account-aanvragen wilt goedkeuren)
ALTER TABLE prosperia_v2_accounts
  ADD COLUMN is_approved TINYINT(1) NOT NULL DEFAULT 1;
