# -*- coding: utf-8 -*-
"""学級会グッズのUD部品（A4・mm指定）。
   描くたびにUD基準を検査し、finish() で1件でも違反があれば止まる。

   もとは B4横 用の道具。ここでは A4 にし、紙ごとに向きを変えられるようにした。
"""
import os
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.lib.units import mm
from reportlab.lib.colors import Color, black, white

_TTF = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "UDGothic-subset.ttf")
if os.path.exists(_TTF):
    from reportlab.pdfbase.ttfonts import TTFont as _TTFont
    pdfmetrics.registerFont(_TTFont('UDJP', _TTF)); JP = 'UDJP'
else:
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5')); JP = 'HeiseiKakuGo-W5'
    print("  ※ UDGothic-subset.ttf がありません。make_font.py を走らせてください")

# ================= UD基準 =================
MIN_SIZE = {'display': 16.0, 'title': 12.0, 'body': 10.5, 'data': 10.5,
            'label': 9.0, 'note': 9.0, 'dense': 9.0, 'plan': 7.5}
MAX_LABEL_CHARS = 12
LEAD_RATIO   = 1.5
WRITE_H      = 8.0
CIRCLE_H     = 7.0
RULE_W       = 0.6
CONTRAST_BODY, CONTRAST_LARGE = 7.0, 4.5
LINE_CHARS   = 42
BOLD_MIN     = 14.0
BOLD_STROKE  = 0.011
# =========================================

PW, PH = 210.0, 297.0          # A4たて。setpage() で変えられる
MG = 14.0

NAVY  = Color(0.05, 0.10, 0.18)
RED   = Color(0.64, 0.00, 0.08)
GRAY  = Color(0.28, 0.31, 0.36)
HAIR  = Color(0.62, 0.65, 0.70)
LGRAY = Color(0.945, 0.950, 0.960)
BLUE  = Color(0.925, 0.950, 0.980)
GREEN = Color(0.05, 0.34, 0.19)
PALER = Color(1.00, 0.945, 0.945)
KI    = Color(1.00, 0.972, 0.878)

_V, _MAXY, _BAND = [], [0.0], []

# ★フォントに無い字は、紙の上で □（豆腐）になります。
#   目で見ないと気づけないので、描くたびに機械で見ます。
_CMAP = None
def _mojiaru(s):
    global _CMAP
    if _CMAP is None:
        try:
            from fontTools.ttLib import TTFont as _FT
            _CMAP = set(_FT(_TTF, lazy=True).getBestCmap()) if os.path.exists(_TTF) else set()
        except Exception:
            _CMAP = set()
    if not _CMAP:
        return []
    return sorted({ch for ch in s if ord(ch) not in _CMAP})


def setpage(w, h, mg=None):
    global PW, PH, MG
    PW, PH = float(w), float(h)
    if mg is not None:
        MG = float(mg)


def _lum(c):
    def f(v): return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c.red) + 0.7152 * f(c.green) + 0.0722 * f(c.blue)


def contrast(fg, bg=white):
    a, b = _lum(fg), _lum(bg)
    if a < b: a, b = b, a
    return (a + 0.05) / (b + 0.05)


def viol(kind, detail): _V.append((kind, detail))


def zenkaku(s):
    """「全角で何字ぶんか」を数える。半角は0.5字。
       ★ここを1字ずつ数えると、URLのような半角だけの行が、
         見た目は短いのに「長すぎる」と止まります（実測）。"""
    import unicodedata
    return sum(1.0 if unicodedata.east_asian_width(ch) in 'WFA' else 0.5
               for ch in s)
def clear(): _V.clear(); _MAXY[0] = 0.0; _BAND.clear()

def newdoc(path):
    c = canvas.Canvas(path, pagesize=(PW * mm, PH * mm))
    c.setTitle(os.path.basename(path).replace('.pdf', ''))
    return c

def newpage(c):
    c.showPage()
    c.setPageSize((PW * mm, PH * mm))
    _MAXY[0] = 0.0; _BAND.clear()

def X(v): return v * mm
def Y(v): return (PH - v) * mm
def sw(s, size): return pdfmetrics.stringWidth(s, JP, size) / mm


def txt(c, x, y, s, size=10.5, color=black, bold=False, align='l',
        maxw=None, role='body', bg=white):
    if size < MIN_SIZE[role] - 0.01:
        viol('文字が小さい', "'%s' %spt < %spt (%s)" % (s[:20], size, MIN_SIZE[role], role))
    if role == 'label' and len(s) > MAX_LABEL_CHARS:
        viol('labelが長い', "'%s' %d字 > %d字" % (s[:24], len(s), MAX_LABEL_CHARS))
    need = CONTRAST_LARGE if size >= 18 else CONTRAST_BODY
    cr = contrast(color, bg)
    if cr < need - 0.01:
        viol('コントラスト不足', "'%s' 対比%.1f < %s" % (s[:16], cr, need))
    nai = _mojiaru(s)
    if nai:
        viol('フォントに無い字', "'%s' に %s（紙では □ になります。"
             "make_font.py の集め方を直してください）"
             % (s[:20], '・'.join('U+%04X %s' % (ord(x), x) for x in nai)))
    zen = zenkaku(s)
    if zen > LINE_CHARS:
        viol('1行が長い', "'%s…' 全角%.0f字 > %d字" % (s[:24], zen, LINE_CHARS))
    w = sw(s, size)
    if maxw is not None and w > maxw + 0.05:
        viol('横はみ出し', "'%s' 幅%.1fmm > 枠%.1fmm" % (s[:20], w, maxw))
    b = y + size * 0.36
    if b > _MAXY[0]: _MAXY[0] = b
    if b > PH - 2.0:
        viol('縦はみ出し', "'%s' 下端%.0fmm > %.0fmm" % (s[:16], b, PH - 2.0))
    if align == 'c' and maxw: x += (maxw - w) / 2
    if align == 'r' and maxw: x += (maxw - w)
    if bold and size < BOLD_MIN and color == black:
        color = NAVY; bold = False
    c.setFillColor(color)
    if bold:
        c.setStrokeColor(color); c.setLineWidth(size * BOLD_STROKE)
        t = c.beginText(X(x), Y(y + size * 0.352)); t.setFont(JP, size)
        t.setTextRenderMode(2); t.textLine(s); c.drawText(t)
    else:
        c.setFont(JP, size); c.drawString(X(x), Y(y + size * 0.352), s)
    c.setFillColor(black); c.setStrokeColor(black)
    return w


