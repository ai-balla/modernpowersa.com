<?php
declare(strict_types=1);
require __DIR__.'/core.php';
header('Content-Type: application/xml; charset=utf-8');header('Cache-Control: no-cache');
$xml=(string)file_get_contents(MPMS_ROOT.'/sitemap.xml');
try{
    $dom=new DOMDocument();$dom->loadXML($xml,LIBXML_NONET);$root=$dom->documentElement;$namespace=$root->namespaceURI;
    $entries=[];foreach(['en','ar'] as $lang){$entries[]=['path'=>'/'.$lang.'/blog/','date'=>null];}
    foreach(mpms_query('SELECT slug,updated_at FROM '.MPMS_PREFIX.'posts WHERE status=\'published\'') as $post){foreach(['en','ar'] as $lang){$entries[]=['path'=>'/'.$lang.'/blog/'.$post['slug'].'/','date'=>substr($post['updated_at'],0,10)];}}
    foreach($entries as $entry){$url=$dom->createElementNS($namespace,'url');$loc=$dom->createElementNS($namespace,'loc');$loc->appendChild($dom->createTextNode('https://modernpowersa.com'.$entry['path']));$url->appendChild($loc);if($entry['date']){$url->appendChild($dom->createElementNS($namespace,'lastmod',$entry['date']));}$root->appendChild($url);}
    echo $dom->saveXML();
}catch(Throwable $e){error_log('MPMS dynamic sitemap unavailable.');echo $xml;}
