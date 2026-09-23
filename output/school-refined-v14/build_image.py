"""One coherent campus, with four spatially grouped activities."""
from pathlib import Path
source=Path(__file__).resolve().parent.parent/'school-refined-v12/build_image.py'
prefix=source.read_text().split('a=[rect(0,0,3200')[0]
exec(compile(prefix,str(source),'exec'))

CREAM='#FFFEF4';SAND='#F8DF9D';WOOD='#EDC58B';SKY='#B4E8F4'
def label(x,y,s,size=20,color=CREAM,anchor='start'):
    return f'<text x="{x}" y="{y}" fill="{color}" font-family="Hiragino Sans, sans-serif" font-size="{size}" text-anchor="{anchor}">{escape(s)}</text>'
def desk(x,y,w=110):
    return path(f'M{x-w/2+10} {y}v55M{x+w/2-10} {y}v55')+rect(x-w/2,y-12,w,20,WOOD,2)+rect(x-21,y-21,42,9,CREAM,1)
def scaled_back(x,y,c,s=1):
    return f'<g transform="translate({x} {y}) scale({s}) translate({-x} {-y})">{seat_back(x,y,c)}</g>'
def pupil_side(x,y,c,right=True,raised=False):
    # Seated three-quarter view: the feet, hands and gaze turn toward the circle.
    direction=1 if right else -1
    o=[rect(-26,-51,12,41,WOOD,2),rect(-27,-18,49,10,WOOD,2),path('M-24-8v19M18-8v19'),
       path('M-11-22H12Q21-22 21-12V4H10V-9H-11Z',SKIN),rect(9,1,25,11,CREAM,3),
       path('M-8-65Q-24-64-23-49V-20H6V-49Q6-64-8-65Z',c)]
    if raised:o.append(path('M0-54Q5-60 10-56L15-66 17-85Q18-92 23-90Q28-89 27-83L25-62 17-44Q12-36 5-42Z',SKIN))
    else:o.append(path('M0-54Q7-57 10-50L15-36H28Q35-36 35-31Q35-26 28-26H9Q3-26 0-34L-5-45Q-7-52 0-54Z',SKIN))
    o += [f'<circle cx="-5" cy="-83" r="21" fill="{SKIN}" {stroke}/>',
          path('M-26-82Q-28-104-7-105Q12-107 15-91L7-93Q-1-83-20-87L-18-94Z',INK),
          f'<ellipse cx="1" cy="-81" rx="2.2" ry="3" fill="{INK}"/><ellipse cx="12" cy="-81" rx="1.8" ry="2.7" fill="{INK}"/>',path('M3-72q5 4 9-1',width=2),f'<circle cx="-9" cy="-74" r="3" fill="{RED}" opacity=".6"/>']
    return f'<g transform="translate({x} {y}) scale({direction*1.35} 1.35)">'+''.join(o)+'</g>'
def chalknote(x,y,w,s,color):
    return rect(x,y,w,30,color,2)+label(x+w/2,y+21,s,17,INK,'middle')

a=[rect(0,0,3200,1550,SKY)]
for x,y,s in [(170,95,.65),(1180,116,.65),(2100,81,.5),(2975,112,.7)]:a.append(place('kumo',x,y,scale=s))
a.append(path('M0 425Q850 360 1700 419T3200 408V660H0Z','#74D080'))
for i,x in enumerate(range(0,3300,145)):a.append(place('ki' if i%3 else 'ki-hoso',x,530+(i%2)*15,scale=.97))
for x in [300,900,1500,2100,2700,3300]:a.append(place('fence',x,566))

# A Japanese school gym: barrel roof, clerestory windows, solid double doors.
# The front is recognisable architecture, not a small court drawn inside a door.
g=[path('M40 234Q350 10 660 234V500H40Z',CREAM),
   path('M20 212Q350-38 680 212L660 234Q350 10 40 234Z','#5897CA'),
   path('M70 250Q350 70 630 250V268H70Z',SKY)]
for x in range(110,630,65):
    g.append(f'<path d="M{x} 100V268" clip-path="url(#gymglass)" fill="none" stroke="{CREAM}" stroke-width="6"/>')
g += [f'<defs><clipPath id="gymglass"><path d="M70 250Q350 70 630 250V268H70Z"/></clipPath></defs>',
      rect(209,322,280,178,'#E5D3A7'),rect(227,334,245,166,GREEN),path('M349 334V500',color=CREAM),path('M332 404v28M366 404v28',color=YELLOW,width=4),
      rect(180,306,338,20,CREAM),rect(76,341,75,104,SKY),rect(549,341,75,104,SKY),
      path('M113 341v104M76 393h75M586 341v104M549 393h75'),
      path('M35 505H665'),path('M194 510H500',color='#D5B67F',width=8)]
