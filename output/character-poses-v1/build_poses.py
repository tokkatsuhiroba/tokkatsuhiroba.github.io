from pathlib import Path
import xml.etree.ElementTree as ET
from html import escape
import json

HERE=Path(__file__).resolve().parent
SOURCE=HERE.parent/'characters-refined-v6'
NS='http://www.w3.org/2000/svg';ET.register_namespace('',NS)
INK='#1C1C1A';PAPER='#FCFBF7';SKIN='#F6D8B8';GREEN='#1F5C3F';RED='#D2552A';BLUE='#3A6EA5';YELLOW='#E8C547'
STYLE=f'stroke="{INK}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"'
names={'gakkatsu':'学活くん','gyoji':'行人','jidokai':'児童会ちゃん','club':'クラブマン'}
colors={'gakkatsu':GREEN,'gyoji':RED,'jidokai':BLUE,'club':YELLOW}
tints={'gakkatsu':'#EAF1E0','gyoji':'#F8E5D8','jidokai':'#E4EFF3','club':'#FBF0C5'}
def path(d,fill='none',stroke=INK,width=2.2):return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>'
def rect(x,y,w,h,fill,rx=2):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"/>'
def circle(x,y,r,fill):return f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}"/>'
def txt(x,y,t,size=20,fill=INK,anchor='middle'):
    return f'<text x="{x}" y="{y}" font-family="Hiragino Sans, sans-serif" font-size="{size}" text-anchor="{anchor}" fill="{fill}" stroke="none">{escape(t)}</text>'
def arm(d):return path(d,stroke=INK,width=12)+path(d,stroke=SKIN,width=7.8)

original={}
for key in names:
    children=list(ET.parse(SOURCE/f'{key}.svg').getroot().find('{'+NS+'}g'))
    start=next(i for i,n in enumerate(children) if n.tag.endswith('circle') and n.get('cx')=='48' and n.get('r')=='25')
    serialize=lambda n:ET.tostring(n,encoding='unicode')
    head=[];legs=[];body=[];cape=[]
    body_details={'gakkatsu':['M48 56','M52 58'],'gyoji':['M32 66','M30 94'],'jidokai':['M32 55','M26 96'],'club':['M48 67']}
    for i,n in enumerate(children):
        d=n.get('d','')
        if n.tag.endswith('rect') and n.get('y')=='94' or d.startswith(('M33 110','M63 110','M33 115')):legs.append(serialize(n))
        elif d.startswith('M48 52') or any(d.startswith(p) for p in body_details[key]):body.append(serialize(n))
        elif key=='club' and d.startswith(('M32 56','M25 75')):cape.append(serialize(n))
        elif i>=start and not d.startswith('M84 53'):head.append(serialize(n))
    original[key]={'head':''.join(head),'legs':''.join(legs),'body':''.join(body),'cape':''.join(cape)}

def prop_calendar():
    o=[rect(4,71,50,38,PAPER),rect(4,71,50,10,RED),path('M15 67v10M42 67v10',stroke=INK,width=3)]
    for x in [15,28,41]:
        for y in [88,99]:o.append(rect(x-3,y-2,6,5,YELLOW if (x,y)==(28,99) else '#B4D9E5',0))
    o.append(circle(28,99,6,'none'));return ''.join(o)
def prop_document(x=54,y=68):
    return rect(x,y,34,42,PAPER)+rect(x+6,y+8,22,11,'#B4D9E5',1)+path(f'M{x+6} {y+26}h22M{x+6} {y+33}h15',stroke=BLUE,width=1.8)
def prop_book():
    return path('M16 77Q31 72 48 80Q64 72 80 77V108Q63 103 48 111Q32 103 16 108Z',PAPER)+path('M48 80v31M23 85l17 2M23 94l17 2M56 88l16-3M56 97l16-3',stroke=BLUE,width=1.7)
