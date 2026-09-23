"""School panorama based on the live site's SVG parts and approved v6 mascots.

Only writes this output directory. The source site and its build are untouched.
"""
from pathlib import Path
import copy
import importlib.util
import re
from html import escape
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

def place(key,x,base,color=None,scale=1):
    w,h,body=parts[key]
    # Recolor clothes, keeping the warm cheek color unchanged.
    if color:
        root=ET.fromstring(f'<svg xmlns="{NS}">{body}</svg>')
        for n in root.iter():
            if n.get('fill')==RED and n.tag!='{'+NS+'}circle':n.set('fill',color)
        body=''.join(ET.tostring(n,encoding='unicode') for n in root)
    return f'<g transform="translate({x-w*scale/2},{base-(h-8)*scale}) scale({scale})">{body}</g>'

def rect(x,y,w,h,fill,rx=0):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" {stroke}/>'

def path(d,fill='none',color=INK,width=2.5):
    return f'<path d="{d}" fill="{fill}" stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'

def text(x,y,label,size=15,fill=INK,anchor='start'):
    # Scenes must read through actions and props, never category/name labels.
    return ''

def die(x,y,size=22):
    o=[rect(x,y,size,size,PAPER,3)]
    for dx,dy in [(.25,.25),(.75,.25),(.5,.5),(.25,.75),(.75,.75)]:
        o.append(f'<circle cx="{x+size*dx}" cy="{y+size*dy}" r="{size*.07}" fill="{BLUE}"/>')
    return ''.join(o)

def picture_cards(x,y):
    return rect(x,y,22,32,PAPER,2)+rect(x+14,y+6,22,32,PAPER,2)+path(f'M{x+20} {y+28}l5-12 5 12Z',RED)

def lively_child(x,base,color,pose='cheer',lean=0):
    root=ET.fromstring(f'<svg xmlns="{NS}">{parts["ko-tatsu"][2]}</svg>')
    group=root.find('{'+NS+'}g')
    for n in list(group)[:2]:group.remove(n)
    for n in group.iter():
        if n.get('fill')==RED and n.tag!='{'+NS+'}circle':n.set('fill',color)
        if pose=='cheer' and n.tag=='{'+NS+'}ellipse':
            cx=float(n.get('cx'));n.tag='{'+NS+'}path';n.attrib.clear()
            n.set('d',f'M{cx-3} 2q3-5 6 0');n.set('fill','none');n.set('stroke',INK);n.set('stroke-width','2.5')
    if pose=='cheer':
        arms=[path('M11 39Q7 42 4 36L-6 17Q-8 12-4 10Q0 8 3 13L14 32Q17 37 11 39Z',SKIN),path('M33 39Q37 42 40 36L50 17Q52 12 48 10Q44 8 41 13L30 32Q27 37 33 39Z',SKIN)]
    else:
        arms=[path('M11 38Q6 38 6 43L11 53Q13 56 17 54L24 49Q28 46 25 42Q22 39 19 42L16 44 15 41Q14 38 11 38Z',SKIN),path('M33 38Q38 38 38 43L33 53Q31 56 27 54L20 49Q16 46 19 42Q22 39 25 42L28 44 29 41Q30 38 33 38Z',SKIN)]
    for a in arms:group.insert(len(group)-1,ET.fromstring(a))
    return f'<g transform="translate({x-22},{base-82}) rotate({lean} 22 82)">{ET.tostring(group,encoding="unicode")}</g>'

def flowers(x,y,count=5):
    o=[rect(x-10,y+10,count*22+12,18,'#D99F64',3)]
    for i in range(count):
        xx=x+i*22
        o += [path(f'M{xx} {y+10}V{y-8}',color=GREEN,width=2),path(f'M{xx} {y+4}q-13-14-10-2q5 8 10 2M{xx} {y}q13-14 10-2q-5 8-10 2',GREEN)]
        for dx,dy in [(-5,0),(5,0),(0,-5),(0,5)]:o.append(f'<circle cx="{xx+dx}" cy="{y-10+dy}" r="4" fill="{[RED,YELLOW,PAPER][i%3]}"/>')
        o.append(f'<circle cx="{xx}" cy="{y-10}" r="2.5" fill="{YELLOW}"/>')
    return ''.join(o)

