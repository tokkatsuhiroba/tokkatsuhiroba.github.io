"""School panorama based on the live site's SVG parts and approved v6 mascots.

Only writes this output directory. The source site and its build are untouched.
"""
from pathlib import Path
import copy
import importlib.util
import re
import xml.etree.ElementTree as ET

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent.parent
NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)
spec=importlib.util.spec_from_file_location('site_build',PROJECT/'build.py')
site=importlib.util.module_from_spec(spec);spec.loader.exec_module(site)
parts,_=site.load_buhin()
INK='#1C1C1A';PAPER='#FCFBF7';GREEN='#1F5C3F';RED='#D2552A';BLUE='#3A6EA5';YELLOW='#E8C547';SKIN='#F6D8B8'
colors=[GREEN,RED,BLUE,YELLOW]
stroke=f'stroke="{INK}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"'

# Give the small supporting pupils the same fringe, oval eyes and line smile.
# Retain each pose and its original head/body scale.
for key in ['ko-tatsu','ko-te','ko-suwaru','ko-hashiru','sensei','shosho']:
    w,h,body=parts[key]
    root=ET.fromstring(f'<svg xmlns="{NS}">{body}</svg>')
    group=root.find('{'+NS+'}g')
    face=next((n for n in group if n.tag=='{'+NS+'}circle' and n.get('fill')==SKIN and float(n.get('r','0'))>8),None)
    if face is None:continue
    cx,cy,r=(float(face.get(attr)) for attr in ['cx','cy','r'])
    face_index=list(group).index(face)
    for n in list(group)[face_index:]:group.remove(n)
    head=ET.fromstring(f'''<g xmlns="{NS}" transform="translate({cx},{cy}) scale({r/25})" stroke="{INK}" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">
      <circle r="25" fill="{SKIN}"/>
      <path d="M-25-2C-25-17-14-25 0-25S24-16 25-2L18-8 16-4 12-13C5-6-5-4-16-5L-12-11Z" fill="{INK}" stroke="none"/>
      <ellipse cx="-9" cy="2" rx="2.65" ry="3.45" fill="{INK}" stroke="none"/><ellipse cx="9" cy="2" rx="2.65" ry="3.45" fill="{INK}" stroke="none"/>
      <path d="M-6 11q6 6 12 0" fill="none" stroke-width="2.7"/>
      <circle cx="-18" cy="8" r="2.8" fill="{RED}" opacity=".65" stroke="none"/><circle cx="18" cy="8" r="2.8" fill="{RED}" opacity=".65" stroke="none"/>
    </g>''')
    group.append(head)
    parts[key]=(w,h,''.join(ET.tostring(n,encoding='unicode') for n in root))

# A clear back of the head, rather than a blank face-shaped patch.
w,h,body=parts['ko-ushiro']
root=ET.fromstring(f'<svg xmlns="{NS}">{body}</svg>')
for n in root.iter():
    if n.tag=='{'+NS+'}circle' and n.get('r')=='14.5':n.set('fill',INK)
parts['ko-ushiro']=(w,h,''.join(ET.tostring(n,encoding='unicode') for n in root))

for key in ['gakkatsu','gyoji','jidokai','club']:
    root=ET.parse(HERE.parent/'characters-refined-v6'/f'{key}.svg').getroot()
    parts[key]=(96,126,ET.tostring(root.find('{'+NS+'}g'),encoding='unicode'))

def place(key,x,base,color=None):
    w,h,body=parts[key]
    # Recolor clothes, keeping the warm cheek color unchanged.
    if color:
        root=ET.fromstring(f'<svg xmlns="{NS}">{body}</svg>')
        for n in root.iter():
            if n.get('fill')==RED and n.tag!='{'+NS+'}circle':n.set('fill',color)
        body=''.join(ET.tostring(n,encoding='unicode') for n in root)
    return f'<g transform="translate({x-w/2},{base-h+8})">{body}</g>'