a.append('<g transform="translate(55 85) scale(1.38 1.06)">'+''.join(g)+'</g>')
a.append(building('kosha',2470,604,2.02,1.10))
# A covered passage physically connects the two school buildings.
a.append(rect(950,493,958,21,'#5897CA'))
for x in [970,1260,1510,1760,1890]:a.append(rect(x,514,12,95,CREAM))
a.append(path('M950 607H1910',color='#D5B67F',width=6))

a.append(path('M0 647Q770 612 1540 640T3200 628V1550H0Z',SAND))
# Linked paths and a planted border establish places before placing people.
a.append(path('M0 670Q1180 614 3200 665V730Q1240 689 0 744Z','#FFF0C9',color='#E8CF91',width=2))
a.append(path('M2105 709Q2220 982 2120 1550H2250Q2330 1100 2230 709Z','#FFF0C9',color='#E8CF91',width=2))
for x in [95,575,2930]:a.append(flowers(x,620,7))

# CLASS MEETING — one cutaway classroom, with a circle of inward-facing desks.
a += [rect(45,765,912,682,'#F3D6A4'),rect(45,765,912,360,CREAM),
      rect(45,751,912,25,'#5897CA'),rect(45,776,22,671,CREAM),rect(935,776,22,671,CREAM)]
for y in [1180,1270,1360,1445]:a.append(path(f'M68 {y}H934',color='#E5C38D',width=1.5))
# Blackboard contains actual meeting records, not a symbolic flow chart.
a += [rect(111,807,660,242,GREEN,3),path('M109 1052H774',color='#A77C4D',width=9),
      label(132,838,'議題　みんなで楽しむ会をしよう',24),path('M131 850H749',color=CREAM,width=1.7)]
for x,t in [(132,'出し合う'),(344,'くらべ合う'),(567,'決まったこと')]:a.append(label(x,881,t,20))
for x in [324,548]:a.append(path(f'M{x} 864V1030',color='#A6CAB1',width=1.3))
a += [chalknote(132,901,174,'クイズ','#FFFEF4'),chalknote(132,948,174,'宝さがし','#FFFEF4'),
      chalknote(344,901,184,'みんなでできる','#FBEBA4'),chalknote(344,948,184,'協力できる','#F9D0B3'),
      chalknote(567,923,182,'チームで宝さがし','#FBEBA4'),
      path('M589 976q-3-10 5-15q8-4 11 5q4-9 12-5q8 5 4 12l-16 16Z',fill='none',color=CREAM,width=2),
      path('M639 973l8 8 19-24',color=CREAM,width=3),rect(716,1037,40,9,CREAM,1)]
a += [rect(801,815,98,156,SKY),path('M850 815v156M801 891h98',color=CREAM,width=6)]
# Child chairperson and recorder stay together at the front.
a.append(place('gakkatsu',344,1179,scale=1.34))
a.append(child('ko-tatsu',578,1152,BLUE,1.35));a.append(desk(578,1125,152))
a.append(child('ko-te',805,1118,YELLOW,1.32))
a.append(path('M788 1037 749 1004',color='#A77C4D',width=3))
# Side rows face each other; foreground row faces the chairperson.
for x,y,c,right,raised in [(152,1268,RED,True,True),(152,1407,BLUE,True,False),(837,1268,GREEN,False,False),(837,1407,YELLOW,False,True)]:
    a.append(pupil_side(x,y,c,right,raised));a.append(desk(x+(56 if right else -56),y-41,104))
for i,x in enumerate([364,514,664]):
    a.append(desk(x,1330,114));a.append(scaled_back(x,1440,colors[i],1.04))

# SPORTS DAY — runners follow the visible front lanes; supporters face the track.
orig,_=site.load_buhin();parts['nyutaijo']=orig['nyutaijo']
for x in [1170,1605,1990]:a.append(place('bankokki',x,787,scale=.9))
a.append(place('nyutaijo',1555,775,scale=.88))
a.append(f'<ellipse cx="1580" cy="1104" rx="523" ry="254" fill="none" stroke="{CREAM}" stroke-width="9"/>')
a.append(f'<ellipse cx="1580" cy="1104" rx="478" ry="212" fill="none" stroke="{CREAM}" stroke-width="5"/>')
a.append(f'<ellipse cx="1580" cy="1104" rx="433" ry="170" fill="none" stroke="{CREAM}" stroke-width="4"/>')
# Painted start / finish line crosses the near lanes.
a.append(path('M1895 1234l80 61M1908 1221l84 61',color=CREAM,width=5))
# Pupils cheering from the inside edge, an organised team rather than a loose row.
for i,x in enumerate([1355,1450,1545,1640,1735]):
    a.append(lively(x,1050+(i%2)*8,colors[i%4],'cheer' if i%2==0 else 'clap',(-1 if i%2 else 1)*4))
