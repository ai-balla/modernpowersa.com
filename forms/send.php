<?php
/**
 * MPMS request form handler.
 *
 * - Settings (recipient addresses etc.) are read from a config file OUTSIDE the web root:
 *     <hosting account home>/_mpms_private/form-config.php   (see forms/config.sample.php)
 *   If that file is missing, NOTHING is sent and the visitor sees the failure message.
 * - Success is reported only when the mail transport accepted the message.
 * - JSON response for the site's JavaScript; plain redirect for browsers without JavaScript.
 */
declare(strict_types=1);

header('X-Content-Type-Options: nosniff');
header('Cache-Control: no-store');

$lang = (isset($_POST['lang']) && $_POST['lang'] === 'ar') ? 'ar' : 'en';
$wantsJson = isset($_SERVER['HTTP_ACCEPT']) && stripos($_SERVER['HTTP_ACCEPT'], 'application/json') !== false;

function respond(bool $ok, string $lang, bool $json, array $errors = [], int $code = 200): void
{
    if ($json) {
        http_response_code($code);
        header('Content-Type: application/json; charset=utf-8');
        echo json_encode($ok ? ['ok' => true] : ['ok' => false, 'errors' => (object)$errors], JSON_UNESCAPED_UNICODE);
    } else {
        header('Location: /' . $lang . '/contact/' . ($ok ? 'sent' : 'error') . '/', true, 303);
    }
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    http_response_code(405);
    header('Allow: POST');
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['ok' => false]);
    exit;
}

/* ---------- configuration (outside web root) ---------- */
$home = dirname(__DIR__, 2);
$candidates = array_filter([
    getenv('MPMS_FORM_CONFIG') ?: null,
    $home . '/_mpms_private/form-config.php',
    $home . '/_mpms_private/_private/form-config.php',   // location used by the FTP private-bundle upload
]);
$configPath = '';
foreach ($candidates as $c) { if (is_readable($c)) { $configPath = $c; break; } }
$config = $configPath !== '' ? (include $configPath) : null;
if (!is_array($config) || empty($config['to'])) {
    error_log('MPMS form: configuration missing (' . implode(', ', $candidates) . ')');
    respond(false, $lang, $wantsJson, [], 503);
}

/* ---------- same-origin check ---------- */
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
$allowed = $config['allowed_origins'] ?? [];
if ($origin !== '' && $allowed && !in_array($origin, $allowed, true)) {
    respond(false, $lang, $wantsJson, [], 403);
}

/* ---------- spam protection ---------- */
// 1. Honeypot: real visitors never fill this hidden field.
if (!empty($_POST['website'])) {
    // Pretend success to the bot, send nothing.
    respond(true, $lang, $wantsJson);
}
// 2. Time trap: forms submitted within 3 seconds of loading are rejected (only when JS supplied a timestamp).
$ts = isset($_POST['ts']) ? (int)$_POST['ts'] : 0;
if ($ts > 0 && (time() - $ts) < 3) {
    respond(false, $lang, $wantsJson, [], 429);
}
// 3. Rate limit: max N submissions per IP per hour (file-based, no personal data stored beyond a hash).
$limit = (int)($config['rate_limit_per_hour'] ?? 5);
$ipHash = hash('sha256', ($_SERVER['REMOTE_ADDR'] ?? 'unknown') . ($config['salt'] ?? 'mpms'));
$rateDir = $config['rate_dir'] ?? (sys_get_temp_dir() . '/mpms-form-rate');
if (!is_dir($rateDir)) { @mkdir($rateDir, 0700, true); }
$rateFile = $rateDir . '/' . $ipHash;
$hits = [];
if (is_readable($rateFile)) {
    $hits = array_filter(array_map('intval', explode(',', (string)file_get_contents($rateFile))), fn($t) => $t > time() - 3600);
}
if (count($hits) >= $limit) {
    respond(false, $lang, $wantsJson, [], 429);
}