def prop_bulb():
    return path('M79 42Q66 34 71 20Q76 9 88 13Q104 18 95 34L90 42Z',YELLOW)+rect(79,42,12,7,PAPER)+path('M81 52h8M84 13V4M65 19l-7-4M101 18l7-4M66 36l-7 3M104 35l6 3',stroke=INK,width=1.8)
def pose(key,p):
    o=original[key];left='M28 64Q20 73 21 86';right='M68 64Q77 72 76 87';prop='';hands=[];tilt=0
    if p=='welcome':left='M28 64Q12 49 9 27';right='M68 64Q80 69 89 59'
    elif p=='listen':left='M28 64Q9 71 12 52L19 44';right='M68 64Q78 77 88 72';tilt=-5
    elif p=='think':left='M28 64Q23 85 47 84';right='M68 64Q73 79 62 67L55 50';tilt=6
    elif p=='guide':left='M28 64Q18 69 8 78';right='M68 64Q84 73 100 63';prop=path('M91 38h21m-7-7 7 7-7 7',stroke=colors[key],width=3)
    elif p=='board':left='M28 64Q17 74 22 88';right='M68 64Q81 69 87 55';prop=rect(90,31,37,48,GREEN)+path('M90 81v19M126 81v19',stroke=INK)+path('M97 41h21M97 49h15M99 61l4 4 12-9',stroke=PAPER,width=2)+path('M85 56l21-8',stroke='#B18455',width=2)
    elif p=='thanks':left='M28 64Q20 82 44 89';right='M68 64Q77 82 52 89';tilt=7
    elif p=='calendar':left='M28 64Q12 71 7 91';right='M68 64Q67 80 53 91';prop=prop_calendar();hands=[circle(6,93,4.5,SKIN),circle(54,93,4.5,SKIN)]
    elif p=='news':left='M28 64Q20 74 22 85';right='M68 64Q83 75 88 61';prop=path('M83 49l29-12v31L83 56Z',PAPER)+path('M84 55v16h7V58',RED)+path('M119 39l8-5M121 52h10M119 64l8 5',stroke=RED,width=2.5)
    elif p=='cheer':left='M28 64Q14 47 8 29';right='M68 64Q83 47 89 29'
    elif p=='speak':left='M28 64Q15 73 4 62';right='M68 64Q84 79 85 58';prop=path('M84 64l3-18',stroke=INK,width=4)+f'<g transform="rotate(8 88 44)">{rect(81,34,14,13,PAPER,6)}{path("M84 38h8M84 42h8",width=1.2)}</g>'
    elif p=='share':left='M28 64Q15 77 15 86';right='M68 64Q86 79 84 88';prop=prop_document();hands=[circle(85,88,4.5,SKIN)]
    elif p=='upload':left='M28 64Q16 79 25 91';right='M68 64Q80 79 71 91';prop=rect(21,78,55,35,PAPER)+path('M22 80l26 20 27-20M21 111l18-17M76 111l-18-17',stroke=BLUE,width=1.7)+path('M97 100V78M89 86l8-8 8 8',stroke=BLUE,width=3);hands=[circle(22,95,4.5,SKIN),circle(75,95,4.5,SKIN)]
    elif p=='try':left='M28 64Q18 75 19 86';right='M68 64Q89 66 94 55';prop=f'<g transform="translate(10 0)">{prop_bulb()}</g>'
    elif p=='tools':left='M28 64Q14 78 12 87';right='M68 64Q80 79 84 90';prop=rect(12,82,57,32,BLUE)+path('M31 82v-9h20v9',stroke=INK,width=3)+path('M13 94h55',stroke=PAPER,width=1.5)+rect(36,92,9,7,YELLOW,1);hands=[circle(13,93,4.5,SKIN)]
    elif p=='make':left='M28 64Q15 72 15 84';right='M68 64Q85 72 92 59';prop=path('M9 78Q-1 78 0 92Q1 108 19 104Q33 101 27 89Q24 78 9 78Z',PAPER)+circle(8,88,3,RED)+circle(18,92,3,BLUE)+circle(11,98,3,YELLOW)+path('M90 61l12-28',stroke='#A77C4D',width=3)+path('M101 35q-3-7 6-12q2 10-3 13Z',BLUE)
    frontarms=p in ['thanks','think']
    body=o['cape']+o['legs']+('' if frontarms else arm(left)+arm(right))+o['body']
    headcontent=o['head']
    if p=='thanks':
        r=ET.fromstring(f'<g xmlns="{NS}">{headcontent}</g>')
        for n in r.iter():
            if n.tag.endswith('ellipse'):
                x=float(n.get('cx'));y=float(n.get('cy'))
                n.tag='{'+NS+'}path';n.attrib.clear();n.set('d',f'M{x-3} {y}q3 4 6 0');n.set('fill','none');n.set('stroke',INK);n.set('stroke-width','1.8')
        headcontent=ET.tostring(r,encoding='unicode')
    head=f'<g transform="rotate({tilt} 48 50)">{headcontent}</g>'
    return f'<g {STYLE}>{body}{head}{arm(left)+arm(right) if frontarms else ""}{prop}{"".join(hands)}</g>'