a.append(leader('gyoji',1174,1084))
# Baton exchange on the near straight; a second pair follows in the outer lane.
for x,y,c in [(1415,1305,RED),(1500,1310,RED),(1752,1300,BLUE),(1828,1276,BLUE)]:
    a.append(child('ko-hashiru',x,y,c,1.62))
    a.append(path(f'M{x-20} {y-106}q20-11 42 0',color=CREAM,width=5))
a.append(rect(1450,1252,25,8,YELLOW,2));a.append(rect(1787,1244,20,7,YELLOW,2))
for x,y in [(1400,1320),(1735,1320)]:a.append(path(f'M{x-28} {y}h18M{x-21} {y+9}h12',color='#CCA05F',width=2))
for i,x in enumerate([1275,1370,1470,1570,1670,1770,1870]):
    a.append(scaled_back(x,1512,colors[(i+1)%4],.92))
for x in [1110,2060]:a.append(place('hata',x,1450,scale=.8))

# STUDENT COUNCIL — a small stage directly outside the school entrance.
# Speaker, pupil organisers and both rows of listeners share one paved court.
a.append(rect(2300,705,829,382,'#FFF0C9',15))
a.append(rect(2477,741,559,47,WOOD,2));a.append(rect(2477,741,559,12,'#F5D49E',2))
a.append(rect(3028,768,65,24,WOOD,1));a.append(rect(3051,792,65,22,WOOD,1))
a.append(place('jidokai',2706,740,scale=1.34))
a.append(child('ko-tatsu',2841,738,RED,1.23));a.append(rect(2821,682,41,35,CREAM,1))
a.append(child('ko-te',2963,737,GREEN,1.2))
a.append(place('keijiban',2373,803,scale=.69))
for j,y in enumerate([925,1052]):
    for i,x in enumerate([2448,2550,2652,2754,2856,2958]):a.append(scaled_back(x+(j%2)*16,y,colors[(i+j)%4],.94))
# One organiser addresses the audience from beside the stage.
a.append(child('ko-te',3090,952,BLUE,1.25))

# CLUBS — one sheltered work area, two adjoining tables and shared supplies.
a += [rect(2312,1140,810,339,'#F3D6A4',3),rect(2312,1114,810,26,'#5897CA',2),
      rect(2312,1140,15,338,CREAM),rect(3107,1140,15,338,CREAM)]
a.append(place('club',2378,1363,scale=1.22))
# The easel and painter form a single action; brush tip reaches the canvas.
a.append(place('easel',2493,1316,scale=.92))
a.append(f'<g transform="translate(2622 1314) scale(1.4) translate(-2622 -1314)">{making_child(2622,1314,RED,"paint")}</g>')
a.append(child('ko-tatsu',2804,1293,BLUE,1.38));a.append(child('ko-tatsu',3011,1293,YELLOW,1.38))
a.append(rect(2738,1262,335,29,WOOD,3));a.append(path('M2760 1291v91M3054 1291v91'))
# A shared model is visibly on the worktable, not floating between pupils.
a += [rect(2850,1218,90,42,CREAM,1),path('M2839 1218 2895 1184 2951 1218Z',RED),rect(2884,1236,20,24,GREEN,1),
      rect(2758,1244,54,17,YELLOW,1),rect(2991,1250,53,11,CREAM,1),
      path('M2819 1254l15-26',color=BLUE,width=5),path('M3007 1245l20-17',color=RED,width=4)]
# A seated sketcher shares the same work area; tools stay on the nearby shelf.
a.append(place('ko-suwaru',2498,1445,GREEN,1.65))
a.append(path('M2478 1386l45 9-6 28-45-9Z',CREAM))
a.append(path('M2487 1396l15 3M2484 1406l15 3',color=BLUE,width=2))
a.append(path('M2520 1386l-15 17',color=RED,width=4))
a.append(rect(2633,1390,106,23,WOOD,2));a.append(path('M2644 1413v48M2722 1413v48'))
for x,c in [(2653,BLUE),(2684,RED),(2715,YELLOW)]:a.append(rect(x-9,1367,18,24,c,2))
for x in [2334,3050]:a.append(flowers(x,1482,3))

def blossom(x,y,color,size=1):
    # Deliberate, repeating petal shapes match the site's flat line illustration.
    o=[]
    for dx,dy in [(0,-9),(8,-3),(5,7),(-5,7),(-8,-3)]:
        o.append(f'<ellipse cx="{dx}" cy="{dy}" rx="6.4" ry="6.6" fill="{color}" stroke="{INK}" stroke-width="1.7"/>')
    o.append(f'<circle r="4.5" fill="{YELLOW}" stroke="{INK}" stroke-width="1.5"/>')
    return f'<g transform="translate({x} {y}) scale({size})">'+''.join(o)+'</g>'

