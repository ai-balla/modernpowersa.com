<?php
declare(strict_types=1);
define('MPMS_ROOT', dirname(__DIR__));
const MPMS_PREFIX = 'mpms_cms_';
function mpms_private(string $name): string {
    return dirname(__DIR__, 2) . '/_mpms_private/' . $name;
}
function mpms_config(string $name): array {
    $path = mpms_private($name);
    if (!is_readable($path)) { throw new RuntimeException('Private configuration unavailable.'); }
    $value = require $path;
    if (!is_array($value)) { throw new RuntimeException('Invalid private configuration.'); }
    return $value;
}
function mpms_db(): PDO {
    static $db = null;
    if ($db instanceof PDO) { return $db; }
    $c = mpms_config('database-config.php');
    $db = new PDO('mysql:host='.$c['host'].';dbname='.$c['name'].';charset=utf8mb4', $c['username'], $c['password'], [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION, PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES => false,
    ]);
    $marker = mpms_private('cms-schema-v1-'.substr(hash('sha256',$c['name']),0,12));
    if (is_file($marker)) { return $db; }
    $schema = [
      'users' => 'id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY, username VARCHAR(100) NOT NULL UNIQUE, password_hash VARCHAR(255) NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
      'pages' => 'path VARCHAR(190) PRIMARY KEY, draft_json MEDIUMTEXT NOT NULL, live_json MEDIUMTEXT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',
      'posts' => 'id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY, slug VARCHAR(140) NOT NULL UNIQUE, title_en VARCHAR(240) NOT NULL, title_ar VARCHAR(240) NOT NULL, excerpt_en TEXT NOT NULL, excerpt_ar TEXT NOT NULL, body_en MEDIUMTEXT NOT NULL, body_ar MEDIUMTEXT NOT NULL, image VARCHAR(255) NOT NULL DEFAULT \'\', status VARCHAR(20) NOT NULL DEFAULT \'draft\', published_at DATETIME NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP',
      'inquiries' => 'id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, name VARCHAR(120) NOT NULL, email VARCHAR(160) NOT NULL, company VARCHAR(160) NOT NULL DEFAULT \'\', phone VARCHAR(40) NOT NULL DEFAULT \'\', type VARCHAR(40) NOT NULL, service VARCHAR(100) NOT NULL DEFAULT \'\', location VARCHAR(200) NOT NULL DEFAULT \'\', message TEXT NOT NULL, lang VARCHAR(2) NOT NULL, status VARCHAR(20) NOT NULL DEFAULT \'new\', delivery VARCHAR(30) NOT NULL DEFAULT \'pending\', notes TEXT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
      'settings' => 'name VARCHAR(80) PRIMARY KEY, value MEDIUMTEXT NOT NULL',
      'audit' => 'id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY, username VARCHAR(100) NOT NULL, action VARCHAR(100) NOT NULL, detail VARCHAR(240) NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
      'login_attempts' => 'ip_hash CHAR(64) PRIMARY KEY, attempts INT NOT NULL DEFAULT 0, window_start INT NOT NULL',
    ];
    foreach ($schema as $table => $columns) { $db->exec('CREATE TABLE IF NOT EXISTS '.MPMS_PREFIX.$table.' ('.$columns.') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'); }
    if ((int)$db->query('SELECT COUNT(*) FROM '.MPMS_PREFIX.'users')->fetchColumn() === 0) {
        $bootstrap = mpms_config('admin-bootstrap.php');
        $q = $db->prepare('INSERT IGNORE INTO '.MPMS_PREFIX.'users (username,password_hash) VALUES (?,?)');
        $q->execute([$bootstrap['username'], password_hash($bootstrap['password'], PASSWORD_DEFAULT)]);
    }
    @file_put_contents($marker, 'installed', LOCK_EX);
    return $db;
}
function mpms_query(string $sql, array $params = []): PDOStatement {
    $q = mpms_db()->prepare($sql); $q->execute($params); return $q;
}
function mpms_h(?string $s): string { return htmlspecialchars($s ?? '', ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'); }
function mpms_session(): void {
    if (session_status() !== PHP_SESSION_ACTIVE) {
        session_name('mpms_admin');
        session_set_cookie_params(['lifetime'=>0,'path'=>'/','secure'=>true,'httponly'=>true,'samesite'=>'Strict']);
        ini_set('session.use_strict_mode','1');
        session_start();
    }
    if (!empty($_SESSION['user']) && time() - (int)($_SESSION['seen'] ?? 0) > 1800) { $_SESSION = []; session_regenerate_id(true); }
    if (!empty($_SESSION['user'])) { $_SESSION['seen'] = time(); }
}
function mpms_logged_in(): bool { return !empty($_SESSION['user']); }
function mpms_csrf(): string { return $_SESSION['csrf'] ??= bin2hex(random_bytes(32)); }
function mpms_check_csrf(): void {
    if (!is_string($_POST['csrf'] ?? null) || !hash_equals(mpms_csrf(), $_POST['csrf'])) { http_response_code(403); exit('Request expired. Reload and try again.'); }
}
function mpms_log(string $action, string $detail = ''): void {
    mpms_query('INSERT INTO '.MPMS_PREFIX.'audit (username,action,detail) VALUES (?,?,?)', [$_SESSION['user'] ?? 'system', $action, mb_substr($detail,0,240)]);
}
function mpms_setting(string $key, string $default = ''): string {
    static $settings = null;
    if ($settings === null) { $settings = mpms_query('SELECT name,value FROM '.MPMS_PREFIX.'settings')->fetchAll(PDO::FETCH_KEY_PAIR); }
    return $settings[$key] ?? $default;
}
function mpms_page_files(): array {
    $pages = [];
    foreach (['en','ar'] as $lang) {
        $it = new RecursiveIteratorIterator(new RecursiveDirectoryIterator(MPMS_ROOT.'/'.$lang, FilesystemIterator::SKIP_DOTS));
        foreach ($it as $file) {
            if ($file->getFilename() !== 'index.html') { continue; }
            // Derive paths exclusively from the public language directories.
            $path = $lang.'/'.str_replace('\\','/',substr($file->getPathname(),strlen(MPMS_ROOT.'/'.$lang)+1));
            $slug = '/'.substr($path,0,-strlen('index.html'));
            if (preg_match('~/contact/(sent|error)/$~',$slug)) { continue; }
            $pages[$slug] = $file->getPathname();
        }
    }
    ksort($pages); return $pages;
}
function mpms_dom(string $html): DOMDocument {
    $dom = new DOMDocument('1.0','UTF-8');
    $previous = libxml_use_internal_errors(true);
    $dom->loadHTML('<?xml encoding="UTF-8">'.$html, LIBXML_NONET | LIBXML_NOERROR | LIBXML_NOWARNING);
    foreach (iterator_to_array($dom->childNodes) as $node) { if ($node->nodeType === XML_PI_NODE) { $dom->removeChild($node); } }
    libxml_clear_errors(); libxml_use_internal_errors($previous); return $dom;
}
function mpms_fields(DOMDocument $dom): array {
    $xpath = new DOMXPath($dom); $fields = [];
    foreach ($xpath->query('//main//text()[normalize-space(.) != "" and not(ancestor::script) and not(ancestor::style)] | //head/title/text() | //head/meta[@name="description"]/@content') as $node) {
        if ($node->parentNode instanceof DOMElement && in_array($node->parentNode->tagName,['option','button','label'],true)) { continue; }
        // Form copy and user-input defaults remain controlled by the bilingual form implementation.
        if ($xpath->query('ancestor::form',$node)->length) { continue; }
        $original = $node->nodeValue;
        $path = $node->getNodePath();
        $key = hash('sha256',$path."\0".$original);
        $fields[$key] = ['xpath'=>$path,'original'=>$original,'label'=>$node->parentNode->nodeName,'value'=>trim($original)];
    }
    return $fields;
}
function mpms_apply(DOMDocument $dom, array $values): int {
    $xpath = new DOMXPath($dom); $applied = 0;
    foreach (mpms_fields($dom) as $key => $field) {
        if (!array_key_exists($key,$values) || !is_string($values[$key])) { continue; }
        $node = $xpath->query($field['xpath'])->item(0);
        if ($node) {
            preg_match('/^\s*/u',$field['original'],$leading);preg_match('/\s*$/u',$field['original'],$trailing);
            $node->nodeValue = ($leading[0]??'').$values[$key].($trailing[0]??''); $applied++;
        }
    }
    return $applied;
}
function mpms_inquiry(array $d, string $lang): int {
    mpms_query('INSERT INTO '.MPMS_PREFIX.'inquiries (name,email,company,phone,type,service,location,message,lang) VALUES (?,?,?,?,?,?,?,?,?)', [
        $d['name'],$d['email'],$d['company'],$d['phone'],$d['type'],$d['service'],$d['location'],$d['message'],$lang,
    ]);
    return (int)mpms_db()->lastInsertId();
}
function mpms_markdown(string $text): string {
    $output=''; $paragraph=[];
    $flush = static function () use (&$output,&$paragraph): void { if ($paragraph) { $output.='<p>'.implode('<br>',array_map('mpms_h',$paragraph)).'</p>'; $paragraph=[]; } };
    foreach (preg_split('/\R/u',$text) as $line) {
        if (trim($line)==='') { $flush(); continue; }
        if (preg_match('/^(#{1,3})\s+(.+)$/u',$line,$m)) { $flush(); $level=strlen($m[1])+1; $output.='<h'.$level.'>'.mpms_h($m[2]).'</h'.$level.'>'; }
        else { $paragraph[]=$line; }
    }
    $flush(); return $output;
}