def making_child(x,base,color,activity):
    # Hold the tool in a shaped hand instead of drawing a line through the body.
    root=ET.fromstring(f'<svg xmlns="{NS}">{parts["ko-tatsu"][2]}</svg>')
    group=root.find('{'+NS+'}g')
    for n in list(group)[:2]:group.remove(n)
    for n in group.iter():
        if n.get('fill')==RED and n.tag!='{'+NS+'}circle':n.set('fill',color)
    if activity=='drum':
        tools=path('M-14 35-53 23M12 41-42 29',color='#92754E',width=3)
        arms=[path('M11 40Q8 36 4 37L-13 32Q-18 31-18 35Q-18 38-14 39L4 47Q10 49 12 45Z',SKIN),path('M34 39Q38 40 35 46Q34 49 29 48L12 44Q7 43 8 39Q9 36 13 37L30 40Z',SKIN)]
    else:
        tools=path('M-15 30-44 12',color='#92754E',width=2.5)+path('M-44 12-49 9',color=GREEN,width=3.5)
        arms=[path('M11 39Q8 35 4 36L-12 27Q-17 25-18 29Q-19 32-15 34L1 44Q7 48 11 44Z',SKIN),f'<rect x="31.7" y="38" width="7.5" height="20" rx="3.75" fill="{SKIN}" {stroke}/>']
    for a in reversed(arms):group.insert(0,ET.fromstring(a))
    return f'<g transform="translate({x-22},{base-82})">{tools}{ET.tostring(group,encoding="unicode")}</g>'

# School-specific architecture: a broad high-roofed gym and a classroom block.
gym=[rect(32,182,536,258,PAPER),path('M12 188 92 108H510L588 188Z',BLUE),path('M92 108 300 45 510 108',BLUE)]
for x in range(65,545,80):
    gym.append(rect(x,216,58,58,'#A9E1F5',1))
    gym.append(path(f'M{x+29} 216v58'))
for x in range(70,570,55):gym.append(path(f'M{x} 186l30-74',color='#274A69',width=1.6))
gym += [path('M32 296H568',color='#C5C8BC'),rect(206,326,188,114,PAPER),rect(224,341,76,99,GREEN),rect(300,341,76,99,GREEN),path('M290 378v18M310 378v18',color=PAPER),text(300,315,'体育館',22,INK,'middle'),path('M0 442H600')]
gym += [rect(237,341,126,99,'#F6D79C'),rect(275,351,50,28,PAPER,1),rect(291,364,18,12,PAPER),f'<ellipse cx="300" cy="383" rx="12" ry="3" fill="none" stroke="{RED}" stroke-width="2.5"/>',path('M289 386l4 13h14l4-13M297 387v12M303 387v12',color=PAPER,width=1.5),path('M248 428H352M265 438q35-31 70 0',color=PAPER,width=2)]
parts['taiikukan']=(600,450,'<title>高い屋根と高窓、大きな出入口のある体育館</title>'+''.join(gym))

school=[rect(27,166,566,326,PAPER),rect(18,150,584,18,BLUE),rect(269,100,82,50,PAPER),path('M259 100H361',color=BLUE,width=9)]
for y in [207,298,389]:
    for x in [51,119,187,374,442,510]:
        school += [rect(x,y,54,55,'#A9E1F5',1),path(f'M{x+27} {y}v55M{x} {y+37}h54',color='#547478',width=1.5)]
for y in [279,370]:school.append(path(f'M27 {y}H593',color='#B8C0B7'))
school += [rect(275,407,70,85,GREEN),path('M310 407v85M298 447v13M322 447v13',color=PAPER),rect(262,397,96,10,BLUE),rect(274,196,72,147,'#A9E1F5'),path('M310 196v147M274 245h72M274 294h72',color='#547478'),f'<circle cx="310" cy="125" r="19" fill="{PAPER}" {stroke}/>',path('M310 113v12l10 6'),path('M0 492H620')]
parts['kosha']=(620,500,'<title>教室の窓が並ぶ三階建ての小学校校舎</title>'+''.join(school))

board=[rect(8,10,394,154,GREEN,3),path('M12 164H399',color='#92754E',width=7)]
# A real meeting layout in pictures: shared goal, proposed games, opinions,
# and the selected proposal. No meaningless decorative chalk lines.
for x in [37,57,77]:
    board += [f'<circle cx="{x}" cy="32" r="5" fill="none" stroke="{PAPER}" stroke-width="2"/>',path(f'M{x-7} 51v-6q7-12 14 0v6',color=PAPER,width=2)]
