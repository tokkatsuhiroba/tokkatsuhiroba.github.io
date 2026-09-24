# -*- coding: utf-8 -*-
"""iPhoneで「ホーム画面に追加」したときに出るアイコンを作る（2026-09-24 依頼）。

   使い方： cd src/icon && python3 tsukuru.py
   （macOSでだけ動きます。出来た2枚を そのまま置きます）

   ★作り方は src/ogp/tsukuru.py と同じです。
     macOSの qlmanage でSVGを描いて、Pillowで大きさをそろえます。
     新しい道具は1つも足していません。
   ★qlmanage は 正方形でないSVGの縦横比を守ってくれませんが、
     アイコンは **もともと正方形**なので、そこで困りません。

   ここで作るもの：
     apple-touch-icon-180.png … 180×180。ホーム画面の札になります。
     favicon-32.png           … 32×32。タブの左はしに出る小さい絵です。

   ★角は丸めません。iPhoneが自分で丸めます。
     こちらで丸めると、丸めたあとに もう1回丸められて 角が欠けます。
   ★すき通らせません（背景を必ず塗ります）。
     iPhoneは すき通ったところを **黒**にするので、
     せっかくの白地が 真っ黒な札になってしまいます。
   ★絵を差しかえるときは **ファイル名のほう**を変えてください
     （apple-touch-icon-180.png → apple-touch-icon-181.png のように）。
     OGPと同じ理由です。「?」で版を上げると、取りに来る側が読まないことがあります。
     名前を変えたら src/head-hiroba.html の2行も合わせます。
"""
import io, os, re, subprocess
from PIL import Image, ImageChops

import pathlib
SRC = str(pathlib.Path(__file__).resolve().parents[1] / 'ill' / 'approved' / 'characters')

# サイトの色。帯の緑と、紙の色です（ページと同じものを使います）。
MIDORI = '#2FBA68'
KAMI   = '#FCFBF7'
D      = 1200                       # 下書きの大きさ。最後に小さくします。


def kyara(name):
    """キャラクターのSVGから、中身（<svg>の内がわ）と viewBox を取り出す。
       ＝ src/ogp/tsukuru.py と同じやり方です。"""
    s = io.open(os.path.join(SRC, name + '.svg'), encoding='utf-8').read()
    vb = [float(v) for v in re.search(r'viewBox="([^"]+)"', s).group(1).split()]
    naka = re.sub(r'<title>.*?</title>', '',
                  s.split('>', 1)[1].rsplit('</svg>', 1)[0], flags=re.S)
    return vb, naka


def svg(namae, haba, naka_y, maru_r, clip):
    """緑の地に 紙いろの丸をのせ、その中にキャラクターを立たせる。

       小さくなっても「緑の札に、まるい白、その中に だれか居る」という
       形だけは残ります。字は1文字も置いていません。
       180の札に「TOKKATSU広場」と書いても、読める大きさになりません。

       haba   … キャラクターの横はば（下書き1200のときの数）
       naka_y … キャラクターの上ぶち
       clip   … 丸からはみ出たぶんを切るかどうか（小さいほうの絵で使います）
    """
    (vx, vy, vw, vh), moto = kyara(namae)
    sc = haba / vw
    x  = (D - haba) / 2.0
    kata = ('<g transform="translate(%g %g) scale(%g)">'
            '<g transform="translate(%g %g)">%s</g></g>'
            % (x, naka_y, sc, -vx, -vy, moto))
    if clip:
        kata = '<g clip-path="url(#maru)">%s</g>' % kata
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
            'viewBox="0 0 %d %d">'
            '<defs><clipPath id="maru">'
            '<circle cx="%g" cy="%g" r="%g"/></clipPath></defs>'
            '<rect width="%d" height="%d" fill="%s"/>'
            '<circle cx="%g" cy="%g" r="%g" fill="%s"/>'
            % (D, D, D, D, D / 2.0, D / 2.0, maru_r, D, D, MIDORI,
               D / 2.0, D / 2.0, maru_r, KAMI)
            + kata + '</svg>')


def kaku(f, s, dai):
    """SVGを描いて、dai×dai のPNGにして置く。

       qlmanage は まわりに白いふちを付けることがあるので、
       **白でないところ**を探して、そこだけを切り出します
       （＝緑の地の四角ぴったり）。"""
    io.open(f + '.svg', 'w', encoding='utf-8').write(s)
    if os.path.exists(f + '.svg.png'):
        os.remove(f + '.svg.png')
    subprocess.run(['qlmanage', '-t', '-s', '1600', '-o', '.', f + '.svg'],
                   capture_output=True)
    im = Image.open(f + '.svg.png').convert('RGB')
    shiro = Image.new('RGB', im.size, (255, 255, 255))
    chigau = ImageChops.difference(im, shiro).convert('L').point(
        lambda v: 255 if v > 8 else 0)
    box = chigau.getbbox()
    if not box:
        raise SystemExit('%s が真っ白に描かれました（qlmanage が読めていません）' % f)
    im.crop(box).resize((dai, dai), Image.LANCZOS).save(f + '.png')
    # 下書き（.svg と qlmanage の .png）は置いておきません。
    # 置くと build.py が 公開用/ へ写す枚数に混ざり、何が本物か分からなくなります。
    os.remove(f + '.svg.png')
    os.remove(f + '.svg')
    print('%-24s %s  %.0fKB' % (f + '.png', Image.open(f + '.png').size,
                                os.path.getsize(f + '.png') / 1024))


# ホーム画面の札。学活くんが まるごと 丸の中に立ちます。
kaku('apple-touch-icon-180', svg('gakkatsu', 560.0, 250.0, 440.0, False), 180)

# タブの小さい絵。32では 全身は つぶれて泥のかたまりになるので、
# **顔だけ**を大きく出して、丸からはみ出たぶんを切ります。
kaku('favicon-32', svg('gakkatsu', 1250.0, 169.0, 470.0, True), 32)
