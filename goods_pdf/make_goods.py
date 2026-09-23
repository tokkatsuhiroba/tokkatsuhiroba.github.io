# -*- coding: utf-8 -*-
"""学級会グッズ6点をA4のPDFにする。

★言葉は、サイトの「学級活動(1)の学習過程」にそろえています。
    出し合う → くらべ合う → まとめる
    提案理由を ものさしにする
    賛成・反対の人数ではなく、「なぜ」を残す
  紙とサイトで言い方が違うと、子どもが迷います。

★誰が読む紙かで、文字の下限が変わります（lib_ud の role）。
    子どもが読んで書く紙 … 10.5pt 以上
    黒板に貼る紙        … 16pt 以上（実際は 24〜48pt）

★記入欄は 8mm。6mmだと大人の字しか入りません。
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ud import *

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   'src', 'downloads')
SITE = 'TOKKATSU広場  特別活動の情報が、溜まる場'


def _waku(c, x, y, w, h, midashi, iro=NAVY, bg=None):
    """1枚ぶんの枠と、左上の見出し札。"""
    rect(c, x, y, w, h, bg, iro, 1.4, 2.0)
    fw = sw(midashi, 11) + 8
    rect(c, x + 4, y - 3.3, fw, 6.6, iro, None, 0, 1.0)
    txt(c, x + 8, y - 1.9, midashi, 11, white, maxw=fw - 8, role='body', bg=iro)
    return y + 7.0


def _kiri(c, y):
    """切り取り線。"""
    line(c, 6, y, PW - 6, y, 0.6, HAIR, (2, 2))
    txt(c, PW - 24, y - 2.6, "✂ きりとり", 9, GRAY, role='note')


# ── 1. 議題ポスト用紙（A4に2枚・子どもが書いて入れる）──────────
def gidai_post():
    setpage(210, 297, 14)
    path = os.path.join(OUT, 'gidai-post.pdf')
    clear(); c = newdoc(path)
    for k in range(2):
        top = 12 + k * 140
        y = _waku(c, MG, top, PW - 2 * MG, 126, "議題ポスト用紙", NAVY, KI)
        x = MG + 6; w = PW - 2 * MG - 12
        y = para(c, x, y + 2, "クラスのみんなで 決めたいことを 書いて、"
                              "議題ポストに 入れてください。", 11, w)
        y += 3
        txt(c, x, y, "なまえ", 10.5, NAVY, bg=KI)
        line(c, x + 22, y + 6.4, x + 92, y + 6.4, 0.8, GRAY)
        txt(c, x + 100, y, "月　日", 10.5, NAVY, bg=KI)
        line(c, x + 122, y + 6.4, x + w, y + 6.4, 0.8, GRAY)
        y += 12
        txt(c, x, y, "みんなで 決めたいこと", 11, NAVY, bg=KI)
        y = writelines(c, x, y + 4, w, 2)
        y += 2
        txt(c, x, y, "どうして みんなで 話したいのですか（わけ）", 11, NAVY, bg=KI)
        y = writelines(c, x, y + 4, w, 3)
        y += 1
        para(c, x, y, "★「じぶんで できること」「先生が 決めること」は、"
                      "学級会の 議題には なりません。", 10.5, w, color=GRAY, bg=KI)
        if k == 0:
            _kiri(c, top + 133)
    ashi(c, SITE + "　／　A4・等倍（100%）で印刷")
    finish(c, path)


# ── 2. 提案カード（A4に1枚・子ども）────────────────────
def teian_card():
    setpage(210, 297, 14)
    path = os.path.join(OUT, 'teian-card.pdf')
    clear(); c = newdoc(path)
    y = _waku(c, MG, 12, PW - 2 * MG, 268, "提案カード", NAVY, None)
    x = MG + 6; w = PW - 2 * MG - 12
    y = para(c, x, y + 2, "議題ポストに 入れたことが 議題に えらばれたら、"
                          "このカードに くわしく 書きます。", 11, w)
    y += 4
    txt(c, x, y, "なまえ", 10.5, NAVY)
    line(c, x + 22, y + 6.4, x + 92, y + 6.4, 0.8, GRAY)
    txt(c, x + 100, y, "月　日", 10.5, NAVY)
    line(c, x + 122, y + 6.4, x + w, y + 6.4, 0.8, GRAY)
    y += 14
    y = sec(c, x, y, "① 議題（何を 決めますか）", w)
    y = writelines(c, x, y, w, 2)
    y += 5
    y = sec(c, x, y, "② 提案理由（どうして みんなで 話すのですか）", w)
    y = para(c, x, y, "★ここが いちばん 大事です。話合いで 案を くらべるときの"
                      "「ものさし」に なります。", 10.5, w, color=GRAY)
    y = writelines(c, x, y + 1, w, 4)
    y += 5
    y = sec(c, x, y, "③ 決まったら、クラスは どうなると うれしいですか", w)
    y = writelines(c, x, y, w, 3)
    y += 5
    y = sec(c, x, y, "④ いつまでに やりたいですか", w)
    txt(c, x, y + 1, "　月　　日ごろまで", 11)
    line(c, x, y + 8.4, x + 80, y + 8.4, 0.8, GRAY)
    y += 14
    y = sec(c, x, y, "⑤ 計画委員会が 書くところ", w)
    y = para(c, x, y, "この議題を 学級会で 話し合いますか。", 10.5, w)
    xx = x
    xx += circlebox(c, xx, y + 1, "話し合う", 10.5, 7.5) + 5
    xx += circlebox(c, xx, y + 1, "もう少し 考える", 10.5, 7.5) + 5
    circlebox(c, xx, y + 1, "べつの方法で", 10.5, 7.5)
    ashi(c, SITE + "　／　A4・等倍（100%）で印刷")
    finish(c, path)


# ── 3. 学級会ノート（A4に1枚・子ども）───────────────────
def gakkyukai_note():
    setpage(210, 297, 14)
    path = os.path.join(OUT, 'gakkyukai-note.pdf')
    clear(); c = newdoc(path)
    y = _waku(c, MG, 12, PW - 2 * MG, 268, "学級会ノート", GREEN, None)
    x = MG + 6; w = PW - 2 * MG - 12
    txt(c, x, y + 2, "第　　回　議題", 11, NAVY)
    line(c, x + 42, y + 8.4, x + w, y + 8.4, 0.8, GRAY)
    y += 14
    txt(c, x, y, "なまえ", 10.5, NAVY)
    line(c, x + 22, y + 6.4, x + 92, y + 6.4, 0.8, GRAY)
    txt(c, x + 100, y, "月　日", 10.5, NAVY)
    line(c, x + 122, y + 6.4, x + w, y + 6.4, 0.8, GRAY)
    y += 13

    y = sec(c, x, y, "話合いの まえに ── わたしの考え", w)
    y = para(c, x, y, "提案理由を 読んでから 書きます。", 10.5, w, color=GRAY)
    y = writelines(c, x, y + 1, w, 3)
    y += 4
    y = sec(c, x, y, "話合いの あいだ ── くらべて 思ったこと", w)
    y = para(c, x, y, "友だちの 考えで「なるほど」と 思ったことを 書きます。",
             10.5, w, color=GRAY)
    y = writelines(c, x, y + 1, w, 3)
    y += 4
    y = sec(c, x, y, "決まったこと", w)
    y = writelines(c, x, y, w, 2)
    y += 2
    txt(c, x, y, "やくわり（わたしが やること）", 10.5, NAVY)
    y = writelines(c, x, y + 4, w, 1)
    y += 4
    y = sec(c, x, y, "ふりかえり（やってみた あとで 書きます）", w)
    y = para(c, x, y, "はじめの 自分の考えと くらべて、どう 変わりましたか。",
             10.5, w, color=GRAY)
    y = writelines(c, x, y + 1, w, 3)
    ashi(c, SITE + "　／　A4・等倍（100%）で印刷")
    finish(c, path)


# ── 4. 司会進行メモ（A4に1枚・司会の子が持つ）────────────────
SHIKAI = [
    ("はじめの言葉", "これから 第　　回 学級会を 始めます。"),
    ("議題の かくにん", "今日の 議題は「　　　　　　　　　　」です。"),
    ("提案理由を 聞く", "提案した人、どうして みんなで 話したいのか"
                        "話してください。"),
    ("① 出し合う", "まず 考えを 出し合います。いいか わるいかは"
                    "あとで 言います。"),
    ("② くらべ合う", "出た考えを くらべます。提案理由に いちばん"
                      "合うのは どれですか。"),
    ("③ まとめる", "近い考えを まとめます。まとめても いいですか。"),
    ("決まったことの かくにん", "決まったことを 言います。これで いいですか。"),
    ("やくわりを 決める", "だれが 何を するか 決めます。"),
    ("ふりかえり", "今日の 話合いで よかったところを 話してください。"),
    ("おわりの言葉", "これで 第　　回 学級会を 終わります。"),
]


def shikai_memo():
    setpage(210, 297, 12)
    path = os.path.join(OUT, 'shikai-memo.pdf')
    clear(); c = newdoc(path)
    y = _waku(c, MG, 10, PW - 2 * MG, 272, "司会進行メモ", NAVY, None)
    x = MG + 5; w = PW - 2 * MG - 10
    y = para(c, x, y + 1, "上から 順に 読みます。□ に ✓ を 入れながら すすめます。",
             10.5, w, color=GRAY)
    y += 2
    for i, (na, kotoba) in enumerate(SHIKAI, 1):
        rect(c, x, y, 5.6, 5.6, None, GRAY, 0.8, 0.8)          # ✓の□
        txt(c, x + 9, y, "%d  %s" % (i, na), 11, NAVY, maxw=w - 9, role='body')
        yy = para(c, x + 9, y + 6.4, "「" + kotoba + "」", 11, w - 12)
        line(c, x, yy + 0.6, x + w, yy + 0.6, 0.4, HAIR)
        y = yy + 3.4
    para(c, x, y + 1, "★人数で 決めません。「なぜ そう思うのか」を 聞いてから"
                      "まとめます。", 10.5, w, color=RED, bold=True)
    ashi(c, SITE + "　／　A4・等倍（100%）で印刷")
    finish(c, path)


# ── 5. 話合いの流れ掲示（A4よこ・貼る紙・4ページ）──────────────
NAGARE = [
    ("①", "出し合う", "いいか わるいかは 言わない。\nまず ぜんぶ 出す。", BLUE),
    ("②", "くらべ合う", "提案理由に いちばん 合うのは どれか。", KI),
    ("③", "まとめる", "近い考えを まとめる。\n人数では 決めない。", PALER),
]


def nagare_keiji():
    setpage(297, 210, 16)
    path = os.path.join(OUT, 'nagare-keiji.pdf')
    clear(); c = newdoc(path)
    for i, (ban, na, yo, bg) in enumerate(NAGARE):
        if i: newpage(c)
        rect(c, MG, MG, PW - 2 * MG, PH - 2 * MG, bg, NAVY, 2.4, 4.0)
        txt(c, MG, MG + 14, ban, 60, NAVY, maxw=PW - 2 * MG, align='c',
            role='display', bg=bg)
        txt(c, MG, MG + 78, na, 56, NAVY, True, maxw=PW - 2 * MG, align='c',
            role='display', bg=bg)
        yy = MG + 132
        for ln in yo.split("\n"):
            txt(c, MG, yy, ln, 22, NAVY, maxw=PW - 2 * MG, align='c',
                role='display', bg=bg)
            yy += 13
    # まとめの1枚
    newpage(c)
    rect(c, MG, MG, PW - 2 * MG, PH - 2 * MG, None, NAVY, 2.4, 4.0)
    txt(c, MG, MG + 10, "話合いの ながれ", 34, NAVY, True, maxw=PW - 2 * MG,
        align='c', role='display')
    yy = MG + 42
    haba = (PW - 2 * MG - 20) / 3
    for i, (ban, na, yo, bg) in enumerate(NAGARE):
        xx = MG + 10 + i * haba
        rect(c, xx, yy, haba - 8, 96, bg, NAVY, 1.6, 3.0)
        txt(c, xx, yy + 8, ban, 30, NAVY, maxw=haba - 8, align='c',
            role='display', bg=bg)
        txt(c, xx, yy + 42, na, 26, NAVY, True, maxw=haba - 8, align='c',
            role='display', bg=bg)
        if i < 2:
            txt(c, xx + haba - 8, yy + 42, "→", 26, NAVY, maxw=8, align='c',
                role='display')
    txt(c, MG, yy + 108, "※ 賛成・反対の 人数では 決めません。「なぜ」を 残します。",
        18, NAVY, maxw=PW - 2 * MG, align='c', role='display')
    ashi(c, SITE + "　／　A4よこ・等倍（100%）で印刷")
    finish(c, path)


# ── 6. 賛成・反対マーク（A4に4枚・貼る紙）───────────────────
MARK = [("さんせい", GREEN, BLUE, "どこが いいと 思ったか"),
        ("はんたい", RED, PALER, "どこが 心配か"),
        ("つけたし", NAVY, KI, "足したい こと"),
        ("しつもん", NAVY, LGRAY, "わからない ところ")]


def sanhan_mark():
    setpage(210, 297, 10)
    path = os.path.join(OUT, 'sanhan-mark.pdf')
    clear(); c = newdoc(path)
    h = (PH - 2 * MG - 9) / 4
    for i, (na, iro, bg, memo) in enumerate(MARK):
        y = MG + i * (h + 3)
        rect(c, MG, y, PW - 2 * MG, h, bg, iro, 2.0, 3.0)
        txt(c, MG + 6, y + 9, na, 40, iro, True, maxw=110, role='display', bg=bg)
        txt(c, MG + 122, y + 12, memo, 16, NAVY, maxw=62, role='display', bg=bg)
        line(c, MG + 122, y + 30, PW - MG - 6, y + 30, 0.8, GRAY)
        line(c, MG + 122, y + 38, PW - MG - 6, y + 38, 0.8, GRAY)
        if i < 3:
            _kiri(c, y + h + 1.5)
    ashi(c, "短冊のそばに はります。数ではなく「なぜ」を 残す札です。"
            "　／　A4・等倍で印刷")
    finish(c, path)


def main():
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    gidai_post(); teian_card(); gakkyukai_note()
    shikai_memo(); nagare_keiji(); sanhan_mark()
    print("\n  6点とも できました → src/downloads/\n")


if __name__ == '__main__':
    main()
