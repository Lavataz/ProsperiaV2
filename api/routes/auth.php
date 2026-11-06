<?php
// api/routes/auth.php — login, refresh, logout, me

declare(strict_types=1);

require_once __DIR__ . '/../config/database.php';

function json_out(int $status, array $data): void {
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($data);
    exit;
}

function bearer_token(): ?string {
    $h = $_SERVER['HTTP_AUTHORIZATION'] ?? $_SERVER['REDIRECT_HTTP_AUTHORIZATION'] ?? '';
    if (preg_match('/^Bearer\s+(.+)$/i', $h, $m)) {
        return trim($m[1]);
    }
    return null;
}

function require_auth(PDO $pdo): array {
    $token = bearer_token();
    if (!$token) {
        json_out(401, ['error' => 'Geen token']);
    }

    $stmt = $pdo->prepare(
        'SELECT t.user_id, t.expires_at, u.username, u.is_active
         FROM prosperia_v2_tokens t
         JOIN prosperia_v2_users u ON u.id = t.user_id
         WHERE t.token = :t LIMIT 1'
    );
    $stmt->execute([':t' => $token]);
    $row = $stmt->fetch();

    if (!$row) {
        json_out(401, ['error' => 'Token ongeldig']);
    }
    if (strtotime($row['expires_at']) < time()) {
        json_out(401, ['error' => 'Token verlopen']);
    }
    if (!(int)$row['is_active']) {
        json_out(403, ['error' => 'Account gedeactiveerd']);
    }
    return $row;
}

// ---- Acties --------------------------------------------------------------
$action = $input['action'] ?? null;
$pdo = getPDO();

switch ($action) {

    case 'login': {
        $username = trim((string)($input['username'] ?? ''));
        $password = (string)($input['password'] ?? '');

        if ($username === '' || $password === '') {
            json_out(400, ['error' => 'username en password zijn verplicht']);
        }

        // username of email
        $stmt = $pdo->prepare(
            'SELECT id, username, password_hash, is_active
             FROM prosperia_v2_users
             WHERE username = :u OR email = :u LIMIT 1'
        );
        $stmt->execute([':u' => $username]);
        $user = $stmt->fetch();

        if (!$user || !password_verify($password, $user['password_hash'])) {
            // Bewust generieke fout (geen user-enumeratie)
            json_out(401, ['error' => 'Ongeldige inloggegevens']);
        }
        if (!(int)$user['is_active']) {
            json_out(403, ['error' => 'Account gedeactiveerd']);
        }

        // Nieuw token genereren
        $token = bin2hex(random_bytes(32));   // 64 hex chars
        $expiresAt = (new DateTime('+1 hour'))->format('Y-m-d H:i:s');

        $ins = $pdo->prepare(
            'INSERT INTO prosperia_v2_tokens (user_id, token, expires_at, created_at)
             VALUES (:uid, :tok, :exp, NOW())'
        );
        $ins->execute([':uid' => $user['id'], ':tok' => $token, ':exp' => $expiresAt]);

        // Oude tokens opruimen
        $pdo->prepare('DELETE FROM prosperia_v2_tokens WHERE expires_at < NOW()')->execute();

        json_out(200, [
            'token'      => $token,
            'expires_in' => 3600,
            'username'   => $user['username'],
        ]);
    }

    case 'refresh': {
        $row = require_auth($pdo);
        $newToken = bin2hex(random_bytes(32));
        $expiresAt = (new DateTime('+1 hour'))->format('Y-m-d H:i:s');

        $pdo->prepare('DELETE FROM prosperia_v2_tokens WHERE user_id = :uid')
            ->execute([':uid' => $row['user_id']]);
        $pdo->prepare(
            'INSERT INTO prosperia_v2_tokens (user_id, token, expires_at, created_at)
             VALUES (:uid, :tok, :exp, NOW())'
        )->execute([':uid' => $row['user_id'], ':tok' => $newToken, ':exp' => $expiresAt]);

        json_out(200, ['token' => $newToken, 'expires_in' => 3600]);
    }

    case 'logout': {
        $token = bearer_token();
        if ($token) {
            $pdo->prepare('DELETE FROM prosperia_v2_tokens WHERE token = :t')
                ->execute([':t' => $token]);
        }
        json_out(200, ['ok' => true]);
    }

    case 'me': {
        $row = require_auth($pdo);
        json_out(200, [
            'user_id'  => (int)$row['user_id'],
            'username' => $row['username'],
        ]);
    }

    default:
        json_out(404, ['error' => 'Onbekende auth-actie']);
}
