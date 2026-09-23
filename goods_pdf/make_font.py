# -*- coding: utf-8 -*-
"""学級会グッズの紙に埋めこむフォントを作る（1回走らせれば .ttf ができる）。

★このMacに入っている日本語フォントは、ほとんどが CFF（OpenType）で、
  reportlab はそのままでは読めません。TrueType に直すには cu2qu が要ります。
  ところが /Library/Fonts/Arial Unicode.ttf は **はじめから TrueType** で、
  日本語をぜんぶ持っています。だから変換なしで、絞るだけで使えます。
  fsType=8（編集可）なので、PDFへの埋めこみも font 自身が許しています。

★絞るのは「この紙に出てくる字」だけです。22MB → 数百KB になります。
  足りない字があると豆腐（□）になるので、集め方は広めにしてあります。
"""
import os, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = "/Library/Fonts/Arial Unicode.ttf"
OUT  = os.path.join(HERE, "UDGothic-subset.ttf")


def used_chars():
    chars = set()
    for dirpath, _, names in os.walk(HERE):
        for nm in names:
            if not nm.endswith((".py", ".md", ".txt")):
                continue
            try:
                chars |= set(open(os.path.join(dirpath, nm), encoding="utf-8").read())
            except Exception:
                pass
    # かな・英数・記号・丸数字は、書きかえても足りなくならないよう丸ごと入れる
    for a, b in ((0x3040, 0x30FF), (0x0020, 0x007E), (0xFF01, 0xFF5E),
                 (0x2460, 0x2473), (0x3000, 0x303F), (0x2190, 0x21FF),
                 (0x25A0, 0x25FF)):
        chars |= {chr(x) for x in range(a, b + 1)}
    chars |= set("★☆◎○●◆◇■□▲▼※→←↑↓〇✓✔")
    # ★全角スペース（U+3000）を落とさないこと。
    #   Python の isprintable() は、ASCIIの空白いがいの空白を False にします。
    #   ここで落ちると「第　　回」が「第□□回」になります（実測）。
    return {c for c in chars
            if c == "\u3000" or (c.isprintable() and unicodedata.category(c) != "Cc")}


def main():
    from fontTools.ttLib import TTFont
    from fontTools import subset
    chars = used_chars()
    print("使う文字 %d字" % len(chars))
    f = TTFont(SRC)
    assert "glyf" in f, "TrueType ではありません（cu2qu が要ります）"
    opts = subset.Options(notdef_outline=True, layout_features=[], name_IDs=['*'],
                          recalc_bounds=True, drop_tables=['VORG'])
    sub = subset.Subsetter(options=opts)
    sub.populate(unicodes=[ord(c) for c in chars])
    sub.subset(f)
    print("絞ったあと %d グリフ" % len(f.getGlyphOrder()))
    f.save(OUT)
    print("保存 %s  %dKB" % (os.path.basename(OUT), os.path.getsize(OUT) // 1024))
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont as RLTTFont
    pdfmetrics.registerFont(RLTTFont("UDJP", OUT))
    print("reportlab 登録OK")


if __name__ == "__main__":
    main()