board += [path('M98 40H133M126 34l7 6-7 6',color=PAPER,width=2),rect(151,22,54,34,GREEN,5),path('M167 56l-8 6v-8',color=PAPER,width=2),path('M158 32h39M158 41h25',color=PAPER,width=2)]
board += [rect(24,71,98,66,PAPER,2),picture_cards(55,82),rect(146,71,98,66,PAPER,2),die(171,87,29)]
for x,color in [(36,RED),(62,BLUE),(156,YELLOW),(182,RED),(208,BLUE)]:board.append(rect(x,143,15,10,color,1))
board += [path('M251 105h24M267 98l8 7-8 7',color=YELLOW,width=2.5),rect(284,69,103,73,YELLOW,2),rect(290,75,91,61,PAPER,1),die(323,87,29),path('M362 127l5 5 11-13',color=GREEN,width=2.5)]
board += [path('M42 166v24M368 166v24'),rect(341,151,33,8,PAPER,1)]
parts['kokuban']=(410,200,'<title>みんなで遊ぶ案を絵札で提案し、意見を並べて決める学級会の黒板</title>'+''.join(board))

gate=[rect(25,32,23,240,PAPER),rect(292,32,23,240,PAPER),rect(25,36,290,58,RED),text(170,76,'うんどうかい',28,PAPER,'middle'),path('M15 272H59M282 272H325')]
for i in range(10):gate.append(rect(25+i*29,36,29,58,PAPER if i%2==0 else RED))
parts['nyutaijo']=(340,280,'<title>運動会の入場門</title>'+''.join(gate))

notice=[path('M18 47 36 18H244L262 47Z',GREEN),rect(25,45,230,137,GREEN),rect(38,57,204,112,PAPER),text(140,77,'児童会からのお知らせ',14,GREEN,'middle')]
for x,label,color in [(45,'あいさつ',RED),(111,'集会',YELLOW),(177,'そうじ',BLUE)]:
    notice += [rect(x,74,58,86,PAPER,1),rect(x,74,58,12,color)]
notice += [f'<circle cx="62" cy="111" r="6" fill="{SKIN}" {stroke}/>',f'<circle cx="84" cy="111" r="6" fill="{SKIN}" {stroke}/>',path('M53 139v-12q9-12 18 0v12M75 139v-12q9-12 18 0v12',color=RED),path('M53 94h40l-5 9-3-6H53Z',PAPER)]
for x,y in [(128,106),(150,106),(139,128)]:notice.append(f'<circle cx="{x}" cy="{y}" r="5" fill="{YELLOW}" {stroke}/>')
notice += [path('M124 113l10 10M155 113l-10 10M134 106h10',color=GREEN,width=2),path('M212 99l-13 32M192 127l17 7-6 14-18-7Z',YELLOW),path('M221 133q-13-11-13 2q9 7 13-2Z',GREEN)]
notice += [rect(44,182,13,30,GREEN),rect(223,182,13,30,GREEN),path('M15 212H265')]
parts['keijiban']=(280,220,'<title>児童会が企画するあいさつ運動や集会の掲示板</title>'+''.join(notice))

# Keep the familiar sky, trees, fence, schoolhouse, gym and yellow ground.
background=site.hiroba_naka(parts).split('<path d="M74 946')[0]
# Replace the incomplete running lane with a complete, readable oval below.
background=re.sub(r'<path d="M900 1060[^>]+/>','',background)
# Earth, rather than a yellow floor; keep character yellows unchanged.
background=re.sub(r'(<path d="M0 828[^>]*fill=")#E8C547',r'\g<1>#E9D7B2',background)
background=re.sub(r'<path d="M0 828[^>]*fill="url\(#ill-sen\)"[^>]*/>','',background)
background=background.replace('#2FBA68','#74D080').replace('opacity=".10"','opacity=".015"')
# Sunny colors are the baseline: warm sand and cream walls, fresh green,
# bright blue roofs. Never cool or mute the entire image for realism.
for old,new in {'#E9D7B2':'#F8DF9D','#FCFBF7':'#FFFEF4','#A9E1F5':'#B4E8F4','#3A6EA5':'#5897CA','#1F5C3F':'#357C50','#274A69':'#3B6C94','#C5C8BC':'#DAD7BC','#B8C0B7':'#D7D8C5'}.items():
    background=background.replace(old,new)
art=[background]
# Everyday school life gives the empty green edges a welcoming scale.
art += [flowers(1880,780,5),flowers(2330,780,5),flowers(35,809,4)]
art.append(place('ko-te',270,787,BLUE))
art.append(place('ko-te',340,805,YELLOW))