/* ---------- validation ---------- */
function field(string $k, int $max): string
{
    $v = isset($_POST[$k]) && is_string($_POST[$k]) ? trim($_POST[$k]) : '';
    $v = preg_replace('/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/u', '', $v) ?? '';
    return mb_substr($v, 0, $max + 1);
}
$types = ['quote' => 'Quotation request', 'docs' => 'Documents / prequalification', 'general' => 'General enquiry', 'supplier' => 'Supplier / partner'];
$d = [
    'type'     => field('type', 20),
    'service'  => field('service', 80),
    'name'     => field('name', 120),
    'company'  => field('company', 160),
    'email'    => field('email', 160),
    'phone'    => field('phone', 30),
    'location' => field('location', 200),
    'message'  => field('message', 5000),
    'consent'  => field('consent', 3),
];
$errors = [];
if (!isset($types[$d['type']])) { $d['type'] = 'general'; }
if ($d['service'] !== '' && !preg_match('/^[a-z0-9-]{2,80}$/', $d['service'])) { $d['service'] = ''; }
if ($d['name'] === '') { $errors['name'] = 'err_required'; }
if (mb_strlen($d['name']) > 120 || mb_strlen($d['company']) > 160 || mb_strlen($d['location']) > 200) { $errors['name'] = $errors['name'] ?? 'err_long'; }
if ($d['email'] === '') { $errors['email'] = 'err_required'; }
elseif (!filter_var($d['email'], FILTER_VALIDATE_EMAIL) || preg_match('/[\r\n]/', $d['email'])) { $errors['email'] = 'err_email'; }
if ($d['phone'] !== '' && !preg_match('/^\+?[0-9 ()\-]{7,20}$/', $d['phone'])) { $errors['phone'] = 'err_phone'; }
if ($d['message'] === '') { $errors['message'] = 'err_required'; }
elseif (mb_strlen($d['message']) > 5000) { $errors['message'] = 'err_long'; }
if ($d['consent'] !== 'yes') { $errors['consent'] = 'err_consent'; }
if ($errors) {
    respond(false, $lang, $wantsJson, $errors, 422);
}

/* ---------- compose (plain text; no HTML injection possible) ---------- */
$oneLine = fn(string $s): string => str_replace(["\r", "\n"], ' ', $s);
$subject = ($config['subject_prefix'] ?? '[modernpowersa.com]') . ' ' . $types[$d['type']] . ' — ' . $oneLine($d['name'])
    . ($d['company'] !== '' ? ' (' . $oneLine($d['company']) . ')' : '');
$body = implode("\n", [
    'Request type : ' . $types[$d['type']],
    'Service      : ' . ($d['service'] ?: '-'),
    'Name         : ' . $d['name'],
    'Organization : ' . ($d['company'] ?: '-'),
    'Email        : ' . $d['email'],
    'Phone        : ' . ($d['phone'] ?: '-'),
    'Location     : ' . ($d['location'] ?: '-'),
    'Page language: ' . $lang,
    'Received     : ' . gmdate('Y-m-d H:i') . ' UTC',
    str_repeat('-', 60),
    $d['message'],
    str_repeat('-', 60),
    'Sent from the request form on modernpowersa.com. The sender agreed to the privacy notice.',
]);

$from = $config['from'] ?? 'no-reply@modernpowersa.com';
$headers = [
    'From' => 'MPMS Website <' . $from . '>',
    'Reply-To' => $oneLine($d['email']),
    'MIME-Version' => '1.0',
    'Content-Type' => 'text/plain; charset=UTF-8',
    'Content-Transfer-Encoding' => '8bit',
    'X-Mailer' => 'mpms-form',
];
if (!empty($config['cc'])) { $headers['Cc'] = implode(', ', (array)$config['cc']); }
$to = implode(', ', (array)$config['to']);
$encodedSubject = '=?UTF-8?B?' . base64_encode($subject) . '?=';

$transport = $config['transport'] ?? 'mail';
$sent = false;
if ($transport === 'log') {
    // For local testing only: write the message to a file instead of sending it.
    $sent = (bool)file_put_contents($config['log_file'], "To: $to\nSubject: $subject\n" . print_r($headers, true) . "\n$body\n\n=====\n", FILE_APPEND);
} else {
    $sent = mail($to, $encodedSubject, $body, $headers, '-f' . $from);
}

if ($sent) {
    $hits[] = time();
    @file_put_contents($rateFile, implode(',', $hits), LOCK_EX);
    respond(true, $lang, $wantsJson);
}
error_log('MPMS form: mail transport refused the message');
respond(false, $lang, $wantsJson, [], 502);