def rect(x,y,w,h,fill,rx=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" {stroke}/>'

def path(d,fill='none',color=INK,width=2.5):
    return f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'

# Keep the familiar sky, trees, fence, schoolhouse, gym and yellow ground.
background=site.hiroba_naka(parts).split('<path d="M74 946')[0]
# Replace the incomplete running lane with a complete, readable oval below.
background=re.sub(r'<path d="M900 1060[^>]+/>','',background)
art=[background]

# 1. Class meeting: chalkboard, facilitator and U-shaped discussion seats.
art.append(rect(48,850,694,350,PAPER,12))
art.append(place('kokuban',235,1040))
art.append(place('gakkatsu',464,1044))
for i,(x,y) in enumerate([(610,1030),(140,1144),(300,1176),(465,1176),(630,1150)]):
    art.append(place('ko-te' if i==0 else 'ko-suwaru',x,y,colors[(i+2)%4]))
    # Individual desks leave the center open for the discussion.
    desk_y=y-8
    art.append(path(f'M{x-38} {desk_y+5}v26M{x+38} {desk_y+5}v26'))
    art.append(rect(x-52,desk_y-12,104,17,PAPER,3))
    art.append(path(f'M{x-18} {desk_y-7}h29',color=BLUE))
art.append(path('M345 995h38M345 1004h23',color=YELLOW))

# 2. School events: a flower arch, sports-day gate, relay, basket and cheering.
art.append(place('hana-arch',920,982))
art.append(place('shosho',920,979))
for i,x in enumerate([815,868,974,1027]):
    art.append(place('ko-ushiro',x,880,colors[i]))
for x in [1085,1515]:art.append(place('bankokki',x,814))
art.append(place('nyutaijo',1260,1000))
art.append(place('kago',1652,1017))
art.append(f'<ellipse cx="1390" cy="1095" rx="306" ry="86" fill="none" stroke="{PAPER}" stroke-width="7"/>')
art.append(f'<ellipse cx="1390" cy="1095" rx="265" ry="63" fill="none" stroke="{PAPER}" stroke-width="3"/>')
art.append(place('gyoji',1020,1174))
for i,(x,y) in enumerate([(1190,1112),(1370,1137),(1550,1090)]):
    art.append(place('ko-hashiru',x,y,[RED,BLUE,GREEN][i]))
    art.append(rect(x+22,y-55,6,23,YELLOW,2))
for i,x in enumerate([1190,1295,1400,1505,1610]):
    art.append(place('ko-te' if i%2==0 else 'ko-tatsu',x,982 if i<2 else 1000,colors[(i+1)%4]))
for x in [790,1720]:art.append(place('hata',x,1190))

# 3. Student council: the mascot speaks, friends bring ideas, peers listen.
art.append(place('keijiban',1870,940))
art.append(place('nobori',2320,954))
art.append(place('nobori',2372,969))
art.append(rect(2002,960,196,18,PAPER,2))
art.append(path('M2020 978v20M2180 978v20'))
art.append(place('jidokai',2080,957))
art.append(place('ko-te',2248,987,BLUE))
art.append(place('ko-tatsu',1936,1024,GREEN))
art.append(rect(1924,973,25,32,PAPER,1))
art.append(path('M1929 982h15M1929 990h15',color=GREEN))
for row,(base,start,count) in enumerate([(1071,1830,7),(1122,1860,7),(1174,1890,6)]):
    for i in range(count):art.append(place('ko-ushiro',start+i*65,base,colors[(i+row)%4]))

# 4. Clubs: music, painting, science, and exercise around the yellow mascot.
art.append(place('taiko',2530,975))
art.append(place('ko-tatsu',2620,966,RED))
art.append(path('M2610 929l-42-12M2627 940l-55-8'))
art.append(place('easel',2800,981))
art.append(place('ko-tatsu',2890,982,BLUE))
art.append(path('M2878 943l-34-20',color=GREEN))
art.append(place('jikken',3070,970))
art.append(place('ko-te',2970,980,GREEN))
art.append(place('club',2485,1156))
art.append(place('tetsubo',2708,1154))
art.append(place('ko-hashiru',2840,1159,YELLOW))
art.append(place('ko-tatsu',3020,1150,BLUE))
art.append(place('ko-suwaru',3130,1150,GREEN))
# A familiar low worktable with paper and a little airplane.
art.append(rect(2970,1121,197,18,PAPER,3))
art.append(path('M2983 1139v42M3152 1139v42'))
art.append(path('M3048 1109l48-25-18 32-8-10Z',PAPER))
art.append(path('M3070 1106l26-22',color=BLUE))
art.append(rect(2993,1106,31,13,YELLOW,1))

content='\n'.join(art)
assert 'ns0:' not in content
title='特活広場：学級会・学校行事・児童会・クラブ活動が広がる学校'
def svg(box):return f'<svg xmlns="{NS}" viewBox="{box}"><title>{title}</title>{content}</svg>'
(HERE/'school.svg').write_text(svg('0 0 3200 1200'))
(HERE/'school-close.svg').write_text(svg('0 310 3200 890'))
for key,box in [('class','20 820 750 380'),('events','765 750 990 450'),('council','1740 750 680 450'),('club','2410 750 790 450')]:
    (HERE/f'detail-{key}.svg').write_text(svg(box))
print('Created panorama, closer view and four activity details.')