# 1. Class meeting: chalkboard, facilitator and U-shaped discussion seats.
art.append(rect(48,850,694,350,PAPER,12))
art.append(place('kokuban',289,1050))
art.append(place('gakkatsu',543,1060))
for i,(x,y) in enumerate([(658,1056),(140,1132),(300,1176),(465,1176),(640,1150)]):
    art.append(place('ko-te' if i in [0,1] else 'ko-suwaru',x,y,colors[(i+2)%4]))
    # Individual desks leave the center open for the discussion.
    desk_y=y-8
    art.append(path(f'M{x-38} {desk_y+5}v26M{x+38} {desk_y+5}v26'))
    art.append(rect(x-52,desk_y-12,104,17,PAPER,3))
    art.append(path(f'M{x-18} {desk_y-7}h29',color=BLUE))
# Two pupils offer different ideas across the open center of the meeting.
art += [path('M176 1046h55q7 0 7 7v31q0 7-7 7h-37l-12 9v-9h-6q-7 0-7-7v-31q0-7 7-7Z',PAPER),die(193,1055,25)]
art += [path('M677 924h49q7 0 7 7v38q0 7-7 7h-25l-12 10v-10h-12q-7 0-7-7v-38q0-7 7-7Z',PAPER),picture_cards(685,931)]

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
for i,(x,y) in enumerate([(1200,1112),(1265,1112),(1490,1138),(1610,1100)]):
    art.append(place('ko-hashiru',x,y,[RED,BLUE,GREEN,YELLOW][i]))
    if i>1:art.append(rect(x+22,y-41,6,23,YELLOW,2))
    art.append(path(f'M{x-11} {y-69}q12-6 25 0',color=PAPER,width=3))
art.append(rect(1225,1078,20,6,RED,2))
for x,y in [(1180,1124),(1470,1150),(1590,1112)]:art.append(path(f'M{x-18} {y}h10M{x-15} {y+6}h6',color='#BE8D45',width=1.6))
for i,x in enumerate([1190,1295,1400,1505,1610]):
    art.append(lively_child(x,982 if i<2 else 1000,colors[(i+1)%4],'cheer' if i%2==0 else 'clap',-5 if i%2==0 else 4))
art.append(place('ko-te',1720,1045,RED))
art.append(f'<circle cx="1709" cy="966" r="7" fill="{PAPER}" {stroke}/><circle cx="1688" cy="931" r="7" fill="{RED}" {stroke}/>')
for x in [790,1720]:art.append(place('hata',x,1190))

# 3. Student council: the mascot speaks, friends bring ideas, peers listen.
art.append(place('keijiban',1870,940))
art.append(place('ko-te',2315,971,RED))
art.append(place('ko-te',2390,982,GREEN))
art.append(rect(2002,960,196,18,PAPER,2))
art.append(path('M2020 978v20M2180 978v20'))
art.append(place('jidokai',2080,957))
art.append(place('ko-te',2248,987,BLUE))
art.append(place('ko-tatsu',1936,1024,GREEN))
art.append(rect(1924,973,25,32,PAPER,1))
art.append(path('M1929 982h15M1929 990h15',color=GREEN))
for row,(base,start,count) in enumerate([(1080,1808,6),(1128,1840,6),(1174,1875,5)]):
    for i in range(count):
        # Loose groups with a few raised hands feel like a pupil-led gathering.
        xx=start+i*68;yy=base+(i%3-1)*7
        if (row,i) in [(0,4),(1,0)]:art.append(place('ko-te',xx,yy,colors[(i+row)%4]))
        else:art.append(place('ko-ushiro',xx,yy,colors[(i+row)%4]))
art.append(lively_child(2268,1150,YELLOW,'clap',-4))

