<?php
declare(strict_types=1);
require dirname(__DIR__).'/cms/core.php';
header('Cache-Control: no-store'); header('X-Robots-Tag: noindex, nofollow');
header('X-Content-Type-Options: nosniff');
mpms_session();
$view = is_string($_GET['view'] ?? null) ? $_GET['view'] : 'dashboard';
$message = ''; $error = '';
try { mpms_db(); } catch (Throwable $e) { error_log('MPMS CMS database unavailable: '.$e->getCode()); http_response_code(503); exit('Website management is temporarily unavailable. Please contact the website administrator.'); }
function redirect_admin(string $view): never { header('Location: /admin/?view='.$view,true,303); exit; }
function field(string $name, string $label, string $value = '', bool $area = false, string $extra = ''): void {
    echo '<label class="field">'.mpms_h($label);
    if ($area) { echo '<textarea name="'.mpms_h($name).'" '.$extra.'>'.mpms_h($value).'</textarea>'; }
    else { echo '<input name="'.mpms_h($name).'" value="'.mpms_h($value).'" '.$extra.'>'; }
    echo '</label>';
}
function csrf_field(): void { echo '<input type="hidden" name="csrf" value="'.mpms_h(mpms_csrf()).'">'; }
function post_value(string $name, int $max = 20000): string {
    return mb_substr(is_string($_POST[$name] ?? null) ? trim($_POST[$name]) : '',0,$max);
}
if ($_SERVER['REQUEST_METHOD']==='POST') {
    mpms_check_csrf();
    $action=post_value('action',40);
    try {
        if ($action==='login') {
            $hash=hash('sha256',($_SERVER['REMOTE_ADDR']??'unknown').'mpms-admin-login'); $now=time();
            mpms_query('INSERT IGNORE INTO '.MPMS_PREFIX.'login_attempts (ip_hash,attempts,window_start) VALUES (?,0,?)',[$hash,$now]);
            $attempt=mpms_query('SELECT * FROM '.MPMS_PREFIX.'login_attempts WHERE ip_hash=?',[$hash])->fetch();
            if ($now-(int)$attempt['window_start']>900) { mpms_query('UPDATE '.MPMS_PREFIX.'login_attempts SET attempts=0,window_start=? WHERE ip_hash=?',[$now,$hash]); $attempt['attempts']=0; }
            if ((int)$attempt['attempts']>=8) { throw new RuntimeException('Too many attempts. Please try again in 15 minutes.'); }
            mpms_query('UPDATE '.MPMS_PREFIX.'login_attempts SET attempts=attempts+1 WHERE ip_hash=?',[$hash]);
            $user=mpms_query('SELECT * FROM '.MPMS_PREFIX.'users WHERE username=?',[post_value('username',100)])->fetch();
            $password=is_string($_POST['password']??null)?$_POST['password']:'';
            if (!$user || !password_verify($password,$user['password_hash'])) { throw new RuntimeException('The username or password is incorrect.'); }
            session_regenerate_id(true); $_SESSION['user']=$user['username']; $_SESSION['user_id']=(int)$user['id']; $_SESSION['seen']=time(); $_SESSION['csrf']=bin2hex(random_bytes(32));
            mpms_query('DELETE FROM '.MPMS_PREFIX.'login_attempts WHERE ip_hash=?',[$hash]); mpms_log('login'); redirect_admin('dashboard');
        }
        if (!mpms_logged_in()) { throw new RuntimeException('Please sign in.'); }
        if ($action==='export') {
            $backup=['exported_at'=>gmdate('c'),'format'=>'mpms-cms-v1'];
            foreach(['pages','posts','inquiries','settings'] as $table){$backup[$table]=mpms_query('SELECT * FROM '.MPMS_PREFIX.$table)->fetchAll();}
            mpms_log('content_exported');header('Content-Type: application/json; charset=utf-8');header('Content-Disposition: attachment; filename="mpms-content-'.gmdate('Y-m-d').'.json"');
            echo json_encode($backup,JSON_PRETTY_PRINT|JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);exit;
        }
        if ($action==='logout') { mpms_log('logout'); $_SESSION=[]; session_destroy(); redirect_admin('dashboard'); }
        if ($action==='save_page') {
            $path=post_value('path',190);$pages=mpms_page_files();
            if (!isset($pages[$path])) { throw new RuntimeException('Unknown page.'); }
            $fields=mpms_fields(mpms_dom((string)file_get_contents($pages[$path]))); $edits=[];
            foreach ($fields as $key=>$f) { $value=post_value('f_'.$key,10000); if ($value!==$f['value']) { $edits[$key]=$value; } }
            $json=json_encode($edits,JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);
            $mode=post_value('mode',20);
            mpms_query('INSERT INTO '.MPMS_PREFIX.'pages (path,draft_json) VALUES (?,?) ON DUPLICATE KEY UPDATE draft_json=VALUES(draft_json)',[$path,$json]);
            if ($mode==='publish') { mpms_query('UPDATE '.MPMS_PREFIX.'pages SET live_json=? WHERE path=?',[$json,$path]); }
            if ($mode==='unpublish') { mpms_query('UPDATE '.MPMS_PREFIX.'pages SET live_json=NULL WHERE path=?',[$path]); }
            mpms_log('page_'.$mode,$path); $message=$mode==='publish'?'Page published.':($mode==='unpublish'?'Original page restored. Draft retained.':'Draft saved.');
        }
        if ($action==='save_post') {
            $id=(int)($_POST['id']??0);$slug=post_value('slug',140);
            if (!preg_match('/^[a-z0-9]+(?:-[a-z0-9]+)*$/',$slug)) { throw new RuntimeException('Use a URL slug such as marine-maintenance-update.'); }
            $values=[];
            foreach (['title_en','title_ar','excerpt_en','excerpt_ar','body_en','body_ar'] as $key) { $values[$key]=post_value($key,str_starts_with($key,'title')?240:100000); }
            $image=post_value('image',255);
            if ($image!=='' && (!preg_match('~^/assets/(?:uploads|img)/[a-zA-Z0-9/_.-]+\.(?:jpg|jpeg|png|webp)$~',$image)||str_contains($image,'..')||!is_file(MPMS_ROOT.$image))) { throw new RuntimeException('Select an existing image from the media library.'); }
            $status=post_value('status')==='published'?'published':'draft';
            if ($status==='published' && (!$values['title_en']||!$values['title_ar']||!$values['body_en']||!$values['body_ar'])) { throw new RuntimeException('Both Arabic and English titles and articles are required before publishing.'); }
            $params=array_merge([$slug],array_values($values),[$image,$status]);
            $publishedAt=$status==='published'?gmdate('Y-m-d H:i:s'):null;
            if ($id) { mpms_query('UPDATE '.MPMS_PREFIX.'posts SET slug=?,title_en=?,title_ar=?,excerpt_en=?,excerpt_ar=?,body_en=?,body_ar=?,image=?,status=?,published_at=COALESCE(published_at,?) WHERE id=?',array_merge($params,[$publishedAt,$id])); }
            else { mpms_query('INSERT INTO '.MPMS_PREFIX.'posts (slug,title_en,title_ar,excerpt_en,excerpt_ar,body_en,body_ar,image,status,published_at) VALUES (?,?,?,?,?,?,?,?,?,?)',array_merge($params,[$publishedAt])); }
            mpms_log('blog_'.$status,$slug);$message='Article saved.';$view='blog';
        }
        if ($action==='inquiry') {
            $status=post_value('status',20);if (!in_array($status,['new','in_progress','closed'],true)) { throw new RuntimeException('Invalid status.'); }
            mpms_query('UPDATE '.MPMS_PREFIX.'inquiries SET status=?,notes=? WHERE id=?',[$status,post_value('notes',10000),(int)$_POST['id']]);mpms_log('inquiry_updated',(string)(int)$_POST['id']);$message='Contact request updated.';
        }
        if ($action==='save_settings') {
            $email=post_value('contact_email',160);$phone=post_value('contact_phone',40);
            if (!filter_var($email,FILTER_VALIDATE_EMAIL)) { throw new RuntimeException('Enter a valid public contact email.'); }
            if (!preg_match('/^\+?[0-9 ()-]{7,30}$/',$phone)) { throw new RuntimeException('Enter a valid contact phone.'); }
            foreach (['contact_email','contact_phone','address_en','address_ar'] as $key) {
                mpms_query('INSERT INTO '.MPMS_PREFIX.'settings (name,value) VALUES (?,?) ON DUPLICATE KEY UPDATE value=VALUES(value)',[$key,post_value($key,2000)]);
            }
            mpms_log('settings_updated');$message='Public contact settings saved. Email delivery recipient remains the private form setting.';
        }
        if ($action==='upload') {
            $file=$_FILES['image']??null;
            if (!$file || $file['error']!==UPLOAD_ERR_OK || $file['size']>5*1024*1024) { throw new RuntimeException('Choose a JPG, PNG or WebP image smaller than 5 MB.'); }
            $mime=(new finfo(FILEINFO_MIME_TYPE))->file($file['tmp_name']);$types=['image/jpeg'=>'jpg','image/png'=>'png','image/webp'=>'webp'];
            if (!isset($types[$mime]) || !getimagesize($file['tmp_name'])) { throw new RuntimeException('The file is not a supported image.'); }
            $info=getimagesize($file['tmp_name']);if ($info[0]*$info[1]>40000000) { throw new RuntimeException('Image dimensions are too large.'); }
            $dir=MPMS_ROOT.'/assets/uploads';if (!is_dir($dir)) { mkdir($dir,0755,true); }
            $name=bin2hex(random_bytes(16)).'.'.$types[$mime];
            if (!move_uploaded_file($file['tmp_name'],$dir.'/'.$name)) { throw new RuntimeException('Upload could not be saved.'); }
            mpms_log('image_uploaded',$name);$message='Image uploaded: /assets/uploads/'.$name;
        }
        if ($action==='password') {
            $user=mpms_query('SELECT * FROM '.MPMS_PREFIX.'users WHERE id=?',[$_SESSION['user_id']])->fetch();
            $current=is_string($_POST['current']??null)?$_POST['current']:'';$new=is_string($_POST['new']??null)?$_POST['new']:'';
            if (!password_verify($current,$user['password_hash'])) { throw new RuntimeException('Current password is incorrect.'); }
            if (strlen($new)<14 || $new!==($_POST['confirm']??'')) { throw new RuntimeException('Use at least 14 characters and matching confirmation.'); }
            mpms_query('UPDATE '.MPMS_PREFIX.'users SET password_hash=? WHERE id=?',[password_hash($new,PASSWORD_DEFAULT),$_SESSION['user_id']]);
            session_regenerate_id(true);mpms_log('password_changed');$message='Admin password updated.';
        }
    } catch (PDOException $e) { error_log('MPMS admin operation failed: '.$e->getCode()); @file_put_contents(mpms_private('admin-errors.log'),gmdate('c').' '.$e->getMessage()."\n",FILE_APPEND|LOCK_EX); $error='This change could not be saved. The URL slug may already be in use.'; }
    catch (RuntimeException $e) { $error=$e->getMessage(); }
}
?><!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MPMS · Website management</title><link rel="icon" href="/assets/img/favicon-32.png"><link rel="stylesheet" href="/admin/admin.css"></head><body>
<?php if (!mpms_logged_in()): ?>
<main class="login"><div class="login-card"><img src="/assets/img/logo.png" width="220" alt="MPMS"><p class="eyebrow">Website management · إدارة الموقع</p><h1>Welcome back</h1><p>Sign in to manage MPMS content and enquiries.</p><?php if($error):?><p class="notice error"><?=mpms_h($error)?></p><?php endif;?><form method="post"><?php csrf_field();?><input type="hidden" name="action" value="login"><?php field('username','Username · اسم المستخدم','',false,'required autocomplete="username"');field('password','Password · كلمة المرور','',false,'type="password" required autocomplete="current-password"');?><button>Sign in · تسجيل الدخول</button></form><a href="/">Return to website</a></div></main>
<?php else:
$nav=['dashboard'=>'Overview / نظرة عامة','pages'=>'Pages / الصفحات','blog'=>'Blog / المدونة','inquiries'=>'Contacts / الطلبات','media'=>'Media / الصور','settings'=>'Settings / الإعدادات','account'=>'Account / الحساب'];
if(!isset($nav[$view])){$view='dashboard';}
?><aside><a class="admin-brand" href="/admin/"><img src="/assets/img/logo-white.png" width="180" alt="MPMS"></a><p>CONTENT WORKSPACE</p><nav><?php foreach($nav as $k=>$label):?><a class="<?=$view===$k?'active':''?>" href="/admin/?view=<?=$k?>"><?=mpms_h($label)?></a><?php endforeach;?></nav><a class="live-link" href="/en/" target="_blank" rel="noopener">View website ↗</a><form method="post"><?php csrf_field();?><input type="hidden" name="action" value="logout"><button class="logout">Sign out</button></form></aside>
<main class="workspace"><header><div><p class="eyebrow">MODERN POWER MARINE SERVICES</p><h1><?=mpms_h(explode(' / ',$nav[$view])[0])?></h1></div><span class="user"><?=mpms_h($_SESSION['user'])?></span></header>
<?php if($message):?><p class="notice"><?=mpms_h($message)?></p><?php endif;?><?php if($error):?><p class="notice error"><?=mpms_h($error)?></p><?php endif;?>
<?php if($view==='dashboard'): $count=fn($table)=>(int)mpms_query('SELECT COUNT(*) FROM '.MPMS_PREFIX.$table)->fetchColumn();?>
<div class="stats"><?php foreach(['Editable pages'=>count(mpms_page_files()),'Blog articles'=>$count('posts'),'Contact requests'=>$count('inquiries'),'New requests'=>(int)mpms_query('SELECT COUNT(*) FROM '.MPMS_PREFIX.'inquiries WHERE status=\'new\'')->fetchColumn()] as $label=>$number):?><section><p><?=mpms_h($label)?></p><strong><?=$number?></strong></section><?php endforeach;?></div><section class="panel"><h2>A clear place to keep MPMS up to date</h2><p>Edit Arabic and English page text, publish company updates, and follow up on website enquiries. Draft changes stay private until you publish them.</p><div class="actions"><a class="button" href="?view=pages">Edit website pages</a><a class="button secondary" href="?view=blog&edit=new">Write an article</a></div></section><section class="panel"><h2>Recent activity</h2><?php foreach(mpms_query('SELECT * FROM '.MPMS_PREFIX.'audit ORDER BY id DESC LIMIT 12') as $row):?><p class="activity"><span><?=mpms_h($row['action'].' '.$row['detail'])?></span><small><?=mpms_h($row['created_at'])?></small></p><?php endforeach;?></section>
<?php elseif($view==='pages'):
$pages=mpms_page_files();$path=is_string($_GET['path']??null)?$_GET['path']:'';
if(isset($pages[$path])):
$dom=mpms_dom((string)file_get_contents($pages[$path]));$fields=mpms_fields($dom);$record=mpms_query('SELECT * FROM '.MPMS_PREFIX.'pages WHERE path=?',[$path])->fetch();$edits=$record?json_decode($record['draft_json'],true):[];
?><section class="panel"><div class="section-head"><div><h2><?=mpms_h($path)?></h2><p>Edit text while retaining the existing page design. Saved drafts are private.</p></div><a href="<?=mpms_h($path)?>?cms_preview=1" target="_blank" rel="noopener">Preview draft ↗</a></div><form method="post"><?php csrf_field();?><input type="hidden" name="action" value="save_page"><input type="hidden" name="path" value="<?=mpms_h($path)?>"><div class="page-fields" dir="<?=str_starts_with($path,'/ar/')?'rtl':'ltr'?>"><?php foreach($fields as $key=>$f):field('f_'.$key,strtoupper($f['label']),$edits[$key]??$f['value'],true,'maxlength="10000" rows="2"');endforeach;?></div><div class="sticky-actions"><button name="mode" value="draft" class="secondary">Save draft</button><button name="mode" value="publish">Publish changes</button><button name="mode" value="unpublish" class="quiet">Restore original page</button></div></form></section>
<?php else:?><section class="panel"><h2>Arabic and English content</h2><p>Choose a page to edit. Services, projects, quality credentials and company information are included.</p><div class="page-list"><?php foreach($pages as $path=>$file):?><a href="?view=pages&path=<?=rawurlencode($path)?>"><span><?=mpms_h($path)?></span><span>Edit →</span></a><?php endforeach;?></div></section><?php endif;?>
<?php elseif($view==='blog'):
$editing=$_GET['edit']??null;
if($editing!==null):$post=$editing==='new'?[]:(mpms_query('SELECT * FROM '.MPMS_PREFIX.'posts WHERE id=?',[(int)$editing])->fetch()?:[]);
?><section class="panel"><h2><?=$post?'Edit article':'New article'?></h2><form method="post"><?php csrf_field();?><input type="hidden" name="action" value="save_post"><input type="hidden" name="id" value="<?=(int)($post['id']??0)?>"><?php field('slug','URL slug',$post['slug']??'',false,'required pattern="[a-z0-9]+(-[a-z0-9]+)*" placeholder="company-update"');?><div class="language-grid"><?php foreach(['en'=>'English','ar'=>'العربية'] as $lang=>$label):?><div dir="<?=$lang==='ar'?'rtl':'ltr'?>"><h3><?=$label?></h3><?php field('title_'.$lang,'Title / العنوان',$post['title_'.$lang]??'',false,'maxlength="240"');field('excerpt_'.$lang,'Summary / الملخص',$post['excerpt_'.$lang]??'',true);field('body_'.$lang,'Article / المقال',$post['body_'.$lang]??'',true,'rows="16"');?></div><?php endforeach;?></div><p class="muted">Write plain text. Start a line with ## for a section heading. Blank lines separate paragraphs.</p><?php field('image','Cover image path (optional)',$post['image']??'',false,'placeholder="/assets/uploads/…"');?><label class="field">Publication status<select name="status"><option value="draft">Draft</option><option value="published" <?=($post['status']??'')==='published'?'selected':''?>>Published</option></select></label><button>Save article</button></form></section>
<?php else:?><section class="panel"><div class="section-head"><h2>Company updates</h2><a class="button" href="?view=blog&edit=new">New article</a></div><p><a href="/en/blog/" target="_blank" rel="noopener">View public blog ↗</a></p><div class="table-wrap"><table><tr><th>Article</th><th>Status</th><th>Updated</th><th></th></tr><?php foreach(mpms_query('SELECT * FROM '.MPMS_PREFIX.'posts ORDER BY updated_at DESC') as $row):?><tr><td><?=mpms_h($row['title_en']?:$row['slug'])?></td><td><span class="badge"><?=mpms_h($row['status'])?></span></td><td><?=mpms_h($row['updated_at'])?></td><td><a href="?view=blog&edit=<?=$row['id']?>">Edit</a></td></tr><?php endforeach;?></table></div></section><?php endif;?>
<?php elseif($view==='inquiries'):
$id=(int)($_GET['id']??0);$row=$id?mpms_query('SELECT * FROM '.MPMS_PREFIX.'inquiries WHERE id=?',[$id])->fetch():null;
if($row):?><section class="panel"><h2><?=mpms_h($row['name'])?></h2><p><?=mpms_h($row['company'].' · '.$row['created_at'])?></p><p><a href="mailto:<?=mpms_h($row['email'])?>"><?=mpms_h($row['email'])?></a> · <?=mpms_h($row['phone'])?></p><dl><dt>Request</dt><dd><?=mpms_h($row['type'].' / '.$row['service'])?></dd><dt>Location</dt><dd><?=mpms_h($row['location'])?></dd><dt>Email delivery</dt><dd><?=mpms_h($row['delivery'])?></dd></dl><blockquote dir="auto"><?=nl2br(mpms_h($row['message']))?></blockquote><form method="post"><?php csrf_field();?><input type="hidden" name="action" value="inquiry"><input type="hidden" name="id" value="<?=$id?>"><label class="field">Follow-up status<select name="status"><?php foreach(['new','in_progress','closed'] as $s):?><option value="<?=$s?>" <?=$row['status']===$s?'selected':''?>><?=mpms_h(ucwords(str_replace('_',' ',$s)))?></option><?php endforeach;?></select></label><?php field('notes','Internal notes',$row['notes']??'',true);?><button>Save follow-up</button></form></section>
<?php else:?><section class="panel"><h2>Website contact requests</h2><p>Requests submitted after the backend is installed appear here. Existing email history is not imported.</p><div class="table-wrap"><table><tr><th>Contact</th><th>Request</th><th>Status</th><th>Received</th></tr><?php foreach(mpms_query('SELECT * FROM '.MPMS_PREFIX.'inquiries ORDER BY id DESC LIMIT 200') as $row):?><tr><td><a href="?view=inquiries&id=<?=$row['id']?>"><?=mpms_h($row['name'])?></a><br><small><?=mpms_h($row['company'])?></small></td><td><?=mpms_h($row['type'])?></td><td><span class="badge"><?=mpms_h($row['status'])?></span></td><td><?=mpms_h($row['created_at'])?></td></tr><?php endforeach;?></table></div></section><?php endif;?>
<?php elseif($view==='media'):?><section class="panel"><h2>Image library</h2><form method="post" enctype="multipart/form-data"><?php csrf_field();?><input type="hidden" name="action" value="upload"><label class="field">Upload an image<input type="file" name="image" accept="image/jpeg,image/png,image/webp" required></label><button>Upload image</button></form><p class="muted">JPG, PNG or WebP, up to 5 MB. Copy an image path into the blog editor.</p><div class="media-grid"><?php foreach(glob(MPMS_ROOT.'/assets/uploads/*.{jpg,jpeg,png,webp}',GLOB_BRACE)?:[] as $file):$url='/assets/uploads/'.basename($file);?><figure><img src="<?=mpms_h($url)?>" alt="Uploaded website image"><figcaption><input aria-label="Image path" readonly value="<?=mpms_h($url)?>"></figcaption></figure><?php endforeach;?></div></section>
<?php elseif($view==='settings'):
$defaults=is_readable(mpms_private('public-settings.php'))?mpms_config('public-settings.php'):[];
?><section class="panel"><h2>Public contact information</h2><p>These settings update the website contact links and addresses. Private email delivery and database credentials remain outside the public website.</p><form method="post"><?php csrf_field();?><input type="hidden" name="action" value="save_settings"><?php field('contact_email','Public email',mpms_setting('contact_email',$defaults['contact_email']??''),false,'type="email" required');field('contact_phone','Main phone',mpms_setting('contact_phone',$defaults['contact_phone']??''),false,'required');?><div class="language-grid"><?php field('address_en','Address · English',mpms_setting('address_en',$defaults['address_en']??''),true);field('address_ar','العنوان · العربية',mpms_setting('address_ar',$defaults['address_ar']??''),true,'dir="rtl"');?></div><button>Save contact settings</button></form></section><section class="panel"><h2>Content backup</h2><p>Download page edits, articles, contact requests and public settings. Keep this file private; it contains enquiry details. Login credentials are excluded.</p><form method="post"><?php csrf_field();?><input type="hidden" name="action" value="export"><button class="secondary">Download private content backup</button></form></section>
<?php elseif($view==='account'):?><section class="panel"><h2>Admin account</h2><p>Signed in as <?=mpms_h($_SESSION['user'])?>. This changes only the admin login.</p><form method="post"><?php csrf_field();?><input type="hidden" name="action" value="password"><?php field('current','Current password','',false,'type="password" required autocomplete="current-password"');field('new','New password','',false,'type="password" minlength="14" required autocomplete="new-password"');field('confirm','Confirm new password','',false,'type="password" minlength="14" required autocomplete="new-password"');?><button>Update admin password</button></form></section><?php endif;?>
</main><?php endif;?></body></html>