def wrapjp(s, size, maxw):
    NG = "。、）」』】〉》’”ぁぃぅぇぉっゃゅょーァィゥェォッャュョ！？"
    out, cur = [], ""
    for ch in s:
        if ch == "\n":
            out.append(cur); cur = ""; continue
        if (sw(cur + ch, size) > maxw or zenkaku(cur) >= LINE_CHARS) and cur:
            if ch in NG and len(cur) >= 2:
                out.append(cur[:-1]); cur = cur[-1] + ch
            else:
                out.append(cur); cur = ch
        else:
            cur += ch
    if cur: out.append(cur)
    return out


def para(c, x, y, s, size=10.5, maxw=100, lead=None, color=black,
         bold=False, role='body', bg=white):
    minlead = size * 0.3528 * LEAD_RATIO
    lead = lead if lead else minlead
    if lead < minlead - 0.01:
        viol('行間が狭い', "'%s' 行間%.1fmm < %.1fmm" % (s[:16], lead, minlead))
    for ln in wrapjp(s, size, maxw):
        txt(c, x, y, ln, size, color, bold, maxw=maxw, role=role, bg=bg)
        y += lead
    return y


def rect(c, x, y, w, h, fill=None, stroke=NAVY, lw=0.6, r=None, dash=None):
    if fill: c.setFillColor(fill)
    if stroke: c.setStrokeColor(stroke)
    c.setLineWidth(lw if stroke else 0)
    if dash: c.setDash(dash)
    st, fl = (1 if stroke else 0), (1 if fill else 0)
    if r: c.roundRect(X(x), Y(y + h), w * mm, h * mm, r * mm, stroke=st, fill=fl)
    else: c.rect(X(x), Y(y + h), w * mm, h * mm, stroke=st, fill=fl)
    c.setDash(); c.setFillColor(black); c.setStrokeColor(black)


def line(c, x1, y1, x2, y2, lw=0.5, color=black, dash=None):
    c.setStrokeColor(color); c.setLineWidth(lw)
    if dash: c.setDash(dash)
    c.line(X(x1), Y(y1), X(x2), Y(y2)); c.setDash(); c.setStrokeColor(black)


def writelines(c, x, y, w, n=1, gap=WRITE_H, lw=RULE_W):
    if gap < WRITE_H - 0.01:
        viol('記入欄が狭い', "行間%smm < %smm" % (gap, WRITE_H))
    if lw < RULE_W - 0.01: viol('罫線が細い', "%spt < %spt" % (lw, RULE_W))
    for i in range(n):
        y += gap
        line(c, x, y, x + w, y, lw, GRAY)
    return y + 1.5


def circlebox(c, x, y, s, size=10.5, h=CIRCLE_H, on=False, bg=white):
    if h < CIRCLE_H - 0.01: viol('選択肢が低い', "'%s' 高さ%smm < %smm" % (s, h, CIRCLE_H))
    w = sw(s, size) + 6.0
    rect(c, x, y, w, h, PALER if on else None, RED if on else GRAY,
         1.6 if on else 0.7, h / 2)
    txt(c, x, y + (h - size * 0.3528) / 2, s, size, RED if on else black, on,
        maxw=w, align='c', bg=PALER if on else bg)
    return w


def sec(c, x, y, s, w=70, size=11.5):
    for (t, b) in _BAND:
        if y < b - 0.5 and y + 6.6 > t + 0.5:
            viol('全幅の要素と重なる', "'%s' y=%.0f が 全幅要素(%.0f〜%.0fmm) の中" % (s[:16], y, t, b))
            break
    rect(c, x, y, w, 6.6, NAVY, None, 0, 1.0)
    txt(c, x + 2.6, y + 1.4, s, size, white, maxw=w - 5, role='body', bg=NAVY)
    return y + 9.0


def ashi(c, s):
    """紙の足もと。どこから出した紙かと、印刷の指示を刷りこむ。"""
    txt(c, MG, PH - MG + 1.0, s, 9, GRAY, maxw=PW - 2 * MG, role='note')


def finish(c, path):
    c.save()
    if _V:
        from collections import Counter
        print("!! UD違反 %d件  " % len(_V) +
              " / ".join("%s%s" % (k, v) for k, v in Counter(k for k, _ in _V).items()))
        for k, d in _V[:14]:
            print("   [%s] %s" % (k, d))
        raise SystemExit(1)
    print("  UD-OK %-30s %3dKB  下端%3.0f/%.0fmm"
          % (os.path.basename(path), os.path.getsize(path) // 1024, _MAXY[0], PH))
