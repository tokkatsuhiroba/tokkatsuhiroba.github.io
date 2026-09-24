#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""グッズの見本（PDFの1ページ目）を作る。

    python3 goods_pdf/make_mihon.py                # 足りないぶんだけ作る
    python3 goods_pdf/make_mihon.py --zenbu        # ぜんぶ作りなおす

  src/downloads/<名前>.pdf  →  src/goods/mihon/<名前>.webp

  なぜ要るか（2026-09-24 依頼）
    グッズは「刷って使う／Wordで直して使う」ものなので、PDFはそのまま
    配ります（板書のように画像へ変えてしまうと、用が足りません）。
    でも札に絵が無いと、押して落とすまで中が見えません。
    だから **1ページ目だけ**を小さな画像にして、札に出します。
    ★この画像は HTML の中に埋めこまれます（原則2＝開いただけでは
      外に1バイトも出ない）。だから小さく作ります。

  ★同じことを .github/workflows/build.yml も走らせています。
    届いたPDFのぶんは、ワークフローが作って main に書き戻します。
    ここを直したら、あちらが呼んでいる引数も見てください。
"""
import io, os, re, sys, glob

ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DL     = os.path.join(ROOT, 'src', 'downloads')
MIHON  = os.path.join(ROOT, 'src', 'goods', 'mihon')
# 横幅。build.py の GOODS_MIHON_W と同じ数にしてください（札に出すだけ）。
W      = 480
# 品質。上げると 120KB（build.py の GOODS_MIHON_KB_MAX）を越えます。
Q      = 72


def tsukuru(pdf, out):
    import pymupdf
    from PIL import Image
    d = pymupdf.open(pdf)
    if not d.page_count:
        raise SystemExit('✕ %s は0ページです' % os.path.basename(pdf))
    p = d[0]
    # 1ページ目の横幅を W にそろえる倍率
    bai = W / float(p.rect.width)
    pix = p.get_pixmap(matrix=pymupdf.Matrix(bai, bai), alpha=False)
    im = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
    im.save(out, 'WEBP', quality=Q, method=6)
    d.close()
    return os.path.getsize(out) / 1024.0


GOODS = os.path.join(ROOT, 'src', 'goods')
# .md の pdf: が指しているファイル名を取り出すための形
PDF_GYO = re.compile(r'^pdf:\s*\S+/downloads/([A-Za-z0-9._-]+)\.pdf\s*$', re.M)


def md_ni_kaku():
    """見本のできた .md に、mihon: の1行を書き足す。

       ★受け口（板書を受けとる.gs）は mihon: を書きません。
         書くと、画像の着くまえに検問へかかるためです。
         だから「見本を作ったあと、ここで書き足す」順にしてあります。
       ★すでに mihon: がある .md は、そのままにします。
    """
    kaita = 0
    for p in sorted(glob.glob(os.path.join(GOODS, '*.md'))):
        if os.path.basename(p).startswith('_'):
            continue
        s = io.open(p, encoding='utf-8').read()
        if re.search(r'^mihon:\s*\S', s, re.M):
            continue
        m = PDF_GYO.search(s)
        if not m:
            continue
        na = m.group(1)
        if not os.path.exists(os.path.join(MIHON, na + '.webp')):
            continue
        # front matter の いちばん下（2つめの --- の手前）に足します
        i = s.index('\n---\n', 3)
        s = s[:i] + '\nmihon: ' + na + s[i:]
        io.open(p, 'w', encoding='utf-8').write(s)
        kaita += 1
        print('  mihon: を足しました … %s' % os.path.basename(p))
    return kaita


def main():
    zenbu = '--zenbu' in sys.argv
    os.makedirs(MIHON, exist_ok=True)
    pdfs = sorted(glob.glob(os.path.join(DL, '*.pdf')))
    if not pdfs:
        print('src/downloads/ にPDFはありません')
        return
    tsukutta = 0
    for pdf in pdfs:
        na = os.path.splitext(os.path.basename(pdf))[0]
        out = os.path.join(MIHON, na + '.webp')
        if os.path.exists(out) and not zenbu:
            print('  そのまま … %s.webp' % na)
            continue
        kb = tsukuru(pdf, out)
        tsukutta += 1
        print('  できました … %s.webp （%.0fKB）' % (na, kb))
    kaita = md_ni_kaku()
    print('\n  %d枚 作り、%d件の .md に mihon: を足しました'
          ' → src/goods/mihon/\n' % (tsukutta, kaita))


if __name__ == '__main__':
    main()
