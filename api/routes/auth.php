<?php
declare(strict_types=1);
require_once __DIR__ . '/../config/database.php';

function auth_json_out(int $status, array $data): void {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data);
    exit;
}

function auth_bearer(): ?string {
    $h = $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';
    if (preg_match('/^Bearer\s+(.+)$/i', $h, $m)) return trim($m[1]);
    return null;
}

function auth_require_user(PDO $pdo, array $allowed_roles = ['admin', 'trader', 'viewer']): array {
    $token = auth_bearer();
    if (!$token) auth_json_out(401, ['error' => 'Geen token']);

    $stmt = $pdo->prepare(
        'SELECT t.user_id, t.expires_at, u.username, u.role, u.is_active, u.is_approved
         FROM prosperia_v2_tokens t
         JOIN prosperia_v2_users u ON u.id = t.user_id
         WHERE t.token = :t LIMIT 1'
    );
    $stmt->execute([':t' => $token]);
    $row = $stmt->fetch();

    if (!$row) auth_json_out(401, ['error' => 'Token ongeldig']);
    if (strtotime($row['expires_at']) < time()) auth_json_out(401, ['error' => 'Token verlopen']);
    if (!(int)$row['is_active']) auth_json_out(403, ['error' => 'Account gedeactiveerd']);
    if (!(int)$row['is_approved']) auth_json_out(403, ['error' => 'Account wacht op goedkeuring']);
    if (!in_array($row['role'], $allowed_roles, true)) auth_json_out(403, ['error' => 'Onvoldoende rechten']);
    return $row;
}

function auth_dispatch(PDO $pdo, array $input): void {
    $action = $input['action'] ?? null;

    switch ($action) {
        case 'login': {
            $username = trim((string)($input['username'] ?? ''));
            $password = (string)($input['password'] ?? '');
            if ($username === '' || $password === '') auth_json_out(400, ['error' => 'username en password verplicht']);

            $stmt = $pdo->prepare(
                'SELECT id, username, password_hash, is_active, is_approved, role
                 FROM prosperia_v2_users WHERE username = :u1 OR email = :u2 LIMIT 1'
            );
            $stmt->execute([':u1' => $username, ':u2' => $username]);
            $user = $stmt->fetch();

            if (!$user || !password_verify($password, $user['password_hash'])) auth_json_out(401, ['error' => 'Ongeldige inloggegevens']);
            if (!(int)$user['is_active']) auth_json_out(403, ['error' => 'Account gedeactiveerd']);
            if (!(int)$user['is_approved']) auth_json_out(403, ['error' => 'Wacht op goedkeuring']);

            $token = bin2hex(random_bytes(32));
            $expiresAt = date('Y-m-d H:i:s', time() + 3600);
            $pdo->prepare('INSERT INTO prosperia_v2_tokens (user_id, token, expires_at, created_at) VALUES (:uid, :tok, :exp, NOW())')
                ->execute([':uid' => $user['id'], ':tok' => $token, ':exp' => $expiresAt]);
            $pdo->prepare('DELETE FROM prosperia_v2_tokens WHERE expires_at < NOW()')->execute();

            auth_json_out(200, [
                'token' => $token,
                'expires_in' => 3600,
                'username' => $user['username'],
                'role' => $user['role'],
            ]);
        }

        case 'register': {
            $u = trim((string)($input['username'] ?? ''));
            $e = trim((string)($input['email'] ?? ''));
            $p = (string)($input['password'] ?? '');
            if (strlen($u) < 3 || strlen($p) < 6 || !filter_var($e, FILTER_VALIDATE_EMAIL)) auth_json_out(400, ['error' => 'Ongeldige invoer']);
            $stmt = $pdo->prepare('SELECT id FROM prosperia_v2_users WHERE username = :u OR email = :e');
            $stmt->execute([':u' => $u, ':e' => $e]);
            if ($stmt->fetch()) auth_json_out(409, ['error' => 'Gebruikersnaam of email bestaat al']);
            $pdo->prepare('INSERT INTO prosperia_v2_users (username, email, password_hash, is_active, is_approved, role, created_at) VALUES (:u, :e, :h, 1, 0, "viewer", NOW())')
                ->execute([':u' => $u, ':e' => $e, ':h' => password_hash($p, PASSWORD_BCRYPT)]);
            auth_json_out(201, ['ok' => true, 'message' => 'Wacht op goedkeuring']);
        }

        case 'logout': {
            $t = auth_bearer();
            if ($t) $pdo->prepare('DELETE FROM prosperia_v2_tokens WHERE token = :t')->execute([':t' => $t]);
            auth_json_out(200, ['ok' => true]);
        }

        case 'me': {
            $r = auth_require_user($pdo);
            auth_json_out(200, ['user_id' => (int)$r['user_id'], 'username' => $r['username'], 'role' => $r['role']]);
        }

        case 'admin_list_users': {
            auth_require_user($pdo, ['admin']);
            $stmt = $pdo->query('SELECT id, username, email, role, is_active, is_approved, created_at FROM prosperia_v2_users ORDER BY created_at DESC');
            auth_json_out(200, ['users' => $stmt->fetchAll()]);
        }

        case 'admin_approve_user': {
            auth_require_user($pdo, ['admin']);
            $id = (int)($input['user_id'] ?? 0);
            if ($id <= 0) auth_json_out(400, ['error' => 'ID ontbreekt']);
            $pdo->prepare('UPDATE prosperia_v2_users SET is_approved = 1 WHERE id = :id')->execute([':id' => $id]);
            auth_json_out(200, ['ok' => true]);
        }

        case 'admin_promote_user': {
            auth_require_user($pdo, ['admin']);
            $id = (int)($input['user_id'] ?? 0);
            $r = (string)($input['role'] ?? '');
            if ($id <= 0 || !in_array($r, ['admin', 'trader', 'viewer'], true)) auth_json_out(400, ['error' => 'Ongeldig']);
            $pdo->prepare('UPDATE prosperia_v2_users SET role = :r WHERE id = :id')->execute([':r' => $r, ':id' => $id]);
            auth_json_out(200, ['ok' => true]);
        }

        case 'admin_deactivate_user': {
            auth_require_user($pdo, ['admin']);
            $id = (int)($input['user_id'] ?? 0);
            if ($id <= 0) auth_json_out(400, ['error' => 'ID ontbreekt']);
            $pdo->prepare('UPDATE prosperia_v2_users SET is_active = 0 WHERE id = :id')->execute([':id' => $id]);
            $pdo->prepare('DELETE FROM prosperia_v2_tokens WHERE user_id = :id')->execute([':id' => $id]);
            auth_json_out(200, ['ok' => true]);
        }

        default:
            auth_json_out(404, ['error' => 'Onbekende auth-actie: ' . $action]);
    }
}
