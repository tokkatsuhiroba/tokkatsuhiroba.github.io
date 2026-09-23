"""Reference-layout school panorama; native flat SVG style, warm, wordless."""
from pathlib import Path
# Reuse the authored character and building geometry, not the older composition.
source=Path(__file__).resolve().parent.parent/'school-refined-v11-lively/build_image.py'
prefix=source.read_text().split('# Keep the familiar sky')[0]
prefix=prefix.replace('range(70,570,55)','range(70,500,55)')
exec(compile(prefix,str(source),'exec'))

# Broad buildings are placed high in the picture; activity areas occupy the yard.
def building(key,x,base,sx,sy):
    w,h,b=parts[key]
    b=b.replace('#FCFBF7','#FFFEF4').replace('#3A6EA5','#5897CA').replace('#A9E1F5','#B4E8F4').replace('#274A69','#3B6C94')
    if key=='kosha':
        root=ET.fromstring(f'<g xmlns="{NS}">{b}</g>')
        for n in root.iter():
            if (n.tag=='{'+NS+'}circle' and n.get('cx')=='310') or n.get('d')=='M310 113v12l10 6':
                n.set('transform',f'translate(310 125) scale({sy/sx} 1) translate(-310 -125)')
        b=ET.tostring(root,encoding='unicode')
    return f'<g transform="translate({x-w*sx/2},{base-(h-8)*sy}) scale({sx},{sy})">{b}</g>'

def child(key,x,base,color=BLUE,scale=1.28):return place(key,x,base,color,scale)
def leader(key,x,base):return place(key,x,base,scale=1.48)
def lively(x,base,color,pose='cheer',lean=0):
    # Scale the existing expression/gesture about its ground contact.
    return f'<g transform="translate({x},{base}) scale(1.28) translate({-x},{-base})">'+lively_child(x,base,color,pose,lean)+'</g>'
def seat_back(x,base,color):
    s=1.35;X=x-22*s;Y=base-82*s
    b=[rect(6,48,34,22,'#D5B77A',2),rect(8,64,5,18,'#D5B77A'),rect(33,64,5,18,'#D5B77A'),rect(12,55,9,21,SKIN,3),rect(24,55,9,21,SKIN,3),rect(10,73,13,8,PAPER,3),rect(24,73,13,8,PAPER,3),path('M22 29q-16 0-16 15v16h32V44q0-15-16-15Z',color),rect(2,38,7,22,SKIN,3),rect(35,38,7,22,SKIN,3),f'<circle cx="22" cy="16" r="15" fill="{INK}" {stroke}/>',rect(4,56,36,10,'#D5B77A',2)]
    return f'<g transform="translate({X},{Y}) scale({s})">'+''.join(b)+'</g>'

a=[rect(0,0,3200,1333,'#B4E8F4')]
# Sky, trees and fence sit behind both buildings.
for x,y,s in [(150,92,.7),(1120,105,.8),(1700,96,.6),(2910,115,.65)]:a.append(place('kumo',x,y,scale=s))
a.append(path('M0 365Q750 310 1500 355T3200 355V580H0Z','#357C50'))
a.append(path('M0 420Q850 375 1640 420T3200 410V680H0Z','#74D080'))
for i,x in enumerate(range(10,3260,150)):
    a.append(place('ki' if i%3 else 'ki-hoso',x,490+(i%3)*8,scale=.95))
for x in [300,900,1500,2100,2700,3300]:a.append(place('fence',x,508))
a.append(building('taiikukan',555,506,1.44,1))
a.append(building('kosha',2420,515,1.57,1.04))
a.append(path('M0 530Q800 497 1630 530T3200 526V1333H0Z','#F8DF9D'))
# Shrubs and flowers at the buildings give the playground its familiar edges.
for x in [94,824,2070,2770]:a.append(flowers(x,514,5))