# 4. Clubs: music, painting, science, and exercise around the yellow mascot.
art.append(place('taiko',2530,975,scale=.72))
art.append(making_child(2620,966,RED,'drum'))
art.append(place('easel',2780,981,scale=.68))
art.append(making_child(2865,982,BLUE,'paint'))
art.append(place('ko-tatsu',2997,978,GREEN))
art.append(place('ko-te',3147,978,YELLOW))
art.append(rect(2970,934,210,14,PAPER,2))
art.append(path('M2984 948v35M3166 948v35'))
art.append(path('M3058 899h12v12l9 18h-29l8-18Z','#A9E1F5'))
art.append(path('M3110 903v21q0 8 7 8t7-8v-21M3107 903h20',PAPER))
art.append(path('M3111 921h12',color=BLUE,width=3))
art.append(place('club',2485,1156))
art.append(lively_child(2940,1070,YELLOW,'clap',-5))
art.append(place('ko-te',2565,1090,BLUE))
# Music and an exhibited drawing are readable actions, without written labels.
art.append(path('M2591 867v-22l18-4v21',color=BLUE,width=2.5))
art.append(f'<ellipse cx="2587" cy="868" rx="5" ry="3.5" fill="{BLUE}"/><ellipse cx="2605" cy="863" rx="5" ry="3.5" fill="{BLUE}"/>')
art.append(rect(2570,1010,38,48,PAPER,2))
art.append(path('M2589 1048v-14M2579 1040q10 3 10 8M2599 1040q-10 3-10 8',color=GREEN,width=2))
art.append(f'<circle cx="2589" cy="1028" r="7" fill="{RED}"/><circle cx="2589" cy="1028" r="3" fill="{YELLOW}"/>')
art.append(place('ko-tatsu',2700,1130,RED))
art.append(place('ko-tatsu',2820,1130,BLUE))
art.append(rect(2656,1098,210,17,PAPER,2))
art.append(path('M2672 1115v47M2850 1115v47'))
art.append(path('M2724 1078H2797L2810 1098H2711Z',YELLOW))
for x in [2735,2747,2759,2771,2783]:art.append(path(f'M{x} 1078l{(x-2760)*.3} 20',color=GREEN,width=1))
for y in [1083,1088,1093]:art.append(path(f'M{2724-(y-1078)*.65} {y}H{2797+(y-1078)*.65}',color=GREEN,width=1))
for x,y,c in [(2737,1084,INK),(2750,1092,PAPER),(2773,1088,INK),(2785,1084,PAPER)]:
    art.append(f'<ellipse cx="{x}" cy="{y}" rx="3.5" ry="2.5" fill="{c}" stroke="{INK}" stroke-width="1"/>')
art.append(place('ko-tatsu',3020,1150,BLUE))
art.append(place('ko-suwaru',3130,1150,GREEN))
# A familiar low worktable with paper and a little airplane.
art.append(rect(2970,1121,197,18,PAPER,3))
art.append(path('M2983 1139v42M3152 1139v42'))
art.append(path('M3048 1109l48-25-18 32-8-10Z',PAPER))
art.append(path('M3070 1106l26-22',color=BLUE))
art.append(rect(2993,1106,31,13,YELLOW,1))

content='\n'.join(art)
content=content.replace('#FCFBF7','#FFFEF4')
assert '<text' not in content, 'Artwork should communicate without text labels'
assert 'ns0:' not in content
title='特活広場：学級会・学校行事・児童会・クラブ活動が広がる学校'
def svg(box):return f'<svg xmlns="{NS}" viewBox="{box}"><title>{title}</title>{content}</svg>'
(HERE/'school.svg').write_text(svg('0 0 3200 1200'))
(HERE/'school-close.svg').write_text(svg('0 310 3200 890'))
for key,box in [('class','20 820 750 380'),('events','765 750 990 450'),('council','1740 750 680 450'),('club','2410 750 790 450')]:
    (HERE/f'detail-{key}.svg').write_text(svg(box))
# A review sheet makes the important small details visible without a website.
panels=[]
for i,(key,title,sub,color) in enumerate([('class','学級活動','話し合って、決める',GREEN),('events','学校行事','力を合わせて、取り組む',RED),('council','児童会活動','学校全体に、働きかける',BLUE),('club','クラブ活動','好きなことを、仲間と深める','#7D641A')]):
    x=30+(i%2)*990;y=25+(i//2)*595
    piece=ET.parse(HERE/f'detail-{key}.svg').getroot()
    body=''.join(ET.tostring(n,encoding='unicode') for n in piece)
    body=body.replace('ill-ami',f'{key}-ami').replace('ill-sen',f'{key}-sen')
    panels += [text(x,y+30,title,28,color),text(x+220,y+29,sub,20,INK),f'<svg x="{x}" y="{y+54}" width="950" height="510" viewBox="{piece.get("viewBox")}" preserveAspectRatio="xMidYMid meet">{body}</svg>']
(HERE/'four-activities.svg').write_text(f'<svg xmlns="{NS}" viewBox="0 0 2020 1230"><rect width="2020" height="1230" fill="{PAPER}"/>'+''.join(panels)+'</svg>')
print('Created panorama, closer view and four activity details.')