catalog={
 'gakkatsu':[('welcome','ようこそ'),('listen','ちょっと聞きたい'),('think','一緒に考える'),('guide','こちらへどうぞ'),('board','学ぶ・学級会'),('thanks','ありがとう')],
 'gyoji':[('welcome','ようこそ'),('calendar','研究日程'),('news','最新のニュース'),('guide','こちらへどうぞ'),('cheer','応援する'),('thanks','ありがとう')],
 'jidokai':[('welcome','ようこそ'),('speak','伝える・発表'),('share','みんなの実践'),('upload','実践を送る'),('guide','こちらへどうぞ'),('thanks','ありがとう')],
 'club':[('welcome','ようこそ'),('try','ちょっと試したい'),('tools','すぐ使える道具'),('make','作ってみよう'),('guide','こちらへどうぞ'),('cheer','やったね！')]
}
def svg(body,box,title):return f'<svg xmlns="{NS}" viewBox="{box}"><title>{escape(title)}</title>{body}</svg>'
manifest=[]
for key,items in catalog.items():
    for p,title in items:
        file=f'{key}-{p}'
        (HERE/f'{file}.svg').write_text(svg(pose(key,p),'-30 -17 170 152',f'{names[key]}：{title}'))
        manifest.append({'file':file,'character':names[key],'use':title,'transparent':True})

def shoulders():
    o=[];centers=[48,122,196,270]
    # All linking arms are behind the four bodies, hands land on adjacent shoulders.
    for i,c in enumerate(centers[:-1]):o.append(arm(f'M{c+20} 65Q{c+40} 57 {c+54} 65'))
    o.append(arm('M28 64Q12 48 9 28'));o.append(arm('M290 64Q306 48 312 28'))
    for i,key in enumerate(names):
        d=original[key];x=centers[i]-48
        o.append(f'<g transform="translate({x} 0)">{d["cape"]}{d["legs"]}{d["body"]}<g transform="rotate({[4,-4,4,-4][i]} 48 50)">{d["head"]}</g></g>')
    for c in centers[:-1]:o.append(circle(c+54,64,4.5,SKIN))
    return f'<g {STYLE}>'+''.join(o)+'</g>'
groups={
 'group-shoulders':('４人で肩を組む',shoulders(),' -12 -10 345 143'),
 'group-welcome':('４人でようこそ',''.join(f'<g transform="translate({i*117} 0)">{pose(k,"welcome")}</g>' for i,k in enumerate(names)),'-15 -12 480 147'),
 'group-thanks':('４人でありがとう',''.join(f'<g transform="translate({i*104} 0)">{pose(k,"thanks")}</g>' for i,k in enumerate(names)),'-15 -12 431 147')
}
for file,(title,body,box) in groups.items():
    (HERE/f'{file}.svg').write_text(svg(body,box,title));manifest.append({'file':file,'character':'４人','use':title,'transparent':True})

