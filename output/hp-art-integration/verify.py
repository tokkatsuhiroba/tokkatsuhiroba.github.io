"""Static integration checks; intentionally does not launch a browser."""
from pathlib import Path
from html.parser import HTMLParser
from collections import Counter
from urllib.parse import urlsplit, unquote
import sys, json, re, subprocess

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import build

class Page(HTMLParser):
    def __init__(self):
        super().__init__();self.ids=[];self.links=[];self.uses=[];self.scripts=[];self.script=None
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if 'id' in d:self.ids.append(d['id'])
        if tag=='a' and 'href' in d:self.links.append(d['href'])
        if tag=='use':self.uses.append(d.get('href',''))
        if tag=='script' and d.get('type','') not in ('application/ld+json',):self.script=''
    def handle_endtag(self,tag):
        if tag=='script' and self.script is not None:self.scripts.append(self.script);self.script=None
    def handle_data(self,s):
        if self.script is not None:self.script+=s

pages,*_=build.build_shin()
parsed={}
errors=[]
for name,html in pages.items():
    p=Page();p.feed(html);parsed[name]=p
    ids=set(p.ids)
    for ref in p.uses:
        if not ref.startswith('#') or ref[1:] not in ids:errors.append([name,'unresolved SVG',ref])
    for identity,n in Counter(p.ids).items():
        if n>1:errors.append([name,'duplicate id',identity])
    for bad in ['<ns0:','/output/','<!--BUILD:']:
        if bad in html:errors.append([name,'unresolved source',bad])
    for i,js in enumerate(p.scripts):
        result=subprocess.run(['node','--check'],input=js,text=True,capture_output=True)
        if result.returncode:errors.append([name,'JS syntax',i,result.stderr])

for name,p in parsed.items():
    for href in p.links:
        u=urlsplit(href)
        if u.scheme or u.netloc:continue
        target=unquote(u.path) or name
        if not target.endswith('.html'):continue
        if target not in parsed:errors.append([name,'missing page',href]);continue
        if u.fragment and unquote(u.fragment) not in parsed[target].ids:errors.append([name,'missing anchor',href])

home=pages['index.html']
for key in ['gakkatsu-listen','gyoji-calendar','jidokai-share','club-try','group-shoulders','group-thanks']:
    if f'href="#ill-k-{key}"' not in home:errors.append(['index.html','missing intended art',key])
if 'viewBox="0 0 3200 1550"' not in home:errors.append(['index.html','wrong school viewBox'])
for bad in ['class="hkumo"','class="hko"','viewBox="760 140 1450 1060"']:
    if bad in home:errors.append(['index.html','obsolete overlay/crop',bad])

# Every newly adopted shape is normalised for the existing 0,0 SVG consumers.
kyara=build.load_kyara()
for key in ['gakkatsu-listen','gyoji-calendar','jidokai-share','club-try']:
    w,h,body=kyara[key]
    if (w,h)!=(170,152) or 'translate(30 17)' not in body:errors.append([key,'viewBox normalisation'])

report={'pages':len(pages),'svgReferences':sum(len(p.uses) for p in parsed.values()),
        'inlineScripts':sum(len(p.scripts) for p in parsed.values()),'errors':errors,
        'browserCheck':'Not run: browser URL policy blocked the local page.'}
(Path(__file__).parent/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False,indent=2))
raise SystemExit(bool(errors))