# Open-front classroom, not a detached white information card.
a += [rect(22,561,716,437,'#F3D6A4'),rect(22,561,716,24,'#FFFEF4'),rect(22,585,25,413,'#FFFEF4'),rect(714,585,24,413,'#FFFEF4'),path('M48 926H714',color='#DBBB83',width=2)]
a.append(place('kokuban',350,812,scale=1.24))
# Low bookcase and a wall shelf make this read as a classroom.
a.append(rect(58,736,69,163,'#CFA375',2))
for y in [749,806,863]:
    a.append(path(f'M62 {y+35}h61',color=INK))
    for j in range(5):a.append(rect(65+j*11,y,8,31,colors[j%4],1))
a.append(leader('gakkatsu',377,927))
a.append(child('ko-te',595,937,BLUE))
for x,y,c in [(143,1018,BLUE),(284,1045,RED),(485,1045,YELLOW),(651,1020,GREEN)]:
    a.append(child('ko-suwaru',x,y,c))
    a.append(path(f'M{x-42} {y-20}v44M{x+42} {y-20}v44'))
    a.append(rect(x-54,y-31,108,16,'#F0CA87',2))
    a.append(rect(x-19,y-40,36,9,PAPER,1))
a.append(path('M630 753h62q9 0 9 9v46q0 9-9 9h-29l-18 14v-14h-15q-9 0-9-9v-46q0-9 9-9Z',PAPER))
a.append(die(644,767,32))

# Sports day: a large continuous track and a foreground row of cheering peers.
# Recover the original rounded gateway to preserve the site's friendly motif.
orig_parts,_=site.load_buhin();parts['nyutaijo']=orig_parts['nyutaijo']
for x in [1030,1510,1920]:a.append(place('bankokki',x,572,scale=.9))
a.append(place('nyutaijo',1430,620,scale=1.05))
a.append(f'<ellipse cx="1390" cy="823" rx="491" ry="159" fill="none" stroke="{PAPER}" stroke-width="10"/>')
a.append(f'<ellipse cx="1390" cy="823" rx="444" ry="129" fill="none" stroke="{PAPER}" stroke-width="5"/>')
a.append(leader('gyoji',864,814))
for i,(x,y) in enumerate([(1155,870),(1240,870),(1480,853),(1680,825)]):
    a.append(child('ko-hashiru',x,y,colors[i]))
    a.append(path(f'M{x-14} {y-88}q16-8 32 0',color=PAPER,width=4))
    if i>1:a.append(rect(x+27,y-53,7,28,YELLOW,2))
a.append(rect(1188,827,25,7,RED,2))
for i,x in enumerate([940,1090,1240,1390,1540,1690]):
    a.append(lively(x,1060+(i%2)*12,colors[i%4],'cheer' if i%2==0 else 'clap',-6 if i%2==0 else 5))
for x in [817,1824]:a.append(place('hata',x,1110,scale=.9))

# Student council: children run a gathering, a few peers participate at the front.
a.append(place('keijiban',2022,692,scale=1.2))
a.append(rect(2010,816,382,25,'#D5AC73',2))
a.append(path('M2037 841v50M2367 841v50',color=INK,width=3))
a.append(leader('jidokai',2144,811))
a.append(child('ko-te',2424,835,BLUE))
a.append(child('ko-tatsu',2340,722,BLUE))
# One representative brings a proposal sheet to the group.
a.append(child('ko-tatsu',1970,908,GREEN))
a.append(rect(1951,835,39,43,PAPER,2));a.append(die(1959,844,21))
for i,x in enumerate([1980,2080,2180,2280,2380]):a.append(seat_back(x,1060+(i%2)*8,colors[i%4]))
a.append(lively(2468,1030,GREEN,'clap',-5))