# Review sheets have generous spacing and labels outside the usable artwork.
def sheet(key,items):
    o=[rect(0,0,1260,940,PAPER,0),txt(630,63,names[key]+' のポーズ集',32)]
    for i,(p,t) in enumerate(items):
        x=30+(i%3)*410;y=102+(i//3)*404
        o.append(f'<rect x="{x}" y="{y}" width="380" height="366" rx="22" fill="{tints[key]}"/>')
        o.append(f'<g transform="translate({x+85} {y+40}) scale(2.1)">{pose(key,p)}</g>')
        o.append(txt(x+190,y+331,t,24))
    return svg(''.join(o),'0 0 1260 940',names[key]+' の６ポーズ')
for key,items in catalog.items():(HERE/f'sheet-{key}.svg').write_text(sheet(key,items))

o=[rect(0,0,1760,1510,PAPER,0),txt(880,60,'特活広場の４人 — ポーズコレクション',34)]
for row,(key,items) in enumerate(catalog.items()):
    y=100+row*350
    o.append(txt(40,y+27,names[key],24,('#80621D' if key=='club' else colors[key]),'start'))
    for col,(p,t) in enumerate(items):
        x=28+col*290
        o.append(f'<rect x="{x}" y="{y+49}" width="274" height="277" rx="15" fill="{tints[key]}"/>')
        o.append(f'<g transform="translate({x+66} {y+65}) scale(1.60)">{pose(key,p)}</g>')
        o.append(txt(x+137,y+301,t,18))
(HERE/'all-poses.svg').write_text(svg(''.join(o),'0 0 1760 1510','４人の24ポーズ一覧'))

o=[rect(0,0,1500,1510,PAPER,0),txt(750,68,'４人いっしょに',34)]
for i,(file,(title,body,box)) in enumerate(groups.items()):
    y=125+i*450;w=float(box.split()[2]);sc=min(1220/w,2.55)
    o.append(f'<rect x="65" y="{y-8}" width="1370" height="404" rx="24" fill="{["#EAF1E0","#E4EFF3","#FBF0C5"][i]}"/>')
    # Scale groups to fit the same horizontal span without changing their shape.
    o.append(f'<g transform="translate({(1500-w*sc)/2+15*sc} {y+15}) scale({sc})">{body}</g>')
    o.append(txt(750,y+367,title,27))
(HERE/'sheet-groups.svg').write_text(svg(''.join(o),'0 0 1500 1510','４人の集合ポーズ'))

entry=[('gakkatsu','listen','ちょっと聞きたい'),('gyoji','calendar','ちょっと知りたい'),('jidokai','share','ちょっと伝えたい'),('club','try','ちょっと試したい')]
o=[rect(0,0,1600,490,PAPER,0)]
for i,(key,p,t) in enumerate(entry):
    x=i*400;o.append(f'<rect x="{x+16}" y="20" width="368" height="446" rx="24" fill="{tints[key]}"/>')
    o.append(f'<g transform="translate({x+88} 60) scale(2.30)">{pose(key,p)}</g>')
    o.append(txt(x+200,380,names[key],24,('#80621D' if key=='club' else colors[key])));o.append(txt(x+200,426,t,25))
(HERE/'homepage-entries.svg').write_text(svg(''.join(o),'0 0 1600 490','HPの４つの入口用ポーズ'))
(HERE/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
(HERE/'README.md').write_text('''# 特活広場 キャラクターポーズ集\n\n承認済みの characters-refined-v6 の顔・服・色を用いた、24の個別ポーズと3つの集合ポーズです。\n\n- all-poses.png：全24ポーズ一覧\n- sheet-groups.png：肩を組む／ようこそ／ありがとう\n- homepage-entries.png：HPの4つの入口への割り当て案\n- sheet-*.png：各キャラクターの6ポーズ\n- その他のPNG：背景透過、個別素材。SVGは拡大・編集用です。\n- manifest.json：ファイル名と用途一覧\n\nHPの項目は src/hiroba.html と build.py の入口定義を参照しました。サイト本体は変更していません。\n''')
print(f'Built {len(manifest)} transparent assets and 7 review sheets.')
