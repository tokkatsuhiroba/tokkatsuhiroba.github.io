#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""送られたグッズのファイルから、「作成者」の名前を消す。

    python3 goods_pdf/nanashi.py            # src/downloads/ をぜんぶ見る
    python3 goods_pdf/nanashi.py --miru     # 消さずに、何が入っているかだけ見る

  なぜ要るか（2026-09-24 依頼）
    写真は「このページの上で黒く塗って隠せる」ので済みました。
    **ファイルの中は塗れません。**
    そのうえ Word は、画面のどこにも出ていないのに
      docProps/core.xml の dc:creator（作った人）
      docProps/core.xml の cp:lastModifiedBy（最後に直した人）
      docProps/app.xml  の Company（つとめ先）
    に名前と学校名を抱えています。PDF も /Author に抱えます。
    送る人は、まず気づきません。だから機械で落とします。

  ★これで消えるのは **名前の欄だけ**です。
    本文・ヘッダー・フッター・透かしに書かれた学校名は消せません。
    そこは、送る人と管理人が目で見るしかありません
    （画面の「見ました」と、知らせメールの★に書いてあります）。

  ★同じものを2度走らせても、2度めは何もしません（空なら触りません）。
    触ると中身が変わり、ワークフローが毎回 書き戻すことになります。
"""
import io, os, re, sys, glob, shutil, zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DL   = os.path.join(ROOT, 'src', 'downloads')

# Office（.docx .pptx .xlsx）の中で、名前を抱えている欄
OFFICE_RAN = (
    ('docProps/core.xml', ('dc:creator', 'cp:lastModifiedBy')),
    ('docProps/app.xml',  ('Company', 'Manager')),
)
OFFICE = ('.docx', '.pptx', '.xlsx')


def office_miru(p):
    """空でない名前の欄を [(ファイル, 欄, 中身)] で返す。"""
    aru = []
    with zipfile.ZipFile(p) as z:
        na = set(z.namelist())
        for f, rans in OFFICE_RAN:
            if f not in na:
                continue
            s = z.read(f).decode('utf-8', 'replace')
            for r in rans:
                for m in re.finditer(r'<%s>([^<]*)</%s>' % (r, r), s):
                    if m.group(1).strip():
                        aru.append((f, r, m.group(1)))
    return aru


def office_kesu(p):
    """名前の欄を空にして、書き直す。何も無ければ False。"""
    if not office_miru(p):
        return False
    tmp = p + '.nanashi'
    with zipfile.ZipFile(p) as moto, \
         zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as ato:
        for i in moto.infolist():
            b = moto.read(i.filename)
            rans = dict(OFFICE_RAN).get(i.filename)
            if rans:
                s = b.decode('utf-8', 'replace')
                for r in rans:
                    s = re.sub(r'<%s>[^<]*</%s>' % (r, r), '<%s></%s>' % (r, r), s)
                b = s.encode('utf-8')
            # 時こくは元のまま写します（中身が同じなら、同じバイトになるように）
            ato.writestr(i, b)
    shutil.move(tmp, p)
    return True


def pdf_kesu(p, miru=False):
    import pymupdf
    d = pymupdf.open(p)
    m = d.metadata or {}
    aru = [(k, m.get(k)) for k in ('author', 'creator', 'producer', 'keywords', 'subject')
           if (m.get(k) or '').strip()]
    if miru:
        d.close()
        return aru
    # 作った人まわりだけ空にします（題名は残します。札には出しませんが、
    #   落とした先生の手もとで「何のファイルか」が分かるためです）
    if not [k for k, _ in aru if k in ('author', 'creator', 'keywords', 'subject')]:
        d.close()
        return False
    m2 = dict(m)
    for k in ('author', 'creator', 'keywords', 'subject'):
        m2[k] = ''
    d.set_metadata(m2)
    # pymupdf は「元のファイルに上書き」を断ります（incremental でないとき）。
    #   いったん別名で出して、あとから置きかえます。
    tmp = p + '.nanashi'
    d.save(tmp, deflate=True, garbage=0)
    d.close()
    shutil.move(tmp, p)
    return True


def main():
    miru = '--miru' in sys.argv
    if not os.path.isdir(DL):
        print('src/downloads/ がありません')
        return
    kaeta, dame = 0, 0
    for p in sorted(glob.glob(os.path.join(DL, '*'))):
        e = os.path.splitext(p)[1].lower()
        na = os.path.basename(p)
        # ★1つ読めなくても、**絶対に止めません**（2026-09-24 実測）。
        #   壊れた .docx が1つ届いただけで、ここが例外を投げ、ビルドが
        #   落ち、**サイトがまるごと更新されなくなりました**。
        #   読めないものは そのままにして、先へ進みます。
        #   （読めないファイルは、知らせメールの［すぐ消す］で下ろせます。
        #     受け口も、いまは読めないものを はじめから断っています。）
        try:
            if e in OFFICE:
                aru = office_miru(p)
                if miru:
                    print('  %s … %s' % (na, aru or '（名前の欄は空です）'))
                elif aru:
                    office_kesu(p)
                    kaeta += 1
                    print('  消しました … %s （%s）'
                          % (na, '、'.join('%s=%s' % (r, v) for _, r, v in aru)))
            elif e == '.pdf':
                if miru:
                    print('  %s … %s' % (na, pdf_kesu(p, True) or '（名前の欄は空です）'))
                elif pdf_kesu(p):
                    kaeta += 1
                    print('  消しました … %s' % na)
        except Exception as err:
            dame += 1
            print('  ⚠ 読めませんでした（そのままにします） … %s … %s'
                  % (na, str(err)[:120]))
    if not miru:
        print('\n  %d個から、作成者の名前を消しました%s\n'
              % (kaeta, ('（%d個は読めませんでした）' % dame) if dame else ''))


if __name__ == '__main__':
    main()