# Clubs: painting, music, model-making and caring for the shared flowerbed.
a.append(leader('club',2632,773))
a.append(place('easel',2850,856,scale=.91))
# Hand/tool relationships come from the corrected authored pupil poses.
a.append(f'<g transform="translate(2990 846) scale(1.28) translate(-2990 -846)">'+making_child(2990,846,RED,'paint')+'</g>')
a.append(place('taiko',3110,674,scale=.94))
a.append(f'<g transform="translate(3005 667) scale(-1.28 1.28) translate(-3005 -667)">'+making_child(3005,667,BLUE,'drum')+'</g>')
a.append(path('M2940 553v-24l21-5v22',color=BLUE,width=3))
a.append(f'<ellipse cx="2935" cy="554" rx="6" ry="4" fill="{BLUE}"/><ellipse cx="2956" cy="548" rx="6" ry="4" fill="{BLUE}"/>')
a.append(child('ko-tatsu',2828,1018,GREEN));a.append(child('ko-tatsu',3098,1018,YELLOW))
a.append(rect(2750,984,410,24,'#D5AC73',3));a.append(path('M2774 1008v48M3140 1008v48'))
a.append(path('M2932 960l86-49-27 61-24-21Z',PAPER));a.append(path('M2967 951l51-40',color=BLUE))
a.append(rect(2862,965,49,18,YELLOW,2));a.append(rect(3120,974,28,8,PAPER,1))
a.append(lively(2673,1000,RED,'clap',-5))

# Foreground: gate, bench, drinking taps and gardening. These give the map depth.
for x in [108,690]:a += [rect(x,1113,74,198,PAPER,3),rect(x-7,1104,88,21,PAPER,2)]
for x in [183,534]:
    a.append(rect(x,1160,155,117,GREEN,2))
    for xx in range(x+14,x+152,24):a.append(rect(xx,1169,7,98,YELLOW,1))
a.append(child('ko-tatsu',400,1303,BLUE));a.append(child('ko-te',523,1280,RED))
# A small schoolbag is a familiar, readable everyday detail.
a.append(rect(364,1242,31,41,BLUE,4));a.append(path('M370 1242v-8h17v8',color=BLUE,width=4))
a += [rect(1230,1227,257,27,'#D5AC73',2),path('M1250 1254v57M1467 1254v57'),rect(1267,1169,162,20,'#D5AC73',2),path('M1280 1189v38M1417 1189v38')]
a.append(path('M1270 1226q0-38 39-38q34 0 34 38Z',PAPER));a.append(path('M1309 1188v38h34q0-38-34-38Z',RED));a.append(path('M1265 1227h84',color=INK))
a.append(rect(1424,1177,50,66,BLUE,5));a.append(path('M1434 1177v-11h28v11M1449 1179v61',color=PAPER,width=3))
a += [rect(1746,1181,204,110,PAPER,4),rect(1734,1266,228,30,PAPER,4)]
for x in [1790,1885]:
    a.append(path(f'M{x} 1197v18h16',color='#587D84',width=7))
    a.append(path(f'M{x+15} 1218v39',color='#70BEDD',width=3))
a.append(child('ko-tatsu',2014,1303,GREEN));a.append(child('ko-tatsu',2140,1307,YELLOW))
a.append(rect(2149,1225,37,48,BLUE,4))
# Flowerbed is shared school life, while the nearby hands show the gardening.
a.append(child('ko-tatsu',2666,1204,GREEN));a.append(child('ko-tatsu',2950,1204,RED))
a.append(rect(2690,1150,36,29,BLUE,5));a.append(path('M2726 1158l30 16-4 9-28-10',BLUE));a.append(path('M2694 1152q-17-19-21 6',color=BLUE,width=4))
for i in range(4):a.append(path(f'M{2751+i*5} {1184+i*2}l{4+i} 23',color='#70BEDD',width=2))
a.append(flowers(2550,1260,26))
a.append(rect(2950,1169,26,25,'#D99F64',2));a.append(path('M2963 1169v-22',color=GREEN,width=2));a.append(f'<circle cx="2963" cy="1144" r="8" fill="{YELLOW}"/>')

content='\n'.join(a).replace('#FCFBF7','#FFFEF4').replace('#2FBA68','#74D080')
assert '<text' not in content and 'ns0:' not in content

def output(name,box):
    (HERE/f'{name}.svg').write_text(f'<svg xmlns="{NS}" viewBox="{box}"><title>明るい学校の広場で、話し合い・運動会・児童会の集会・クラブ活動に取り組む子どもたち</title>{content}</svg>')
output('school','0 0 3200 1333')
for name,box in [('detail-class','0 520 790 580'),('detail-events','770 510 1130 610'),('detail-council','1890 490 620 635'),('detail-club','2500 500 700 620')]:output(name,box)
print('Built flat illustration with reference-led composition; no visible text.')
