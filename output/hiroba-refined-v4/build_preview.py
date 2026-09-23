from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
NS='http://www.w3.org/2000/svg'
# HTML's inline SVG parser does not resolve XML prefixes such as ns0:path.
# Serialize with the default SVG namespace so shapes remain native SVG elements.
ET.register_namespace('',NS)
template=(ROOT.parent/'hp-mascot-design/page.template.html').read_text()
template=template.replace('<title>TOKKATSU広場｜みんなの特活が、つながる場所</title>','<title>TOKKATSU広場｜いつもの広場を、少し丁寧に</title>')
template=template.replace('</style>',(ROOT/'refined.css').read_text()+'\n</style>')
template=template.replace('<nav class="top-actions" aria-label="サイト案内">','<nav class="top-actions" aria-label="サイト案内"><button class="pill" type="button" data-dialog="characters">4人の紹介</button>')
world=ET.parse(ROOT/'school.svg').getroot()
defs=ET.tostring(world[0],encoding='unicode')
people=[('gakkatsu','学活くん','学級活動','話し合う、決める、やってみる。みんなの考えをつなぐ案内役。','#e4ead7','#1F5C3F'),('gyoji','行人','学校行事','旗を持って、みんなを応援。行事に向かう一歩をいっしょに。','#f2e1d3','#a43c20'),('jidokai','児童会ちゃん','児童会活動','みんなの声を集めて届ける。学校をよくするアイデアをいっしょに。','#dfe8e9','#2d5e8b'),('club','クラブマン','クラブ活動','好きなことを、仲間といっしょに。試したくなる活動を見つけよう。','#f2e7bd','#6c5314')]
roster=[]
for key,name,role,description,tint,tone in people:
    group=ET.parse(ROOT/f'{key}.svg').getroot().find('{'+NS+'}g')
    defs+=f'<g id="mascot-{key}">'+ET.tostring(group,encoding='unicode')+'</g>'
    avatar=f'<svg viewBox="0 0 96 126" aria-hidden="true"><use href="#mascot-{key}"/></svg>'
    template,n=re.subn(r'<img [^>]*alt="'+name+r'">',avatar,template)
    assert n==1
    template=template.replace(f'<span class="guide-name">{name}</span>',f'<span class="guide-name">{name}</span><span class="guide-role">{role}</span>')
    roster.append(f'<article class="roster-card" style="--tint:{tint};--tone:{tone}">{avatar}<h3>{name}</h3><p class="role">{role}</p><p>{description}</p></article>')
template=template.replace('<body>','<body><svg class="asset-defs" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><defs>'+defs+'</defs></svg>')
cards=re.findall(r'<a class="guide"[^>]*>.*?</a>',template,re.S)
assert len(cards)==4
for old in cards:template=template.replace(old,'__GUIDE_SLOT__',1)
for i in [0,1,3,2]:template=template.replace('__GUIDE_SLOT__',cards[i],1)
world_svg='<svg id="world-image" viewBox="0 250 3200 950" role="img" aria-label="今の特活広場と同じ校庭。学級会、運動会、児童会、クラブ活動をする仲間たち。"><use href="#ill-hiroba"/></svg>'
template,n=re.subn(r'<img src="__WORLD__"[^>]+>',world_svg,template);assert n==1
# Use activity names that children recognize immediately, preserving the 4 official roles on the cards.
for key,label in [('class','学級会'),('events','運動会'),('council','児童会'),('club','クラブ')]:
    template=re.sub(r'(data-scene="'+key+r'" aria-pressed="false">)[^<]+',r'\g<1>'+label,template)
template=template.replace('<div class="scene-toolbar">','<span id="scene-status" class="sr-only" aria-live="polite"></span><div class="scene-toolbar">')
dialog='<dialog id="characters" class="roster-dialog" aria-labelledby="characters-title"><div class="dialog-header"><h2 id="characters-title">広場の4人。</h2><button type="button" class="close" data-close aria-label="4人の紹介を閉じる">×</button></div><div class="roster-grid">'+''.join(roster)+'</div></dialog>'
template=template.replace('<script>',dialog+'\n<script>')
js=(ROOT.parent/'pixel-hiroba-v3/pixel.js').read_text()
boxes={'0 384 1536 640':'0 250 3200 950','0 628 420 260':'30 865 740 335','412 557 510 361':'790 765 960 435','890 595 297 298':'1720 775 700 425','1170 594 366 397':'2390 775 810 425'}
for old,new in boxes.items():js=js.replace(old,new)
js=js.replace('unmodified approved school sheet','original SVG school panorama with refined mascot leaders')
js=js.replace('バトンをつなぐ走者と応援する仲間。','校庭を走ったり玉入れをしたりする仲間。').replace('座った仲間に呼びかける。','集まった仲間に呼びかける。').replace('絵、工作、太鼓、花壇の水やり。','絵、科学、太鼓、運動。')
template=re.sub(r'<script>.*?</script>',lambda m:'<script>\n'+js+'\n</script>',template,flags=re.S)
assert '__WORLD__' not in template and '__MASCOTS__' not in template
assert not re.search(r'</?ns\d+:',template), 'XML-prefixed shapes cannot render as inline HTML SVG'
(ROOT/'index.html').write_text(template)
(ROOT/'ui-syntax-check.js').write_text(js)
print('Built standalone refined-original preview:',len(template.encode()),'bytes')
