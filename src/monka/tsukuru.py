# -*- coding: utf-8 -*-
"""文科省資料（shiru.html#monka）の札の上に置くサムネイルを作る（2026-09-26 依頼）。

  「文科資料はサムネイルをつけて。視覚的にわかりやすくして」

  使い方：
    python3 src/monka/tsukuru.py <材料の置き場>
  材料の置き場には、公式から取ってきた次のファイルを入れておきます。
    PDF（1ページめを表紙として使う）…… build.py の LINKS の MONKA_… と同じもの
      tokkatsu_20240722-01.pdf / tokkatsu_j-h_leafb_1.pdf（緑本 小／中高）
      r020326_pri_tokubetsuk.pdf / r020326_mid_tokubetsuk.pdf / r030820_hig_tokubetsuk.pdf（評価）
      20221213-mxt_kyoiku02-100002607_014.pdf / 20260730-mxt_kyoiku01-100002608_13.pdf /
      1407196_22_1_1_2.pdf（解説 小／中／高）
    映像資料のページの見出しの絵（ページの中の images/top-image.jpg）
      sho_tokkatsueizo_top-image.jpg / sho_tokkatsueizo2_top-image.jpg
    道徳教育アーカイブのトップの画面写真（1280×800）
      dotoku_ss.png
        ★真ん中の大きな写真は子どもの顔が大きいので使いません。
          ロゴと、下の4つの入口（アイコン）だけを切り出します。

  出来上がり：src/monka/<名前>.webp（480×300・1枚40KB以内）
    build.py がページに埋めこみます（外からは1バイトも読みません。原則2）。
  要るもの：PyMuPDF（fitz）と Pillow。
"""
import io
import os
import sys

import fitz
from PIL import Image, ImageDraw

W, H = 480, 300
INK = (28, 28, 26)
KOKO = os.path.dirname(os.path.abspath(__file__))


def hyoshi(pdf, migi_hanbun=False):
    """PDFの1ページめを絵にする。見開き（横長）なら右半分＝表紙だけ。"""
    d = fitz.open(pdf)
    pix = d[0].get_pixmap(matrix=fitz.Matrix(2, 2))
    im = Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB')
    if migi_hanbun or im.width > im.height:
        im = im.crop((im.width // 2, 0, im.width, im.height))
    return im


def kasaneru(kami, iro):
    """表紙を少しずつずらして重ねる。いちばん前（左下）が kami[0]。"""
    c = Image.new('RGB', (W, H), iro)
    n = len(kami)
    h = 246
    ws = [round(k.width * h / k.height) for k in kami]
    dx, dy = 58, 12
    zen_w = ws[0] + dx * (n - 1)
    x0 = (W - zen_w) // 2
    y0 = (H - h) // 2 + dy * (n - 1) // 2
    dr = ImageDraw.Draw(c)
    for i in reversed(range(n)):
        k = kami[i].resize((ws[i], h), Image.LANCZOS)
        x, y = x0 + dx * i, y0 - dy * i
        dr.rectangle((x + 4, y + 4, x + ws[i] + 4, y + h + 4), fill=INK)   # 札と同じ影
        c.paste(k, (x, y))
        dr.rectangle((x - 1, y - 1, x + ws[i], y + h), outline=INK, width=2)
    return c


def haba_ni(im, iro, haba, saisei=False):
    """横長の絵を、真ん中に置く。saisei=True なら「動画」の印を右下に。"""
    c = Image.new('RGB', (W, H), iro)
    k = im.convert('RGB')
    h = round(k.height * haba / k.width)
    k = k.resize((haba, h), Image.LANCZOS)
    c.paste(k, ((W - haba) // 2, (H - h) // 2 - (14 if saisei else 0)))
    if saisei:
        dr = ImageDraw.Draw(c)
        cx, cy, r = W - 50, H - 46, 26
        dr.ellipse((cx - r + 3, cy - r + 3, cx + r + 3, cy + r + 3), fill=INK)
        dr.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(232, 197, 71), outline=INK, width=3)
        dr.polygon([(cx - 8, cy - 13), (cx - 8, cy + 13), (cx + 14, cy)], fill=INK)
    return c


def dotoku(ss, iro):
    im = Image.open(ss).convert('RGB')
    logo = im.crop((12, 14, 330, 74))            # 左上のロゴ
    iriguchi = im.crop((112, 552, 1148, 732))    # 下の4つの入口
    c = Image.new('RGB', (W, H), iro)
    lw = 300
    logo = logo.resize((lw, round(logo.height * lw / logo.width)), Image.LANCZOS)
    c.paste(logo, ((W - lw) // 2, 40))
    iw = 440
    iriguchi = iriguchi.resize((iw, round(iriguchi.height * iw / iriguchi.width)), Image.LANCZOS)
    c.paste(iriguchi, ((W - iw) // 2, 130))
    return c


def dasu(im, na):
    saki = os.path.join(KOKO, na + '.webp')
    for q in (82, 76, 70, 62, 55):
        b = io.BytesIO()
        im.save(b, 'WEBP', quality=q, method=6)
        if b.tell() <= 40 * 1024:
            break
    open(saki, 'wb').write(b.getvalue())
    print('  %s.webp  %dx%d  %.1fKB (q=%d)' % (na, im.width, im.height, b.tell() / 1024, q))


def main():
    m = sys.argv[1] if len(sys.argv) > 1 else '.'
    p = lambda f: os.path.join(m, f)
    dasu(kasaneru([hyoshi(p('tokkatsu_20240722-01.pdf'), True),
                   hyoshi(p('tokkatsu_j-h_leafb_1.pdf'))], (237, 245, 236)), 'midori')
    dasu(kasaneru([hyoshi(p('r020326_pri_tokubetsuk.pdf')),
                   hyoshi(p('r020326_mid_tokubetsuk.pdf')),
                   hyoshi(p('r030820_hig_tokubetsuk.pdf'))], (251, 242, 216)), 'hyoka')
    dasu(haba_ni(Image.open(p('sho_tokkatsueizo_top-image.jpg')), (255, 255, 255), 430, True),
         'eizo-gakkatsu')
    dasu(haba_ni(Image.open(p('sho_tokkatsueizo2_top-image.jpg')), (255, 255, 255), 430, True),
         'eizo-club')
    dasu(dotoku(p('dotoku_ss.png'), (255, 255, 255)), 'dotoku')
    dasu(kasaneru([hyoshi(p('20221213-mxt_kyoiku02-100002607_014.pdf')),
                   hyoshi(p('20260730-mxt_kyoiku01-100002608_13.pdf')),
                   hyoshi(p('1407196_22_1_1_2.pdf'))], (239, 234, 247)), 'kaisetsu')


if __name__ == '__main__':
    main()
