# -*- coding: utf-8 -*-
"""OGP（LINEに貼ったときに出る絵）を1200×630で作る。

   使い方： cd src/ogp && python3 tsukuru.py
   （macOSでだけ動きます。出来た ogp.png / ogp-okuru.png を そのまま置きます）

   ★macOSの qlmanage でSVGを描きます（外の道具は使いません）。
   ★qlmanage は 正方形でないSVGの縦横比を守ってくれません。
     そこで **1200×1200の中に、1200×630の帯を入れて**描き、
     あとから帯だけを切り出します（比が1.905になることを実測ずみ）。
"""
import io, os, re, subprocess
from PIL import Image

import pathlib
SRC  = str(pathlib.Path(__file__).resolve().parents[1] / 'ill' / 'approved' / 'characters')
MARU = 'Hiragino Maru Gothic ProN'
W, H = 1200, 630
UE   = (1200 - H) // 2          # 帯の上ぶち（＝285）

def kyara(name):
    s = io.open(os.path.join(SRC, name + '.svg'), encoding='utf-8').read()
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', s).group(1).split()]
    naka = re.sub(r'<title>.*?</title>', '',
                  s.split('>', 1)[1].rsplit('</svg>', 1)[0], flags=re.S)
    return vb, naka

def svg(namae, dai, sho, shita, haikei, obi, dai_size=72, haba=760.0):
    (vx, vy, vw, vh), naka = kyara(namae)
    sc = haba / vw
    x = (W - haba) / 2.0
    y = UE + H - vh * sc - 30
    T = ('<text x="600" y="%g" text-anchor="middle" font-family="%s" '
         'font-weight="%s" font-size="%g" fill="%s" letter-spacing="%g">%s</text>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="1200" '
            'viewBox="0 0 1200 1200">'
            '<rect width="1200" height="1200" fill="#FFFFFF"/>'
            '<rect x="0" y="%d" width="%d" height="%d" fill="%s"/>'
            '<rect x="0" y="%d" width="%d" height="13" fill="%s"/>'
            % (UE, W, H, haikei, UE, W, obi)
            + T % (UE + 128, MARU, 700, dai_size, '#1C1C1A', 3, dai)
            + T % (UE + 196, MARU, 600, 33, '#63625C', 2, sho)
            + T % (UE + 250, MARU, 600, 24, '#8A8983', 1, shita)
            + '<g transform="translate(%g %g) scale(%g)">'
              '<g transform="translate(%g %g)">%s</g></g></svg>'
              % (x, y, sc, -vx, -vy, naka))

def kaku(f, s):
    io.open(f + '.svg', 'w', encoding='utf-8').write(s)
    if os.path.exists(f + '.svg.png'):
        os.remove(f + '.svg.png')
    subprocess.run(['qlmanage', '-t', '-s', '1600', '-o', '.', f + '.svg'],
                   capture_output=True)
    im = Image.open(f + '.svg.png').convert('RGB')
    w, h = im.size
    px = im.load()
    shiro = lambda p: p[0] > 250 and p[1] > 250 and p[2] > 250
    ys = [y for y in range(h) if not shiro(px[w // 2, y])]
    im.crop((0, ys[0], w, ys[-1] + 1)).resize((W, H), Image.LANCZOS).save(f + '.png')
    print('%-14s %s  %.0fKB' % (f + '.png', Image.open(f + '.png').size,
                                os.path.getsize(f + '.png') / 1024))

kaku('ogp-hiroba2', svg('group-shoulders',
                'みんなの特活ひろば<tspan font-size="44">（仮）</tspan>', '特別活動の情報が、溜まる場。',
                'ニュース・実践・板書・研究日程・お悩みBOX',
                '#FCFBF7', '#2FBA68'))
kaku('ogp-okuru2', svg('group-welcome',
                      '実践を、共有してください。', '写真1枚でも大丈夫。ログインも要りません。',
                      'みんなの特活ひろば（仮）',
                      '#FBF2D8', '#D2552A', dai_size=66, haba=1000.0))
# お悩みBOX（2026-09-24 依頼）。お悩み1件をLINEに流したとき、
#   札に出ていたのは「4人が肩を組んだ絵」と サイト全体の説明でした。
#   受けとった人には、何を頼まれているのか分かりません。
#   ★1人（学活くん）にしたのは、**困っているのは1人**だからです。
#     肩を組んだ4人は「みんなで集まる場」の絵で、お願いの顔になりません。
#   ★haba を 460 にしたのは、1人ぶんの絵だからです。
#     4人ぶんの 760／1000 のままだと、人が引きのばされて大きすぎます。
kaku('ogp-komari2', svg('gakkatsu-think',
                       'お悩みBOX', '答えを、待っています。',
                       'みんなの特活ひろば（仮）｜特別活動',
                       '#E1EAF3', '#3A6EA5', dai_size=80, haba=460.0))
