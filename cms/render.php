<?php
declare(strict_types=1);
require __DIR__.'/core.php';
header('Content-Type: text/html; charset=utf-8');
header('Cache-Control: no-cache, must-revalidate');
$path=parse_url($_SERVER['REQUEST_URI']??'/',PHP_URL_PATH);
if (!is_string($path) || !preg_match('~^/(en|ar)/(?:[a-z0-9-]+/)*$~',$path,$match)) { http_response_code(404); readfile(MPMS_ROOT.'/404.html'); exit; }
$lang=$match[1];$other=$lang==='en'?'ar':'en';$isBlog=str_starts_with($path,'/'.$lang.'/blog/');
$file=MPMS_ROOT.$path.'index.html';
if (!$isBlog && !is_file($file)) { http_response_code(404); readfile(MPMS_ROOT.'/404.html'); exit; }
$html=(string)file_get_contents($isBlog?MPMS_ROOT.'/'.$lang.'/company/index.html':$file);
try {
    mpms_db();
    $dom=mpms_dom($html);$xpath=new DOMXPath($dom);
    $preview=isset($_GET['cms_preview']);
    if($preview){mpms_session();if(!mpms_logged_in()){http_response_code(403);exit('Sign in to preview unpublished changes.');}header('X-Robots-Tag: noindex, nofollow');header('Cache-Control: no-store');}
    if(!$isBlog){
        $record=mpms_query('SELECT draft_json,live_json FROM '.MPMS_PREFIX.'pages WHERE path=?',[$path])->fetch();
        if($record){$edits=json_decode((string)($preview?$record['draft_json']:$record['live_json']),true)?:[];mpms_apply($dom,$edits);}
    }
    // Blog is always discoverable through the main menu in both languages.
    if($isBlog){foreach($xpath->query('//nav[@id="site-nav"]//a[@aria-current]') as $link){$link->removeAttribute('aria-current');}}
    $menu=$xpath->query('//nav[@id="site-nav"]/ul')->item(0);
    if($menu){$li=$dom->createElement('li');$a=$dom->createElement('a');$a->setAttribute('href','/'.$lang.'/blog/');if($isBlog){$a->setAttribute('aria-current','page');}$a->appendChild($dom->createTextNode($lang==='ar'?'المدونة':'Blog'));$li->appendChild($a);$menu->appendChild($li);}
    // Blog styling is supplied by the shared redesigned site stylesheet.
    // Settings are shared, so contact links stay synchronized across all pages.
    $email=mpms_setting('contact_email');$phone=mpms_setting('contact_phone');$address=mpms_setting('address_'.$lang);
    if($email!==''){
        foreach($xpath->query('//a[starts-with(@href,"mailto:")]') as $a){$a->setAttribute('href','mailto:'.$email);$a->nodeValue=$email;}
    }
    if($phone!==''){
        $defaults=is_readable(mpms_private('public-settings.php'))?mpms_config('public-settings.php'):[];
        $old=preg_replace('/[^+0-9]/','',$defaults['contact_phone']??'');
        foreach($xpath->query('//a[starts-with(@href,"tel:")]') as $a){if($old===''||$a->getAttribute('href')==='tel:'.$old){$a->setAttribute('href','tel:'.preg_replace('/[^+0-9]/','',$phone));$a->nodeValue=$phone;}}
    }
    if($address!==''){foreach($xpath->query('//address') as $node){$node->nodeValue=$address;$node->setAttribute('class',$node->getAttribute('class').' cms-address');}}
    if($isBlog){
        $slug=substr($path,strlen('/'.$lang.'/blog/'));$slug=rtrim($slug,'/');
        $title=$lang==='ar'?'أخبار الشركة ومقالات':'Company news & insights';
        $description=$lang==='ar'?'آخر الأخبار والمستجدات من شركة الطاقة الحديثة للخدمات البحرية.':'Updates and insights from Modern Power Marine Services.';
        $body='';$published=null;
        if($slug!==''){
            $post=mpms_query('SELECT * FROM '.MPMS_PREFIX.'posts WHERE slug=? AND status=\'published\'',[$slug])->fetch();
            if(!$post){http_response_code(404);readfile(MPMS_ROOT.'/404.html');exit;}
            $title=$post['title_'.$lang];$description=$post['excerpt_'.$lang];$published=$post['published_at'];
            $body='<article class="cms-article">';
            if($post['image']){$body.='<img class="cms-cover" src="'.mpms_h($post['image']).'" alt="'.mpms_h($title).'">';}
            if($published){$body.='<p class="cms-date">'.mpms_h(substr($published,0,10)).'</p>';}
            $body.=mpms_markdown($post['body_'.$lang]).'</article>';
        }else{
            $posts=mpms_query('SELECT * FROM '.MPMS_PREFIX.'posts WHERE status=\'published\' ORDER BY published_at DESC LIMIT 100')->fetchAll();
            if(!$posts){$body='<div class="cms-empty"><h2>'.($lang==='ar'?'مستجدات الشركة':'Company updates').'</h2><p>'.($lang==='ar'?'ستُنشر أخبار الشركة ومقالاتها هنا عند توفرها.':'Company news and articles will appear here when published.').'</p></div>';}
            else{$body='<div class="cms-blog-grid">';foreach($posts as $post){$url='/'.$lang.'/blog/'.$post['slug'].'/';$body.='<article class="cms-blog-card">';if($post['image']){$body.='<a href="'.mpms_h($url).'"><img src="'.mpms_h($post['image']).'" alt="" loading="lazy"></a>';}$body.='<div><small>'.mpms_h(substr($post['published_at']??'',0,10)).'</small><h2><a href="'.mpms_h($url).'">'.mpms_h($post['title_'.$lang]).'</a></h2><p>'.mpms_h($post['excerpt_'.$lang]).'</p><a class="arrow" href="'.mpms_h($url).'">'.($lang==='ar'?'قراءة المقال':'Read article').'</a></div></article>';}$body.='</div>';}
        }
        $main='<main id="main"><section class="page-hero"><div class="wrap ph-in"><p><a href="/'.$lang.'/">'.($lang==='ar'?'الرئيسية':'Home').'</a> / <a href="/'.$lang.'/blog/">'.($lang==='ar'?'المدونة':'Blog').'</a></p><h1>'.mpms_h($title).'</h1><p class="lede">'.mpms_h($description).'</p></div></section><section class="section"><div class="wrap">'.$body.'</div></section></main>';
        $fragment=mpms_dom($main);$newMain=$dom->importNode($fragment->getElementsByTagName('main')->item(0),true);$oldMain=$dom->getElementsByTagName('main')->item(0);$oldMain->parentNode->replaceChild($newMain,$oldMain);
        $dom->getElementsByTagName('title')->item(0)->nodeValue=$title.' | MPMS';
        foreach($xpath->query('//meta[@name="description" or @property="og:description"]') as $meta){$meta->setAttribute('content',$description);}
        foreach($xpath->query('//meta[@property="og:title"]') as $meta){$meta->setAttribute('content',$title.' | MPMS');}
        foreach($xpath->query('//meta[@property="og:url"]') as $meta){$meta->setAttribute('content','https://modernpowersa.com'.$path);}
        foreach($xpath->query('//link[@rel="canonical"]') as $link){$link->setAttribute('href','https://modernpowersa.com'.$path);}
        foreach($xpath->query('//link[@rel="alternate" and (@hreflang="en" or @hreflang="ar")]') as $link){$link->setAttribute('href','https://modernpowersa.com/'. $link->getAttribute('hreflang').'/blog/'.($slug!==''?$slug.'/':''));}
        foreach($xpath->query('//a[contains(concat(" ",@class," ")," lang-switch ")]') as $link){$link->setAttribute('href','/'.$other.'/blog/'.($slug!==''?$slug.'/':''));}
        foreach(iterator_to_array($xpath->query('//script[@type="application/ld+json"]')) as $script){$script->parentNode->removeChild($script);}
    }
    echo $dom->saveHTML();
}catch(Throwable $e){
    error_log('MPMS public content backend unavailable: '.$e->getCode());
    if($isBlog){http_response_code(503);header('Retry-After: 300');echo '<!doctype html><html lang="'.$lang.'"><meta charset="utf-8"><title>MPMS</title><p>'.($lang==='ar'?'المدونة غير متاحة مؤقتًا.':'The blog is temporarily unavailable.').'</p><a href="/'.$lang.'/">MPMS</a></html>';}
    else{echo $html;}
}
