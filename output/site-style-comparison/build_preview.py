"""Build a portable style comparison with shared content and embedded artwork."""
from pathlib import Path
import base64
import re
import struct

ROOT=Path(__file__).resolve().parent
template=(ROOT.parent/'hp-mascot-design/page.template.html').read_text()
template=template.replace('<body>','<body data-theme="three">')
template=template.replace('</style>',(ROOT/'theme.css').read_text()+'\n</style>')
switch='''<div class="style-switch" role="group" aria-label="サイトの絵柄を比較"><button type="button" data-style="three" aria-pressed="true">立体キャラクター</button><button type="button" data-style="pixel" aria-pressed="false">ドット絵</button></div>'''
template=template.replace('<nav class="top-actions"',switch+'\n<nav class="top-actions"')
assets=[]
for asset_id,filename in [('asset-world-3d','school-3d.png'),('asset-mascots-3d','mascots-3d.png'),('asset-pixel','pixel-sheet.png')]:
    raw=(ROOT/filename).read_bytes()
    width,height=struct.unpack('>II',raw[16:24])
    data=base64.b64encode(raw).decode()
    assets.append(f'<image id="{asset_id}" width="{width}" height="{height}" href="data:image/png;base64,{data}"/>')
template=template.replace('<a href="#destinations"', '<svg class="asset-defs" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><defs>'+''.join(assets)+'</defs></svg>\n<a href="#destinations"',1)
world='''<svg id="world-image" viewBox="0 0 1942 809" role="img" aria-label="校舎と校庭を囲む、学級会・運動会・児童会・クラブ活動の広場。" xmlns="http://www.w3.org/2000/svg"><use id="world-use" href="#asset-world-3d"/></svg>'''
template,n=re.subn(r'<img src="__WORLD__"[^>]+>',world,template)
assert n==1
for index,name in [(0,'学活くん'),(1,'行人'),(3,'クラブマン'),(2,'児童会ちゃん')]:
    avatar=f'<svg data-avatar-index="{index}" viewBox="{index*443.5} 30 443.5 734" aria-hidden="true" xmlns="http://www.w3.org/2000/svg"><use href="#asset-mascots-3d"/></svg>'
    template,n=re.subn(r'<img [^>]*alt="'+name+r'">',avatar,template)
    assert n==1
template=re.sub(r'document.querySelectorAll\("img\[data-avatar\]"\).*?;\}\);\n','',template)
template=template.replace("document.getElementById('world-image').alt=config.alt;","document.getElementById('world-image').setAttribute('aria-label',config.alt);")
template=template.replace('4人のキャラクターと多くの仲間が過ごす、レトロな学校の遠景。','4人のキャラクターと多くの仲間が過ごす学校の遠景。')
template=template.replace('<footer><p>LINEで話して、ここで確かめて、持ち帰る。</p>','<footer><p class="comparison-note" id="style-status" aria-live="polite">立体キャラクター版を表示中。同じ内容で見比べられます。</p>')
template=template.replace('</script>',(ROOT/'theme.js').read_text()+'\n</script>')
assert '__WORLD__' not in template and '__MASCOTS__' not in template
(ROOT/'index.html').write_text(template)
print(f'Created {ROOT / "index.html"}: {len(template.encode()):,} bytes')