def flowerbed(x,y,w,count):
    # y is ground level. Layer foliage, upright stems and blooms above low brick.
    o=[path(f'M{x+6} {y-10}Q{x} {y-39} {x+27} {y-34}H{x+w-25}Q{x+w+3} {y-32} {x+w-5} {y-8}Z','#74D080')]
    palette=['#E98970',CREAM,YELLOW,'#F1A3AC',RED]
    for i in range(count):
        xx=x+19+i*(w-38)/(count-1);top=y-49-[0,14,5,20,8][i%5]
        o += [path(f'M{xx} {y-9}V{top+8}',color=GREEN,width=3),
              path(f'M{xx} {y-25}q-19-24-21-9q1 14 21 9M{xx} {y-19}q20-25 22-11q-1 15-22 11',fill='#64B86C',color=GREEN,width=1.5),
              blossom(xx,top,palette[i%5],.82+(i%3)*.08)]
    o += [rect(x,y-9,w,24,'#DDA476',2),path(f'M{x} {y+3}H{x+w}',color='#AE7952',width=1.4)]
    for xx in range(int(x)+28,int(x+w),57):o.append(path(f'M{xx} {y-9}v12M{xx+28} {y+3}v12',color='#AE7952',width=1.4))
    return ''.join(o)

# Flowers frame the activities, leaving the track, board and sightlines clear.
a.append(flowerbed(75,1529,867,25))
a.append(flowerbed(2325,1529,786,23))
# Planting in front of the buildings makes the whole campus feel cared for.
a.append(flowerbed(86,633,190,6))
a.append(flowerbed(585,633,224,7))
a.append(flowerbed(2060,639,218,7))
a.append(flowerbed(2927,636,209,7))
# A flowering entrance arch uses the already established school-event gateway.
for x,y,c in [(1450,618,CREAM),(1478,581,'#F1A3AC'),(1520,561,YELLOW),(1564,561,CREAM),(1606,579,'#E98970'),(1640,614,YELLOW)]:
    a.append(path(f'M{x-7} {y+5}q-19-16-23-5q1 13 23 5M{x+7} {y+5}q20-16 23-5q-1 13-23 5','#64B86C',color=GREEN,width=1.5))
    a.append(blossom(x,y,c,.91))
# One small vase on the classroom windowsill, with the blackboard left intact.
a.append(path('M831 944h35l-5 29h-25Z','#E98970'))
for x,y,c in [(837,923,YELLOW),(851,913,CREAM),(862,928,'#E98970')]:
    a.append(path(f'M{x} {y}L849 946',color=GREEN,width=2));a.append(blossom(x,y,c,.55))

# Friends meet along the continuous school path, in pairs rather than scattered.
a.append(child('ko-te',1100,705,BLUE,1.08))
a.append(child('ko-tatsu',1171,705,YELLOW,1.08))
a.append(child('ko-tatsu',1875,705,GREEN,1.08))
a.append(child('ko-te',1946,705,RED,1.08))
# A second, staggered cluster cheers the relay from the infield.
for i,x in enumerate([1400,1565,1730]):
    a.append(lively(x,1159,colors[(i+1)%4],'clap',[-4,3,-3][i]))
# A pair works on paper crafts at the same low table, alongside the painters.
for x,c in [(2832,BLUE),(3030,YELLOW)]:a.append(place('ko-suwaru',x,1460,c,1.55))
a.append(rect(2771,1404,313,20,WOOD,2));a.append(path('M2790 1424v49M3062 1424v49'))
a.append(path('M2906 1403l35-34 38 34Z',CREAM))
a.append(path('M2906 1403l35-13 38 13M2941 1369v21',color=BLUE,width=2))
a.append(path('M2800 1399l26-4 11 8-27 1Z','#F1A3AC'))
a.append(path('M2990 1398l34-9 13 11-28 3Z',YELLOW))

content='\n'.join(a).replace('#FCFBF7',CREAM).replace('#2FBA68','#74D080')
assert 'ns0:' not in content and '<image' not in content
def output(name,box):
    (HERE/f'{name}.svg').write_text(f'<svg xmlns="{NS}" viewBox="{box}"><title>学校の場所と活動をまとまりで描いた特活広場</title>{content}</svg>')
output('school','0 0 3200 1550')
output('detail-class','35 740 935 725')
output('detail-gym','50 120 970 535')
output('detail-council-club','2280 540 875 990')
print('v14 built: flowering campus, more shared activities, preserved four-area layout')
