"""Refine the site's original editable SVGs without changing the live assets."""
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parent.parent
NS='http://www.w3.org/2000/svg'
ET.register_namespace('',NS)

def element(tag,**attrs):
    return ET.Element('{'+NS+'}'+tag,{k.replace('_','-'):str(v) for k,v in attrs.items()})

characters=[('gakkatsu','学活くん'),('gyoji','行人'),('jidokai','児童会ちゃん'),('club','クラブマン')]
for name,title in characters:
    svg=ET.fromstring((PROJECT/'src/ill/kyara'/f'{name}.svg').read_text())
    group=svg.find('{'+NS+'}g')
    group.set('stroke-width','2.2')
    # Keep the existing body, proportions, props and nine-color palette.
    for node in list(group):
        tag=node.tag.split('}')[-1]
        if tag=='circle' and node.get('r')=='2.9':
            node.tag='{'+NS+'}ellipse';node.attrib.pop('r')
            node.set('rx','2.65');node.set('ry','3.45')
        if tag=='circle' and node.get('r')=='3.4':
            node.set('r','2.8');node.set('opacity','.65')
        if name=='jidokai' and tag=='rect' and node.get('x')=='66':
            node.tag='{'+NS+'}path';node.attrib.clear()
            node.set('d','M69 59q-5 0-5 5l2 15q1 7 7 5l9-11q3-4-1-7-4-2-6 2l-2 3-1-8q0-4-3-4z')
            node.set('fill','#F6D8B8')
        if tag=='path' and node.get('stroke')=='none' and node.get('d','').startswith('M22 '):
            node.set('d','M22 28C22 14 33 5 48 5c15 0 25 9 26 23l-7-6-2 5-4-10c-7 7-17 9-28 8l4-6c-5 3-10 6-15 9z')
        if tag=='path' and node.get('stroke')=='none' and node.get('d','').startswith(('M41 ','M40 ')):
            if name in ('gyoji','club'):
                y=41 if name=='gyoji' else 42
                node.set('d',f'M41 {y}h14c-1 10-12 10-14 0z')
            else:
                y=41 if name=='gakkatsu' else 42
                node.set('d',f'M42 {y}q6 6 12 0');node.set('fill','none');node.set('stroke','#1C1C1A');node.set('stroke-width','1.8')
    # Small authored details stay legible at the larger guide-card size.
    extra='<path d="M33 115h10M53 115h10" fill="none" stroke="#1C1C1A" stroke-width="1.2"/>'
    if name=='gakkatsu':
        extra+='<path d="M35 25q4-2 7 0M54 25q4-2 7 0" fill="none" stroke-width="1.6"/><path d="M52 58l-4 5-4-5" fill="none" stroke="#FCFBF7" stroke-width="1.6"/>'
    if name=='gyoji':
        extra+='<path d="M44 46q4-2 8 0" fill="none" stroke="#D2552A" stroke-width="2.2"/><path d="M30 94h36" fill="none" stroke="#FCFBF7" stroke-width="1.4"/>'
    if name=='jidokai':
        extra+='<circle cx="32" cy="59" r="2" fill="#FCFBF7" stroke="none"/><path d="M26 96h44" fill="none" stroke="#FCFBF7" stroke-width="1.3"/><path d="M84 53l6 3M83 56l5 2" fill="none" stroke-width="1.2"/>'
    if name=='club':
        extra+='<path d="M44 47q4-2 8 0" fill="none" stroke="#D2552A" stroke-width="2.2"/><path d="M25 75l-5 18M71 75l5 18" fill="none" stroke-width="1.2"/>'
    wrapper=ET.fromstring(f'<g xmlns="{NS}">{extra}</g>')
    for node in wrapper:group.append(node)
    (ROOT/f'{name}.svg').write_text(ET.tostring(svg,encoding='unicode'))

# Extract the actual school panorama from the built HP; its SVG is self-contained.
html=(PROJECT/'公開用/index.html').read_text()
start=html.index('<g id="ill-hiroba">')
depth=0;end=None
for match in re.finditer(r'</?g\b[^>]*>',html[start:]):
    depth += -1 if match.group().startswith('</') else 1
    if depth==0:end=start+match.end();break
assert end
world=ET.fromstring(f'<svg xmlns="{NS}" viewBox="0 0 3200 1200">'+html[start:end]+'</svg>')
group=world[0]
# Four larger activity leaders bridge the panorama and the guide cards.
for name,x,y in [('gakkatsu',420,1068),('gyoji',1094,1040),('jidokai',1990,835),('club',2402,958)]:
    holder=element('g',transform=f'translate({x},{y})')
    source=ET.parse(ROOT/f'{name}.svg').getroot()
    holder.append(source.find('{'+NS+'}g'))
    group.append(holder)
(ROOT/'school.svg').write_text(ET.tostring(world,encoding='unicode'))

# Standalone, exportable character sheet using the same source paths.
sheet=element('svg',viewBox='0 0 640 230')
sheet.append(element('rect',width=640,height=230,fill='#FCFBF7'))
for i,(name,title) in enumerate(characters):
    holder=element('g',transform=f'translate({i*160+16},12) scale(1.3)')
    holder.append(ET.parse(ROOT/f'{name}.svg').getroot().find('{'+NS+'}g'))
    sheet.append(holder)
    label=element('text',x=i*160+80,y=204,text_anchor='middle',fill='#1C1C1A',font_size=19,font_family='Hiragino Sans,sans-serif',font_weight=600)
    label.text=title;sheet.append(label)
(ROOT/'characters.svg').write_text(ET.tostring(sheet,encoding='unicode'))
print('Created four original-style SVG mascots, school panorama and character sheet.')
