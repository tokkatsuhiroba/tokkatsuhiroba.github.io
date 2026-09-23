#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TOKKATSU広場 ビルド
    src/*  ＋  src/news/*.md  ＋  src/jissen/*.md   →   公開用/index.html （1ファイル）

    python3 build.py            … 公開用/index.html を書く（＝公開するもの。縦スクロール1枚）
    python3 build.py --check    … 書かずに、何が入るかだけ見る
    python3 build.py --kyu      … 旧・本体（タブ版）の控え 公開用/index-kyu.html
    python3 build.py --kyu --simple … 簡素版 公開用/index-simple.html
    python3 build.py --tobira   … とびら版の試作（公開用/tobira.html）
    python3 build.py --buhin    … 広場の部品だけを検問する（--mihon で見本も書く）

決めごと（指示書・引き継ぎメモより）
    ・公開するのは index.html 1つだけ。外部ファイルを作らない
    ・ニュースはページの中に焼きこむ（fetch しない＝圏外でも読める）
    ・個人用「優アンテナ」の中身は、検問を通さないと1文字も出さない

※ 2026-09-21：このファイルは一度 0バイトになりました。
   出来上がりのHTML（_復元の手がかり/）と作業記録から組み直したものです。
"""

import io, os, re, sys, glob, math, datetime, calendar, json
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(ROOT, 'src')
# 公開するのはこの1つだけ。2026-09-21 から、中身は新版（縦スクロール1枚）です。
# ══ 「今日」は、日本の今日（2026-09-23）════════════════════
#   GitHub Actions のサーバーは UTC で動きます。日本時間の朝9時までは
#   向こうはまだ前の日で、`date.today()` が1日ずれます。
#   こよみの「日が過ぎたか」も、sitemap の lastmod も、
#   見るのは日本にいる人なので、日本の今日で数えます。
JST = datetime.timezone(datetime.timedelta(hours=9))


def kyou_jst():
    return datetime.datetime.now(JST).date()


OUT  = os.path.join(ROOT, '公開用', 'index.html')
# 旧・本体（タブで切りかえる版）。残してあるだけで、公開はしません
OUT_KYU = os.path.join(ROOT, '公開用', 'index-kyu.html')
# 簡素版（旧・本体のデザインだけ差しかえた版）
OUT_S  = os.path.join(ROOT, '公開用', 'index-simple.html')
CSS    = 'src/style.css'
CSS_S  = 'src/style-simple.css'
NEWS = os.path.join(SRC, 'news')
NG   = os.path.join(SRC, '_ngword.txt')

HOME_N = 3     # ホームに出す最新ニュースの数
NEWS_N = 12    # ニュース節に出す数（古いものは自然に落ちる）

JISSEN = os.path.join(SRC, 'jissen')   # すぐ使える実践（1件＝1ファイル）
GOODS  = os.path.join(SRC, 'goods')    # 学級会グッズ（1点＝1ファイル）
SHIRYO = os.path.join(SRC, 'shiryo')   # 資料の画像（1件＝1フォルダ。ページの中に埋めこむ）
BANSHO = os.path.join(SRC, 'bansho')   # 板書の写真（1件＝1フォルダ。板書のページにだけ埋めこむ）
KOMARI = os.path.join(SRC, 'komari')   # 困りごと（1件＝1ファイル。送られたら、そのまま出ます）
NITTEI = os.path.join(SRC, 'nittei')   # 送られた研究日程（1件＝1ファイル。手で足すぶんは src/app.js の EVENTS）
JISSEN_HOME_N = 2                      # ホームに出す実践の数

# 資料をページの中に入れるときの上限。ここを外すと配れない重さになります。
SHIRYO_KB_MAX  = 500.0   # 画像1枚
SHIRYO_MB_MAX  = 8.0     # 資料1件（1フォルダ）
SHIRYO_ZEN_MAX = 16.0    # 1ページに入る資料の合計
#
# ── 板書を「溜める」と決めた日のこと（2026-09-21）──────────
#   上限が16MBなのは、配るためではなく **スマホで開いたときの重さ** です。
#   だから溜めるなら、置き場所を分けるしかありません。
#     ・板書の写真は bansho.html に **だけ** 埋めこむ
#     ・実践の札からは「板書を見る →」で、そのページへ渡す
#   こうすると manabu.html は軽いまま、板書だけが太っていきます。
#   天井が近づいたら年度で割ります（bansho-2026.html → bansho-2027.html）。
#   そのとき慌てないよう、build の最後に「いま何MB・あと何枚」を出します。
BANSHO_NOKORI_KB = 120.0  # 残り枚数を見つもるときの、板書1枚の目安（実測して直してよい）
SITE_URL = 'https://yuutennis657-beep.github.io/tokkatsu-hiroba/'
OKURU_URL = ('https://script.google.com/macros/s/'
             'AKfycbwb0xkl5HpPDX2WqSov42N8L2FkAVD6ZYx5sbbs_7r332mmsRYY8_VYDyfD29yqKHCH/exec')

# ══ ページの分け方（2026-09-21に決めなおし）════════════════
#   もとは「index.html 1つだけ。外部ファイルを作らない」でした。
#   スマホで縦31画面あり、長すぎるという話から、決めごとのほうを直しました。
#   　　× 別ページへ飛ばさない
#   　　○ 飛んでよい。ただし飛び先の見た目を変えない
#   　　　（同じCSS・同じ帯が同じ位置・いまどこにいるかと戻り道が見える）
#   ページを分けるのは「節」の単位。1件ぶんの中身（実践の準備・流れ・板書、
#   のこり◯件、原文）は、いままでどおりページの中の <details> で開きます。
#
#   （ファイル名, ページの名前, 添えの1行, 入れる節のid）
#   2026-09-21 追記：こよみは、ホームに置きます（「つぎ、いつ」は入口で
#   見たいものなので）。だから ima だけ index.html に入っています。
PAGES = (
    # 2026-09-21 夜：板書を送るところを、ホームのいちばん上にしました。
    #   このサイトの目玉はここです。研究日程より前に出します。
    # ホームは「実践を送る」1本に絞りました（2026-09-22）。
    #   研究日程は、ホームのいちばん下にありました。目当ての人には遠く、
    #   送りに来た人には邪魔でした。ニュースと同じページの上に移します
    #   （どちらも「外の動きを知る」ものなので、隣どうしが自然です）。
    ('index.html',    'TOKKATSU広場', '', ('okuru',)),
    ('shiru.html',    '知る',   '特別活動って、なに。4つの内容は、どれ。ことばの意味も。',
     ('about', 'yotsu', 'kotoba')),
    ('manabu.html',   'はじめかた', '学級会の学習過程と、一次資料と、持ち帰れる道具。',
     ('manabu', 'shokai', 'jissen')),
    ('atsumaru.html', '集まる', '研究日程、ニュース、各地の研究会。',
     ('ima', 'news', 'kai')),
    # みんなの実践（2026-09-21 新設 → 2026-09-22 改称）。
    #   **このサイトの主役です。**だから帯の8つに入れました。
    #   かわりに「すぐ使える道具」を外しています（学ぶ と同じページなので、
    #   学ぶ の札から届きます）。帯は8つ＝スマホで2段4列、を崩しません。
    ('bansho.html',   'みんなの実践', '送ってもらった実践が、そのまま並びます。',
     ('bansho',)),
    # 困りごと（2026-09-21 夜 新設）。帯の8つには入れません。
    #   入口は ホームの「ちょっと聞きたい」の札です。
    # 困りごと（2026-09-21 夜 新設 → 2026-09-22 組み替え）。
    #   **書くところと、読むところを、同じページに置きました。**
    #   前は 書くところがホーム、読むところがこのページ で割れていました。
    #   困っている人が開いた先に、書く欄が無いのは おかしい、という話から。
    ('komari.html',   '困りごと', 'いま困っていることを書く。届いたものを読む。',
     ('kiku', 'komari')),
)
HOME = PAGES[0][0]

# 親のページ（帯に出ないページだけ）。頭のところに「← 学ぶ」を出すために使います。
#   帯で今どこにいるかが出ないぶん、ここで戻り道を見せます。
#   2026-09-22：みんなの実践は帯に出したので、ここから外しました
#   （帯が「いまどこ」を出すので、親への戻り道が二重になります）。
OYA = {'komari.html': ('index.html', 'igi', 'ホーム')}
# 節の名前。ホームの札と、ページの中の見出しで使い回します
SETSU_NA = {
    'ima':    '研究日程', 'news':   'ニュース',
    # 2026-09-22：「学ぶ」→「はじめかた」。
    #   このサイト全体が学ぶ場所なので、「学ぶ」では何の場所か分かりません。
    #   お悩み別の入口を困りごとへ渡したので、ここに残るのは
    #   **学級活動(1)の学習過程・一次資料・すぐ使える道具**。
    #   はじめての人が最初に読むところ、という顔になりました。
    'about':  '特活とは',   'manabu': 'はじめかた',
    'yotsu':  '4つの内容',  'jissen': 'すぐ使える道具',
    'shokai': 'このサイトを紹介する',
    'kai':    '日本の研究会', 'okuru': '実践を送る',
    # 2026-09-22：ここがこのサイトの主役です。
    #   「板書」は狭すぎました（いまは写真もPDFも議題も届きます）。
    #   ファイル名（bansho.html）と front matter の bansho: は、そのままです。
    #   URLは読まれないので変えません。配ったリンクも生きます。
    'bansho': 'みんなの実践', 'komari': '困りごと', 'kiku': 'ちょっと聞きたい',
    'kotoba': 'ことばの意味',
}

# 外のフォームなどのURL。差しかえる場所はここ1つだけ。
# src/body.html の {{FORM_IKEN}} のような目じるしが、ビルド時にこれに置きかわる。
LINKS = {
    'FORM_IKEN'  : 'https://forms.gle/Qkmej386gxQavi8z6',   # 困りごと・意見（2026-09-21 専用フォームに差しかえ）
    'FORM_JISSEN': 'https://forms.gle/fnWnivr61t2BA6tR7',   # 実践・板書の提供（同上）
    # 話す場。このサイトは「溜まる場」で、話は ぜんぶこちらです。
    # 2026-09-21：新版に切りかえたとき、リンクが1本も無くなっていました。
    #   名前は5か所に出るのに、押せる所がどこにも無い状態でした。
    'LINE_OC'    : 'https://line.me/ti/g2/9xsmT5pjwv8jTB-EtUfHn2OoA3Iq0H2ZZqq1gA'
                   '?utm_source=invitation&utm_medium=link_copy&utm_campaign=default',
    'SITE_URL'   : SITE_URL,
}

# ── とびら版（入口の試作）。OKが出たら本体に混ぜて、ここごと消す ──
OUT_T  = os.path.join(ROOT, '公開用', 'tobira.html')
# 新版（縦スクロール1枚）。2026-09-21 に1から書き直し、同じ日に「公開するもの」になりました
CSS_H  = 'src/style-hiroba.css'
CSS_T  = 'src/style-tobira.css'
ILL    = os.path.join(SRC, 'ill')      # イラスト 1枚＝1ファイル（Codex → SVGO → ここ）

SORA_H_MAX    = 50      # 空の高さの上限（svh）。超えると1枚目のカードが画面から落ちる
ILL_KB_MAX    = {240: 10.0, 120: 6.0}   # SVG 1枚の上限（場面は言葉が無いぶん描きこむ）
TOBIRA_KB_MAX = 300.0   # tobira.html 全体の上限

# とびらの1行（相談④。ここ1つで変わる）
TOBIRA_COPY = '人間関係形成・社会参画・自己実現'   # 特別活動の三つの視点

BASE_IRO = ('#FCFBF7', '#1C1C1A')      # 地と墨。どの絵でも使ってよい
# 名前 : (viewBoxの一辺, 場面色, その淡い面, 差し色)
ILL_SPEC = {
    'undokai'       : (240, '#D2552A', '#F6E2D8', '#E8C547'),
    'sotsugyo'      : (240, '#3A6EA5', '#DFE6EB', '#C98B5E'),
    'gakkyukai'     : (240, '#1F5C3F', '#DBE3DB', '#E8C547'),
    'sora-tama'     : (120, '#D2552A', '#F6E2D8', '#E8C547'),
    'sora-hato'     : (120, '#3A6EA5', '#DFE6EB', '#C98B5E'),
    'sora-fukidashi': (120, '#1F5C3F', '#DBE3DB', '#E8C547'),
}


# ── 広場1枚（方向A）。部品を1個ずつ作って、配置はコードで組む ──
BUHIN   = os.path.join(SRC, 'ill', 'buhin')   # 部品 1個＝1ファイル
HIROBA_W, HIROBA_H = 3200, 1200               # 広場の canvas。部品は「この中での実寸」で描く
                                              # 2400→3200に拡張（特活の4内容を並べるため）
SEN      = '2.5'      # 線の太さは、この1種類だけ。太さで遠近を出さない。
                      # 4だと黒が勝って重くなる／1.6だと置いたとき輪郭が消える（9/21に実測して決定）
BUHIN_KB = 4.0        # 部品1個の上限

# ── キャラクター（4つの内容を案内する4人）──
# 部品と同じ検問（線2.5・決めた9色・4KB）を通します。名前はここ1か所で決まります。
KYARA = os.path.join(SRC, 'ill', 'kyara')
KYARA_MEN = (
    ('gakkatsu', '学活くん',     '学級活動',   'n-gakkyu'),
    ('gyoji',    '行人',         '学校行事',   'n-gyoji'),
    ('jidokai',  '児童会ちゃん', '児童会活動', 'n-jidokai'),
    ('club',     'クラブマン',   'クラブ活動', 'n-club'),
)

# その活動が、大人になってからどの集団につながるか。
#   「特活とは」の4人ならびで、名前の下に1行ずつ出ます。
#   出どころ … 国立教育政策研究所『特別活動指導資料（小学校編）』6〜7ページ
KYARA_SAKI = {
    'gakkatsu': '職場、家庭へ',
    'gyoji':    '地域行事、催しへ',
    'jidokai':  '自治会、議会へ',
    'club':     'サークル、同好会へ',
}

# ── しるし（8つの札に出す、モノの絵）──
#   2026-09-23：札の絵が8枚とも人になっていて、ぱっと見て何の札か
#   分かりませんでした。札は **モノ**（カレンダー・地図・封筒…）にして、
#   人（4人のキャラクター）は **行き先の節の見出し** に立たせます。
#   押すまえに「何の場所か」、着いてから「だれが案内するか」の順です。
MARK = os.path.join(SRC, 'ill', 'mark')
# しるしで使ってよい色。採用イラストと同じ並びです（#B4D9E5 は使いません。
# 空の色 #A9E1F5 と見分けがつかず、2つある意味がないため）。
MARK_IRO = ('#FCFBF7', '#1C1C1A', '#A9E1F5', '#2FBA68', '#1F5C3F',
            '#D2552A', '#E8C547', '#3A6EA5', '#F6D8B8')
MARK_KB = 3.0         # しるし1枚の上限
MARK_BOX = 96         # しるしは、ぜんぶ 0 0 96 96。札に並べたとき大きさがそろう

# 広場で使ってよい色。地と墨をのぞいて6色まで。
HIROBA_IRO = {
    '#FCFBF7': '地（紙）',
    '#1C1C1A': '墨（線）',
    '#A9E1F5': '空',
    '#2FBA68': '緑（山・木）',
    '#1F5C3F': '濃い緑（影・黒板）',
    '#D2552A': '朱（旗・こども）',
    '#E8C547': '黄（日ざし・地面）',
    '#3A6EA5': '紺（屋根・式）',
    '#F6D8B8': '肌（顔と手だけ。地の色 #FCFBF7 を顔に使うと、穴が空いて見える）',
}


# ══════════════════════════════════════════════════════════
# 0. 小道具
# ══════════════════════════════════════════════════════════

class Tomeru(Exception):
    """検問にかかった。ビルドを止める。"""


def rd(rel):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        raise Tomeru('元ファイルが無い： %s' % rel)
    return io.open(p, encoding='utf-8').read().rstrip('\n')


def attr(s):
    """data-ar= の中に入れる。中の HTML（<span class='sub'> など）はわざと残す。"""
    return s.replace('"', '&quot;')


AR_MONTH = ['يناير', 'فبراير', 'مارس', 'أبريل', 'مايو', 'يونيو',
            'يوليو', 'أغسطس', 'سبتمبر', 'أكتوبر', 'نوفمبر', 'ديسمبر']

def ja_date(d): return '%d年%d月%d日' % (d.year, d.month, d.day)
def ja_md(d):   return '%d月%d日' % (d.month, d.day)
def ar_date(d): return '%d %s %d' % (d.day, AR_MONTH[d.month - 1], d.year)


def esc_html(x):
    return (str(x).replace('&', '&amp;').replace('<', '&lt;')
                  .replace('>', '&gt;').replace('"', '&quot;'))


def inline_md(x):
    """本文の1行。HTMLは通さない（フォームで受けた文をそのまま置くので）。**太字** だけ効く。"""
    x = esc_html(x)
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', x)


def md_html(body):
    """使える記法はこれだけ：## 見出し／- 箇条書き／1. 番号つき／空行で段落。
       段落の中の改行は <br> にする（板書の型を行で書けるように）。"""
    out, para = [], []
    st = {'lst': None}

    def close_list():
        if st['lst']:
            out.append('</%s>' % st['lst'])
            st['lst'] = None

    def flush_para():
        if para:
            out.append('<p>' + '<br>'.join(inline_md(l) for l in para) + '</p>')
            del para[:]

    def open_list(kind):
        if st['lst'] != kind:
            close_list()
            out.append('<%s>' % kind)
            st['lst'] = kind

    for raw in body.split('\n'):
        line = raw.rstrip()
        if not line.strip():
            flush_para(); close_list()
            continue
        m = re.match(r'^##\s+(.+)$', line)
        if m:
            flush_para(); close_list()
            out.append('<h4>' + inline_md(m.group(1)) + '</h4>')
            continue
        m = re.match(r'^(?:-|\*)\s+(.+)$', line)
        if m:
            flush_para(); open_list('ul')
            out.append('<li>' + inline_md(m.group(1)) + '</li>')
            continue
        m = re.match(r'^\d+[.．]\s*(.+)$', line)
        if m:
            flush_para(); open_list('ol')
            out.append('<li>' + inline_md(m.group(1)) + '</li>')
            continue
        close_list()
        para.append(line)
    flush_para(); close_list()
    return '\n'.join('        ' + l for l in out)


# ══════════════════════════════════════════════════════════
# 1. ニュースを読む（.md → 中身）
# ══════════════════════════════════════════════════════════

# front matter や本文に出てはいけない欄（＝優アンテナ側の欄）
KINSHI_RAN = ['効き目', '自分の考え', '返し', '分野', 'kikime', 'kangae', 'kaeshi']
HISSU      = ['date', 'source', 'url', 'title']


def parse_md(path):
    raw = io.open(path, encoding='utf-8').read()
    m = re.match(r'^---\n(.*?)\n---\n(.*)$', raw, re.S)
    if not m:
        raise Tomeru('%s：front matter（--- ではさむ部分）が無い' % os.path.basename(path))
    fm_text, body = m.group(1), m.group(2)

    fm = {}
    for line in fm_text.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' not in line:
            raise Tomeru('%s：front matter の「%s」に : が無い'
                         % (os.path.basename(path), line))
        k, v = line.split(':', 1)
        fm[k.strip()] = v.strip()

    # 日本語の要約 ／ @ar から下がアラビア語
    parts = re.split(r'^@ar\s*$', body.strip(), maxsplit=1, flags=re.M)
    fm['summary']    = parts[0].strip()
    fm['ar_summary'] = parts[1].strip() if len(parts) > 1 else ''
    fm['_file']      = os.path.basename(path)
    fm['_body_raw']  = body
    return fm


def kenmon(fm):
    """優アンテナと配る用の焼き分け。ここを通らないものは1文字も出さない。"""
    f = fm['_file']

    # ① 出す意思の明示。share: true が無いものは出さない
    if fm.get('share', '').lower() != 'true':
        return False, '%s … share: true が無いので出しません' % f

    # ② 優アンテナ側の欄が混ざっていないか
    for ran in KINSHI_RAN:
        if ran in fm:
            raise Tomeru('%s：「%s」の欄は配る用に出せません（優アンテナの欄）。'
                         '消すか、個人用フォルダに移してください。' % (f, ran))
        if re.search(r'^\s*%s\s*[:：]' % re.escape(ran), fm['_body_raw'], re.M):
            raise Tomeru('%s：本文に「%s：」の行があります（優アンテナの欄）。' % (f, ran))

    # ③ 必須の欄
    for k in HISSU:
        if not fm.get(k):
            raise Tomeru('%s：%s が空です' % (f, k))
    if not fm['summary']:
        raise Tomeru('%s：要約（本文）が空です' % f)

    # ④ リンクは一次情報だけ。http(s) 以外は出さない
    if not re.match(r'^https?://', fm['url']):
        raise Tomeru('%s：url が http(s) で始まっていません（%s）' % (f, fm['url']))

    # ⑤ 重要度は 1〜5
    try:
        fm['rank'] = int(fm.get('rank', '3'))
    except ValueError:
        raise Tomeru('%s：rank が数字ではありません（%s）' % (f, fm.get('rank')))
    if not 1 <= fm['rank'] <= 5:
        raise Tomeru('%s：rank は 1〜5 の数字です（%s）' % (f, fm['rank']))

    # ⑥ 日付
    try:
        fm['d'] = datetime.date(*[int(x) for x in fm['date'].split('-')])
    except Exception:
        raise Tomeru('%s：date は 2026-09-21 の形で書いてください（%s）' % (f, fm['date']))
    return True, None


def ngword_aru(text):
    """出してはいけない語が入っていたら、その語を返す。無ければ None。"""
    if not os.path.exists(NG):
        return None
    for line in io.open(NG, encoding='utf-8'):
        w = line.strip()
        if not w or w.startswith('#'):
            continue
        if w in text:
            return w
    return None


def ngword_check(text, where):
    """出してはいけない語が1つでも混ざっていたら止める（src/_ngword.txt）。"""
    w = ngword_aru(text)
    if w:
        raise Tomeru('%s に、出してはいけない語「%s」が入っています'
                     '（src/_ngword.txt を見てください）' % (where, w))


def load_news():
    kiji, tobashita = [], []
    for p in sorted(glob.glob(os.path.join(NEWS, '*.md'))):
        if os.path.basename(p).startswith('_'):
            continue
        fm = parse_md(p)
        ok, riyuu = kenmon(fm)
        if ok:
            kiji.append(fm)
        else:
            tobashita.append(riyuu)
    kiji.sort(key=lambda a: (a['d'], a['_file']), reverse=True)
    return kiji[:NEWS_N], tobashita


KIJI_T = """  <article>
    <div class="src"><span class="name" data-ar="{ar_source}">{source}</span><span class="dot"></span><span data-ar="{ar_date}">{ja_date}</span></div>
    <h3><a href="{url}" target="_blank" rel="noopener noreferrer" data-ar="{ar_title}">{title}</a></h3>
    <p class="sum" data-ar="{ar_summary}">{summary}</p>
    <div class="foot">
      <div class="rank"><span class="lb" data-ar="الأهمية">重要度</span><div class="bars">{bars}</div></div>
      <div class="acts">
        <button class="btn stock" type="button" aria-pressed="false" data-ar="حفظ">ストック</button>
        <a class="btn link" href="{url}" target="_blank" rel="noopener noreferrer" data-ar="المصدر">原文（外部）</a>
      </div>
    </div>
  </article>"""


def build_articles(kiji):
    out = []
    for a in kiji:
        bars = ('<i class="on"></i>' * a['rank']) + ('<i></i>' * (5 - a['rank']))
        out.append(KIJI_T.format(
            ar_source=attr(a.get('ar_source', '')), source=esc_html(a['source']),
            ar_date=attr(ar_date(a['d'])), ja_date=ja_date(a['d']),
            url=esc_html(a['url']), ar_title=attr(a.get('ar_title', '')),
            title=esc_html(a['title']),
            ar_summary=attr(a.get('ar_summary', '')), summary=esc_html(a['summary']),
            bars=bars))
    return '\n\n'.join(out)


def build_home_rows(kiji):
    rows = []
    for a in kiji[:HOME_N]:
        ar = a.get('ar_home', '')
        if ar and a.get('ar_home_sub'):
            ar = ar + "<span class='sub'>" + a['ar_home_sub'] + "</span>"
        rows.append('      <li><a href="%s" target="_blank" rel="noopener noreferrer">'
                    '<span class="t" data-ar="%s">%s<span class="sub">%s・%s</span></span>'
                    '<span class="d ext">外部</span></a></li>'
                    % (esc_html(a['url']), attr(ar),
                       esc_html(a.get('home') or a['title']),
                       esc_html(a['source']), ja_md(a['d'])))
    return '    <ul class="rows">\n' + '\n'.join(rows) + '\n    </ul>'


# ══════════════════════════════════════════════════════════
# 2. すぐ使える実践・学級会グッズ
# ══════════════════════════════════════════════════════════

def slug_of(path):
    """2026-09-21_keikaku-10min.md → keikaku-10min（日付は並び順に使うだけ）"""
    b = os.path.splitext(os.path.basename(path))[0]
    return b.split('_', 1)[1] if '_' in b else b


def load_goods():
    goods = {}
    for p in sorted(glob.glob(os.path.join(GOODS, '*.md'))):
        if os.path.basename(p).startswith('_'):
            continue
        fm = parse_md(p)
        f  = fm['_file']
        gid = os.path.splitext(f)[0]
        if not re.match(r'^[a-z0-9-]+$', gid):
            raise Tomeru('%s：グッズのファイル名は 英小文字・数字・- だけにしてください' % f)
        for k in ('title', 'desc', 'icon'):
            if not fm.get(k):
                raise Tomeru('%s：%s が空です' % (f, k))
        for k in ('pdf', 'docx'):
            v = fm.get(k, '')
            if v and not re.match(r'^https?://', v):
                raise Tomeru('%s：%s は https:// で始まる置き場のURLにしてください（%s）。'
                             '相対パスにすると、1ファイル配布が割れます' % (f, k, v))
        try:
            fm['order'] = int(fm.get('order', '99'))
        except ValueError:
            raise Tomeru('%s：order が数字ではありません' % f)
        fm['id'] = gid
        fm['used'] = []            # この後、実践側から埋める
        goods[gid] = fm
    return goods


def kenmon_jissen(fm, goods):
    """実践の検問。ニュースと同じ線引きに、グッズの実在確認を足す。"""
    f = fm['_file']
    if fm.get('share', '').lower() != 'true':
        return False, '%s … share: true が無いので出しません' % f
    for ran in KINSHI_RAN:
        if ran in fm:
            raise Tomeru('%s：「%s」の欄は配る用に出せません（優アンテナの欄）。' % (f, ran))
        if re.search(r'^\s*%s\s*[:：]' % re.escape(ran), fm['_body_raw'], re.M):
            raise Tomeru('%s：本文に「%s：」の行があります（優アンテナの欄）。' % (f, ran))
    # 実践か、議題か（2026-09-21）。箱は1つ、厚みだけがちがいます。
    #   jissen … 準備・流れ・板書・つまずき まで書いてあるもの
    #   gidai  … 「こんな議題が出ました」の1件。ひとことだけで足ります
    # 議題は、書く人のハードルをわざと下げるための型です。
    # だから「かかる時間」は聞きません（議題に時間は無い）。
    fm['kind'] = (fm.get('kind') or 'jissen').strip()
    if fm['kind'] not in ('jissen', 'gidai'):
        raise Tomeru('%s：kind は jissen（実践）か gidai（議題）のどちらかです（%s）'
                     % (f, fm['kind']))
    iru = ['date', 'title', 'grade', 'scene']
    if fm['kind'] == 'jissen':
        iru.append('time')
    for k in iru:
        if not fm.get(k):
            raise Tomeru('%s：%s が空です' % (f, k))
    # 議題には「かかる時間」がありません。欄そのものは、いつでもあることにします
    # （出すときに空なら、ただ出ません）
    fm['time'] = fm.get('time', '') or ''
    # ── 棚を2つに分ける目じるし（2026-09-22）────────────────
    #   okuri: true  … 先生方から**届いた**もの → 「みんなの実践」（このサイトの主役）
    #   書かなければ … こちらで**用意した**もの → 「すぐ使える道具」
    #   受け口（板書を受けとる.gs）が、届いたものに必ず okuri: true を付けます。
    #   ★ここを分けないと、「届いた実践はあちらです」と書いた道具箱の中に、
    #     その届いた実践が並びます（実際そうなっていたので分けました）。
    fm['okuri'] = str(fm.get('okuri', '')).strip().lower() == 'true'
    # 4つの内容のどれか。ここが無いと、どのカードにも集まりません
    aru = [n for n, _ in naiyo_ichiran()]
    fm['naiyo'] = fm.get('naiyo', '').strip()
    if fm['naiyo'] not in aru:
        raise Tomeru('%s：naiyo が「%s」です。4つの内容（%s）のどれかを書いてください'
                     % (f, fm['naiyo'] or '空', '／'.join(aru)))
    if not fm['summary']:
        raise Tomeru('%s：本文が空です' % f)
    if fm.get('url') and not re.match(r'^https?://', fm['url']):
        raise Tomeru('%s：url が http(s) で始まっていません（%s）' % (f, fm['url']))
    try:
        fm['d'] = datetime.date(*[int(x) for x in fm['date'].split('-')])
    except Exception:
        raise Tomeru('%s：date は 2026-09-21 の形で書いてください（%s）' % (f, fm['date']))
    # 届いた時こく。サイトから送られたものだけが持ちます（板書を受けとる.gs が書く）。
    #   「2026-09-22 17:33」の形。読めなければ、その日の0時として扱います。
    #   ★ここでは止めません。1件の書き方のせいでサイト全体が出なくなるためです。
    # 送った人の合いことばの**ハッシュ**（2026-09-22 夜）。
    #   これは公開されますが、ここから合いことばは出せません
    #   （128ビットのでたらめ＋SHA-256）。札に付けておくと、送った本人の
    #   ブラウザが「これは自分のだ」と見分けられます。
    fm['nushi'] = (fm.get('nushi') or '').strip().lower()
    if fm['nushi'] and not re.match(r'^[0-9a-f]{64}$', fm['nushi']):
        fm['nushi'] = ''        # 形がちがうものは、無いものとして扱います（止めません）
    fm['todoita_aru'] = bool((fm.get('todoita') or '').strip())
    fm['todoita'] = todoita_yomu(fm.get('todoita'), fm['d'])
    # 資料（指導案・スライド・板書など）。1行に「見出し|置き場」をカンマで並べる。
    #   shiryo: 指導案|ichiren-no-katsudo,  授業スライド|https://…
    #
    # 置き場は2とおり。
    #   ・`src/shiryo/◯◯/` のフォルダ名 … **ページの中で開きます**（外に1本もつながらない）
    #   ・https://… のURL              … 押すと外のタブが開きます（なるべく使わない）
    #
    # 2026-09-21：以前は外部リンクだけでした。「PDFを埋めると外に通信が飛ぶ」が理由です。
    # いまは **PDFを画像にして、この1枚の中に入れて**います。だから通信は飛びません。
    fm['shiryo_list'] = []
    for kumi in [x.strip() for x in fm.get('shiryo', '').split(',') if x.strip()]:
        if '|' not in kumi:
            raise Tomeru('%s：shiryo は「見出し|置き場」の形で書いてください（%s）' % (f, kumi))
        midashi, oki = [y.strip() for y in kumi.split('|', 1)]
        if not midashi:
            raise Tomeru('%s：shiryo の見出しが空です（%s）' % (f, kumi))
        if re.match(r'^https?://', oki):
            if not oki.startswith('https://'):
                raise Tomeru('%s：shiryo の URL は https:// にしてください（%s）' % (f, oki))
            fm['shiryo_list'].append((midashi, 'soto', oki))
            continue
        # 索引（2026-09-21）。**押せません。**「どこで手に入るか」を書くだけ。
        #   研究会や個人が作った資料は、書面の許可が無いと置けません。
        #   置けないものを「探せる」形にするのが索引です。ここが原則3
        #   （単なるリンク集にしない）を守る要なので、**説明を必ず書かせます**。
        #     shiryo: 全国大会の紀要|索引:全国特活研のサイト「過去の大会」から
        if oki.startswith('索引:') or oki.startswith('索引：'):
            setsumei = oki[3:].strip()
            if len(setsumei) < 6:
                raise Tomeru('%s：索引は「どこで手に入るか」を書いてください（いまは「%s」）。'
                             '見出しだけ並べると、ただのリンク集になります' % (f, setsumei))
            if re.search(r'https?://', setsumei):
                raise Tomeru('%s：索引の説明にURLを入れないでください（%s）。'
                             'URLを出すなら「見出し|https://…」の形にしてください' % (f, setsumei))
            fm['shiryo_list'].append((midashi, 'sakuin', setsumei))
            continue
        if not re.match(r'^[a-z0-9-]+$', oki):
            raise Tomeru('%s：shiryo の置き場「%s」は、src/shiryo/ のフォルダ名'
                         '（英小文字・数字・-）か、https:// のURLにしてください' % (f, oki))
        if not os.path.isdir(os.path.join(SHIRYO, oki)):
            aru = sorted(os.path.basename(x) for x in glob.glob(os.path.join(SHIRYO, '*'))
                         if os.path.isdir(x))
            raise Tomeru('%s：shiryo の「%s」が src/shiryo/ にありません（あるのは %s）'
                         % (f, oki, '、'.join(aru) or '無し'))
        fm['shiryo_list'].append((midashi, 'naka', oki))

    # 板書の写真（2026-09-21）。ここに書いたフォルダの画像は、
    # **bansho.html にだけ**埋めこみます。この実践の札には「板書を見る →」が出ます。
    # 同じ画像を2ページに埋めると、重さが倍になるためです。
    fm['bansho'] = (fm.get('bansho') or '').strip()
    if fm['bansho']:
        if not re.match(r'^[a-z0-9-]+$', fm['bansho']):
            raise Tomeru('%s：bansho は src/bansho/ のフォルダ名（英小文字・数字・-）で'
                         '書いてください（%s）' % (f, fm['bansho']))
        if not os.path.isdir(os.path.join(BANSHO, fm['bansho'])):
            aru = sorted(os.path.basename(x) for x in glob.glob(os.path.join(BANSHO, '*'))
                         if os.path.isdir(x))
            raise Tomeru('%s：bansho の「%s」が src/bansho/ にありません（あるのは %s）'
                         % (f, fm['bansho'], '、'.join(aru) or '無し'))

    ids = [g.strip() for g in fm.get('goods', '').split(',') if g.strip()]
    for g in ids:
        if g not in goods:
            raise Tomeru('%s：goods の「%s」は src/goods/ にありません（あるのは %s）'
                         % (f, g, '、'.join(sorted(goods)) or '無し'))
    fm['goods_ids'] = ids
    fm['slug'] = slug_of(fm['_file'])
    if not re.match(r'^[a-z0-9-]+$', fm['slug']):
        raise Tomeru('%s：ファイル名の _ から後ろは 英小文字・数字・- だけにしてください' % f)
    fm['by'] = fm.get('by') or '本サイト'
    # ── 推しポイント（2026-09-22 夜 依頼）──────────────────
    #   いちばん伝えたいことを、ひとことで。題のすぐ下に大きく出ます。任意です。
    #
    #   ★なぜ front matter ではなく、本文の1行目に目じるしで運ぶのか
    #     front matter に oshi: を書くのは **受け口（Apps Script）** です。
    #     受け口はこちらのファイルを直しても、貼り直すまで古いまま動きます。
    #     そのあいだ、入力してもらった推しポイントが どこにも残りません。
    #     本文に混ぜて運べば、**受け口を1行も触らずに** 今日から効きます。
    #   ★手で書く .md では、front matter の oshi: も使えます（そちらが優先）。
    hon = fm['summary'].strip()
    oshi_shirushi, hon = shirushi_hagasu(hon, OSHI_SHIRUSHI)
    oshi = (fm.get('oshi') or '').strip() or oshi_shirushi
    fm['oshi'] = oshi[:OSHI_MOJI_MAX]

    # ── 地域（2026-09-22 依頼）────────────────────────────
    #   「47都道府県で、日本の特色が見えたら楽しい」という話から。
    #   都道府県だけでなく **自治体（市区町村）まで** 書けるようにします。
    #   東京が多くなる見こみで、23区や支部で実態がちがうためです。
    #   ★任意です。書かなければ、札にも何も出ません。
    #   ★書いたぶんは公開ページに出ます（入力欄にもそう書いてあります）。
    #     名前を出す／出さない とは別の話なので、ここは ko を見ません。
    #   ★運び方は推しポイントと同じ（本文の頭に混ぜる）。理由は
    #     shirushi_hagasu の覚え書きに書きました。
    chiiki, hon = shirushi_hagasu(hon, CHIIKI_SHIRUSHI)
    ken = (fm.get('ken') or '').strip()
    shi = (fm.get('shi') or '').strip()
    if chiiki and not (ken or shi):
        kire = [x.strip() for x in chiiki.split(CHIIKI_KUGIRI)]
        ken = kire[0]
        shi = kire[1] if len(kire) > 1 else ''
    if ken and ken not in KEN_CHIHO:
        raise Tomeru('%s：ken の「%s」が 47都道府県にありません。'
                     '「東京都」「神奈川県」「北海道」のように書いてください' % (f, ken))
    if shi and not ken:
        raise Tomeru('%s：shi（自治体）だけ書いてあって、ken（都道府県）が'
                     'ありません。市区町村だけでは、どこの県か決まりません' % f)
    if len(shi) > CHIIKI_SHI_MAX:
        raise Tomeru('%s：shi（自治体）が長すぎます（%d字。%d字まで）'
                     % (f, len(shi), CHIIKI_SHI_MAX))
    if 'http' in shi or 'http' in ken:
        raise Tomeru('%s：地域の欄にURLは入れられません' % f)
    fm['ken'], fm['shi'] = ken, shi
    fm['chiiki'] = (ken + ('　' + shi if shi else '')) if ken else ''
    fm['chiho'] = KEN_CHIHO.get(ken, '')

    fm['summary'] = hon
    if not hon:
        # 推しポイントしか無いときは、それを本文にもします（空の札を出さない）
        fm['summary'] = hon = oshi
    # 最初の段落が「ひとこと」。残りが本文
    parts = re.split(r'\n\s*\n', fm['summary'].strip(), maxsplit=1)
    fm['lead'] = parts[0].strip()
    fm['rest'] = parts[1] if len(parts) > 1 else ''
    if fm['lead'].startswith('#'):
        raise Tomeru('%s：本文は見出しではなく、ひとことの段落から始めてください' % f)
    return True, None


# 本文の頭に混ぜて運ぶときの目じるし。
#   画面の入力欄（src/hiroba.html・src/kanri.html）と、ここでしか使いません。
OSHI_SHIRUSHI = '★推しポイント：'
OSHI_MOJI_MAX = 60
CHIIKI_SHIRUSHI = '★地域：'
CHIIKI_KUGIRI = '／'     # 都道府県と自治体の間（例：東京都／江東区）
CHIIKI_SHI_MAX = 20


def shirushi_hagasu(hon, shirushi):
    """本文の頭に混ぜて運んだ1行を、はがして返す。（値, のこりの本文）

       なぜ front matter ではなく、本文の頭に混ぜて運ぶのか
         新しい欄を front matter に書くのは **受け口（Apps Script）** です。
         受け口はこちらのファイルを直しても、貼り直すまで古いまま動きます。
         そのあいだ、入力してもらった字が どこにも残りません。
         本文に混ぜて運べば、**受け口を1行も触らずに** 今日から効きます。
       ★手で書く .md では front matter（oshi:／ken:／shi:）も使えます。
         そちらのほうが読みやすいので、front matter があればそちらが勝ちます。
       ★見るのは頭の4行だけです。本文の途中に同じ字が出ても、はがしません。
    """
    gyo = hon.split('\n')
    for i, x in enumerate(gyo[:4]):
        if x.startswith(shirushi):
            return x[len(shirushi):].strip(), '\n'.join(gyo[:i] + gyo[i + 1:]).strip()
    return '', hon


_GIT_TODOITA = {}


def git_todoita():
    """src/jissen/*.md が **git に入った時こく** を、ファイル名 → datetime で返す。

       なぜ要るのか（2026-09-22 夜）
         届いたものの時こくは、受け口（板書を受けとる.gs）が todoita: に
         書きます。ところが受け口は Apps Script 側にあって、こちらを直しても
         **貼り直すまで古いまま** です。その間に届いたものは todoita を
         持たず、その日の0時あつかいで いちばん下に沈みます（実測）。
       そこで、todoita が無いものは git に入った時こくで代わりにします。
       送られた1件は、受け口が届いたその場で commit するので、
       git の時こく ≒ 届いた時こく です。

       ★取れなくても止めません（履歴の浅い取りこみ・gitが無い所でも動きます）。
       ★こちらで用意した道具には使いません（→ load_jissen）。道具は
         date: の日づけが意味を持つので、書いた日で並べかえたくありません。"""
    if _GIT_TODOITA:
        return _GIT_TODOITA
    _GIT_TODOITA['_'] = None          # 2度 走らせない（取れなくても、ここで止める）
    try:
        import subprocess
        out = subprocess.run(
            ['git', '-c', 'core.quotepath=false',
             'log', '--diff-filter=A', '--reverse', '--date=iso-strict',
             '--format=%x00%ad', '--name-only', '--', 'src/jissen/'],
            cwd=ROOT, capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return _GIT_TODOITA
    hi = None
    for gyo in out.split('\n'):
        if gyo.startswith('\x00'):
            try:
                hi = datetime.datetime.fromisoformat(gyo[1:].strip()).replace(tzinfo=None)
            except ValueError:
                hi = None
        elif gyo.strip() and hi:
            na = os.path.basename(gyo.strip())
            _GIT_TODOITA.setdefault(na, hi)     # 最初に入ったときだけ
    return _GIT_TODOITA


def todoita_yomu(s, hi):
    """「2026-09-22 17:33」→ datetime。無ければ、その日の0時。
       ★止めません。並べるためだけに使う値なので、読めなければ0時あつかいです。"""
    if s:
        for katachi in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
            try:
                return datetime.datetime.strptime(str(s).strip(), katachi)
            except ValueError:
                pass
    return datetime.datetime.combine(hi, datetime.time.min)


def load_jissen(goods):
    kiji, tobashita = [], []
    for p in sorted(glob.glob(os.path.join(JISSEN, '*.md'))):
        if os.path.basename(p).startswith('_'):
            continue
        fm = parse_md(p)
        ok, riyuu = kenmon_jissen(fm, goods)
        if ok:
            kiji.append(fm)
        else:
            tobashita.append(riyuu)
    # ── 並び（2026-09-22 直し）─────────────────────────────
    #   前は (日づけ, ファイル名) の逆順でした。ところが届いたものの名前は
    #   bansho-20260922-9af344 のように **でたらめな6文字** で終わります。
    #   同じ日に2件 届くと、名前の順＝くじ引きになり、新しいほうが下に
    #   出ることがありました（実測：02:33 に届いたものが、01:00 のものの下）。
    #   だから **届いた時こく（todoita）** で並べます。
    #   こちらで用意した道具には todoita がありません。その日の0時として
    #   扱うので、道具どうしの並びは、これまでと変わりません。
    # todoita を持っていない「届いたもの」は、git に入った時こくで補います。
    #   受け口を貼り直すまでのあいだに届いたものが、下に沈まないように。
    gt = git_todoita()
    for a in kiji:
        if a.get('okuri') and not a.get('todoita_aru'):
            t = gt.get(os.path.basename(a['_file']))
            if t:
                a['todoita'] = t
    kiji.sort(key=lambda a: (a['todoita'], a['_file']), reverse=True)
    seen = set()
    for a in kiji:
        if a['slug'] in seen:
            raise Tomeru('実践の id「%s」が2つあります（ファイル名の _ から後ろが同じ）' % a['slug'])
        seen.add(a['slug'])
        for g in a['goods_ids']:
            goods[g]['used'].append(a)
    return kiji, tobashita


# ══ 困りごと（2026-09-21 夜 新設）════════════════════════
#   サイトの入力欄から送られた1件が、そのままここに出ます。
#   **誰の目も通りません。**板書と同じ決めごとです。
#   ★ここだけは、当たったら「止める」のではなく「その1件を出さない」に
#     しています。1件の困りごとでサイト全体が止まると、送った人にも
#     ほかの人にも分からないからです。
KOMARI_MOJI_MAX = 1000


def load_komari():
    kiji, tobashita = [], []
    for p in sorted(glob.glob(os.path.join(KOMARI, '*.md'))):
        if os.path.basename(p).startswith('_'):
            continue
        fm = parse_md(p)
        f = fm['_file']
        if fm.get('share', '').lower() != 'true':
            tobashita.append('%s … share: true が無いので出しません' % f)
            continue
        hon = fm['summary'].strip()
        if not hon:
            tobashita.append('%s … 中身が空です' % f)
            continue
        w = ngword_aru(hon + fm.get('grade', ''))
        if w:
            tobashita.append('%s … 出してはいけない語「%s」が入っています' % (f, w))
            continue
        try:
            fm['d'] = datetime.date(*[int(x) for x in fm['date'].split('-')])
        except Exception:
            tobashita.append('%s … date が 2026-09-21 の形ではありません' % f)
            continue
        fm['hon'] = hon[:KOMARI_MOJI_MAX]
        fm['grade'] = (fm.get('grade') or '').strip()
        fm['slug'] = slug_of(f)

        # 短い言葉。お悩み別の入口に出すのは、これです。
        #   送られたときは、Apps Script が本文の1行目から作ります。
        #   長すぎたり、言い方が個別すぎたりしたら、**あとから手で直せます**。
        fm['mijikai'] = (fm.get('title') or '').strip() or mijikaku(hon)

        # ここから下の2つは、**あとから人が足す欄**です。
        #   naiyo … 4つの内容のどれか。足すと、その内容のカードにも並びます
        #   saki  … 学級活動(1)の学習過程の段階（1〜5）。足すと、押せる札になり
        #           「学ぶ」のそこが開きます。＝ この悩みに答えが付いた、という印
        # どちらも空のままで出ます。**答えが無いことも情報**なので隠しません。
        aru = [n for n, _ in naiyo_ichiran()]
        fm['naiyo'] = (fm.get('naiyo') or '').strip()
        if fm['naiyo'] and fm['naiyo'] not in aru:
            tobashita.append('%s … naiyo が「%s」です（%s のどれか）'
                             % (f, fm['naiyo'], '／'.join(aru)))
            continue
        # 場面（学級活動(1) など）。実践と同じ項目にしたので、送られた時点で入ります。
        # 古い1件には無いので、空でも通します。
        fm['scene'] = (fm.get('scene') or '').strip()
        # 提供（2026-09-22）。名前は任意で、送った人が「出してよい」に
        # 印を入れたときだけ入ります。無ければ、札には何も出ません。
        fm['by'] = (fm.get('by') or '').strip()
        fm['saki'] = (fm.get('saki') or '').strip()
        if fm['saki'] and fm['saki'] not in '12345':
            tobashita.append('%s … saki が「%s」です（1〜5 か、空）' % (f, fm['saki']))
            continue

        kiji.append(fm)
    kiji.sort(key=lambda a: (a['d'], a['_file']), reverse=True)
    return kiji, tobashita


def mijikaku(hon, n=26):
    """本文から、札に出す短い言葉を作る。1行目を、文の切れ目で切ります。"""
    gyo = hon.split('\n')[0].strip().lstrip('#-・ 　')
    for ku in ('。', '？', '?', '！', '!'):
        if 0 < gyo.find(ku) <= n:
            return gyo[:gyo.find(ku)]
    return gyo if len(gyo) <= n else gyo[:n] + '…'


# 内容のふだは、実践の札と同じ見た目（.bfuda-tag t--◯◯）にします。
# 同じ内容の困りと実践が、同じ色のふだで並ぶようにするためです。
KOMARI_T = """      <article class="komari-fuda" id="k-{slug}">
        <p class="komari-hi">{tag}{hi}{grade}</p>
        <div class="komari-hon">{hon}</div>
{by}      </article>"""
# 名乗ってくださった人だけ、下に小さく出します。
# 名乗らないのが既定なので、無い札のほうが多くて当たり前です。
KOMARI_BY = """        <p class="komari-by">{by}</p>
"""
KOMARI_TAG = '<span class="bfuda-tag t--{nid}">{ja}</span>　'

KOMARI_KARA = """      <p class="komari-mada">まだ1件も届いていません。<br>
      ホームの <a href="#kiku">ちょっと聞きたい</a> から、いま困っていることを送ってください。</p>"""


def build_komari(komari):
    if not komari:
        return KOMARI_KARA
    return '\n'.join(
        KOMARI_T.format(slug=a['slug'], hi=a['d'].strftime('%Y年%-m月%-d日'),
                        tag=(KOMARI_TAG.format(nid=a['naiyo'],
                                               ja=esc_html(a['scene'] or naiyo_ja(a['naiyo'])))
                             if a['naiyo'] else ''),
                        grade=('　' + esc_html(a['grade'])) if a['grade'] else '',
                        by=(KOMARI_BY.format(by=esc_html(sensei_ja(a['by'])))
                            if a['by'] else ''),
                        hon=md_html(a['hon']))
        for a in komari)


# ══ 資料を、ページの中で開く ══════════════════════════════
#   PDFのままだと <embed> になり、端末しだいで開きません。
#   1ページ＝1枚の画像にして、この1枚のHTMLの中に入れます。
#   だから **外に1本もつながりません**（開いただけで通信が飛ばない）。
SHIRYO_MIME = {'.webp': 'image/webp', '.png': 'image/png',
               '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg'}


def gazou_size(b, f):
    """画像の横と縦を、頭のところだけ見て測る（width/height を入れて、開くときに紙が踊らないように）。"""
    if b[:4] == b'RIFF' and b[8:12] == b'WEBP':
        c = b[12:16]
        if c == b'VP8X':
            return (int.from_bytes(b[24:27], 'little') + 1,
                    int.from_bytes(b[27:30], 'little') + 1)
        if c == b'VP8 ':
            i = b.index(b'\x9d\x01\x2a', 20) + 3
            return (int.from_bytes(b[i:i + 2], 'little') & 0x3fff,
                    int.from_bytes(b[i + 2:i + 4], 'little') & 0x3fff)
        if c == b'VP8L':
            n = int.from_bytes(b[21:25], 'little')
            return ((n & 0x3fff) + 1, ((n >> 14) & 0x3fff) + 1)
    if b[:8] == b'\x89PNG\r\n\x1a\n':
        return (int.from_bytes(b[16:20], 'big'), int.from_bytes(b[20:24], 'big'))
    # JPEG（2026-09-21 追加）。板書は送り手のブラウザが JPEG にして送ってきます。
    # 頭から目印（0xFFxx）をたどって、大きさが書いてある区画（SOF）を1つ見つけます。
    if b[:2] == b'\xff\xd8':
        i, n = 2, len(b)
        while i + 9 < n:
            if b[i] != 0xFF:            # 目印でなければ1つ進む
                i += 1
                continue
            m = b[i + 1]
            if m == 0xFF:               # 詰めもの
                i += 1
                continue
            if m == 0x01 or 0xD0 <= m <= 0xD8:   # 長さを持たない目印
                i += 2
                continue
            if m == 0xD9 or m == 0xDA:  # 終わり／画そのもの。ここから先に大きさは無い
                break
            naga = int.from_bytes(b[i + 2:i + 4], 'big')
            # SOF0〜SOF15（0xC4 DHT・0xC8・0xCC DAC は仲間ではない）
            if 0xC0 <= m <= 0xCF and m not in (0xC4, 0xC8, 0xCC):
                return (int.from_bytes(b[i + 7:i + 9], 'big'),
                        int.from_bytes(b[i + 5:i + 7], 'big'))
            i += 2 + naga
    raise Tomeru('%s：大きさが読めませんでした（WebP・PNG・JPEG のどれかにしてください）' % f)


# 1ページに入れた資料の合計（ビルドのはじめに0に戻す）
# ページごとの帳面。どのページが、いま何バイト抱えているか。
#   2026-09-21：前は1つの数でした。板書を別のページに分けたので、
#   ページごとに数えないと、板書の重さが実践の側の上限を食ってしまいます。
_GOUKEI = {}


def shiryo_yomu(oki, moto=None, page='manabu.html'):
    """置き場の画像を、名前の順に読む。戻りは [(data URI, 横, 縦)]。

       moto … src/shiryo か src/bansho（省略すると src/shiryo）
       page … どのページに埋めこむか。上限はページごとに数えます。
    """
    moto = moto or SHIRYO
    na = 'src/' + os.path.basename(moto)
    tokoro = os.path.join(moto, oki)
    import base64
    mai, goukei = [], 0
    for p in sorted(glob.glob(os.path.join(tokoro, '*'))):
        e = os.path.splitext(p)[1].lower()
        if e not in SHIRYO_MIME:
            continue
        b = io.open(p, 'rb').read()
        kb = len(b) / 1024.0
        if kb > SHIRYO_KB_MAX:
            raise Tomeru('%s/%s/%s が %.0fKB あります（上限 %.0fKB）。'
                         '横1000pxくらいのWebPにしてください'
                         % (na, oki, os.path.basename(p), kb, SHIRYO_KB_MAX))
        goukei += len(b)
        w, h = gazou_size(b, '%s/%s/%s' % (na, oki, os.path.basename(p)))
        mai.append(('data:%s;base64,%s' % (SHIRYO_MIME[e], base64.b64encode(b).decode()), w, h))
    if not mai:
        raise Tomeru('%s/%s/ に画像がありません（.webp か .png）' % (na, oki))
    mb = goukei / 1024.0 / 1024.0
    if mb > SHIRYO_MB_MAX:
        raise Tomeru('%s/%s/ が合わせて %.1fMB あります（上限 %.0fMB）。'
                     'ページが重くなるので、要るページだけにしてください' % (na, oki, mb, SHIRYO_MB_MAX))
    _GOUKEI[page] = _GOUKEI.get(page, 0) + goukei
    zen = _GOUKEI[page] / 1024.0 / 1024.0
    if zen > SHIRYO_ZEN_MAX:
        raise Tomeru('%s に入れた画像が合わせて %.1fMB になりました（上限 %.0fMB）。'
                     'スマホで開くには重すぎます。'
                     '板書なら、年度で分けるときが来ています（bansho-2026.html のように）'
                     % (page, zen, SHIRYO_ZEN_MAX))
    return mai


# 2026-09-22 夜（依頼）：ふた（<details>）をやめて、はじめから出します。
#   板書の中身を ふたに入れずそのまま出すと決めたのと、同じ理由です
#   （「わざわざ押したくない」）。資料だけ ふたの中に残っていました。
#   ★画像は loading="lazy" のままなので、画面に入るまで読みません。
# 受け口が自動で付ける名前。これのときは、見出しごと出しません
#   （2026-09-23 依頼：「送ってもらった資料」という文言はいらない）。
#   実践の札の中では、言わなくても何の資料か分かるためです。
#   指導案など、自分で名前を付けた資料のときは、その名前を出します。
SHIRYO_JIDOU_NA = '送ってもらった資料'

SHIRYO_MIDASHI = """          <p class="shiryo-midashi">{midashi}<span class="shiryo-n">{n}ページ</span></p>
"""

SHIRYO_MADO = """        <div class="shiryo-hiraku">
{midashi}          <div class="shiryo-naka">
            <div class="shiryo-mado">
{gazou}
            </div>
{zen}          </div>
        </div>
"""

# 窓の **外** に置く［大きく見る］（2026-09-23）。
#   窓の中（図の下）に置くと、写真の高さをこの行に取られます。
#   「みんなの実践」の札では、これを使わずに札の足へ置きます（→ ZEN_B）。
SHIRYO_ZEN = ('            <p class="shiryo-zen">'
              '<button class="shot-b" type="button" data-zen="shiryo">'
              '大きく見る</button></p>\n')


def shiryo_mado(midashi, oki, alt, moto=None, page='manabu.html', zen=True):
    """資料1件ぶんの「ページの中で開く窓」。
       zen=False … ［大きく見る］を、ここには出しません。
       「みんなの実践」の札では、札の足（提供…の行）に置くためです。"""
    mai = shiryo_yomu(oki, moto, page)
    g = [GAZOU.format(uri=uri, alt=esc_html('%s %dページめ' % (alt, i + 1)),
                      w=w, h=h,
                      kazu=(GAZOU_KAZU.format(i=i + 1, n=len(mai))
                            if len(mai) > 1 else ''))
         for i, (uri, w, h) in enumerate(mai)]
    return SHIRYO_MADO.format(
        midashi=('' if midashi.strip() == SHIRYO_JIDOU_NA
                 else SHIRYO_MIDASHI.format(midashi=esc_html(midashi), n=len(mai))),
        n=len(mai), gazou='\n'.join(g),
        zen=(SHIRYO_ZEN if (zen and mai) else ''))


def goods_status(g):
    if g.get('pdf') and g.get('docx'): return 'PDF・Word'
    if g.get('pdf'):  return 'PDF'
    if g.get('docx'): return 'Word'
    return ''


def line_share(text):
    """LINEに「本文が入った状態」で開くURL（指示書6-5）。送るのは押した人だけ。"""
    from urllib.parse import quote
    return 'https://line.me/R/share?text=' + quote(text, safe='')


JART = """  <article class="jissen" id="j-{slug}">
    <div class="src"><span class="name">{scene}</span><span class="dot"></span><span>{grade}</span><span class="dot"></span><span>{time}</span></div>
    <h3>{title}</h3>
    <p class="sum">{lead}</p>
{more}{set}{weekly}    <div class="foot">
      <span class="by"><span data-ar="مقدَّم من">提供</span>：{by}</span>
      <div class="acts">
        <a class="btn link" href="{line}" target="_blank" rel="noopener noreferrer" data-ar="ناقش هذه الممارسة في LINE">この実践について話す（LINE）</a>
        <button class="btn copy" type="button" data-copy-text="{abs}" data-ar="نسخ رابط هذه الممارسة">この実践のURLをコピー</button>
      </div>
    </div>
  </article>"""

JMORE = """    <details class="jmore">
      <summary><span class="p" data-ar="التفاصيل: التحضير والمسار والسبورة">くわしく（準備・流れ・板書）</span><span class="m" data-ar="إغلاق">とじる</span></summary>
      <div class="jbody">
{body}
      </div>
    </details>
"""

JSET = """    <div class="jset">
      <p class="jset-h" data-ar="يُستخدم مع هذه الأدوات">セットで使うもの</p>
      <ul class="glist">
{items}
      </ul>
    </div>
"""

JSHIRYO = """    <div class="jset jshiryo">
      <p class="jset-h" data-ar="مواد للتنزيل">持ち帰れる資料</p>
      <div class="acts">
{items}
      </div>
    </div>
"""

JWEEKLY = """    <div class="weekly">
      <span class="wl" data-ar="سطر لخطّة الأسبوع">週案用のひとこと</span>
      <span class="wt" id="w-{slug}">{weekly}</span>
      <button class="btn copy" type="button" data-copy="w-{slug}" data-ar="نسخ">コピー</button>
    </div>
"""


def build_jissen(kiji, goods):
    out = []
    for a in kiji:
        more = JMORE.format(body=md_html(a['rest'])) if a['rest'].strip() else ''
        items = []
        for g in a['goods_ids']:
            st = goods_status(goods[g])
            tag = ('<span class="gst">%s</span>' % st) if st \
                  else '<span class="gst" data-ar="قيد الإعداد">準備中</span>'
            items.append('        <li><a href="#manabu/goods-%s" data-ar="%s">%s</a>%s</li>'
                         % (g, attr(goods[g].get('ar_title', '')), esc_html(goods[g]['title']), tag))
        setb = JSET.format(items='\n'.join(items)) if items else ''
        # 資料。フォルダに置いたものは、このページの中で開きます。
        # 外のURLだけは、押すと別のタブが開きます（そう書いてあります）
        sh, mado = [], []
        for m, kind, v in a.get('shiryo_list', []):
            if kind == 'naka':
                mado.append(shiryo_mado(m, v, a['title'], page='公開用/index.html'))
            elif kind == 'sakuin':
                # 索引は押せません。どこで手に入るかを書くだけです
                sh.append('        <span class="sakuin"><b>%s</b>%s</span>'
                          % (esc_html(m), esc_html(v)))
            else:
                sh.append('        <a class="btn" href="%s" target="_blank" '
                          'rel="noopener noreferrer">%s（外部）</a>'
                          % (esc_html(v), esc_html(m)))
        shb = ''.join(mado) + (JSHIRYO.format(items='\n'.join(sh)) if sh else '')
        weekly = JWEEKLY.format(slug=a['slug'], weekly=esc_html(a['weekly'])) if a.get('weekly') else ''
        absurl = SITE_URL + '#manabu/j-' + a['slug']
        out.append(JART.format(
            slug=a['slug'], scene=esc_html(a['scene']), grade=esc_html(a['grade']),
            time=esc_html(a['time']), title=esc_html(a['title']), lead=inline_md(a['lead']),
            more=more, set=setb + shb, weekly=weekly, by=esc_html(a['by']),
            line=line_share(a['title'] + '\n' + absurl), abs=absurl,
        ))
    return '\n\n'.join(out)


def build_jissen_home(kiji):
    rows = []
    for a in kiji[:JISSEN_HOME_N]:
        rows.append('      <li><a href="#manabu/j-%s"><span class="t">%s<span class="sub">%s・%s・%s</span></span>'
                    '<span class="d">→</span></a></li>'
                    % (a['slug'], esc_html(a['title']), esc_html(a['scene']),
                       esc_html(a['grade']), esc_html(a['time'])))
    if not rows:
        return '    <p class="placeholder">実践はまだありません。</p>'
    return '    <ul class="rows">\n' + '\n'.join(rows) + '\n    </ul>'


def build_goods(goods):
    out = []
    for g in sorted(goods.values(), key=lambda x: (x['order'], x['id'])):
        st = goods_status(g)
        if st:
            dl = '<span class="dl">'
            if g.get('pdf'):
                dl += '<a class="btn" href="%s" target="_blank" rel="noopener noreferrer">PDF</a>' % esc_html(g['pdf'])
            if g.get('docx'):
                dl += '<a class="btn" href="%s" target="_blank" rel="noopener noreferrer">Word</a>' % esc_html(g['docx'])
            dl += '</span>'
        else:
            dl = '<span class="go" data-ar="قيد الإعداد">準備中</span>'
        use = ''
        if g['used']:
            links = '、'.join('<a href="#manabu/j-%s">%s</a>' % (a['slug'], esc_html(a['title'])) for a in g['used'])
            use = '<span class="use"><span data-ar="الممارسات التي تستخدمه">使う実践</span>：%s</span>' % links
        out.append('      <li><div class="tile goods" id="goods-%s"><svg class="gthumb" aria-hidden="true"><use href="#%s"/></svg>'
                   '<span class="tl"><b class="tt" data-ar="%s">%s</b><span class="ts" data-ar="%s">%s</span>%s</span>%s</div></li>'
                   % (g['id'], esc_html(g['icon']), attr(g.get('ar_title', '')), esc_html(g['title']),
                      attr(g.get('ar_desc', '')), esc_html(g['desc']), use, dl))
    return '    <ul class="tiles">\n' + '\n'.join(out) + '\n    </ul>'


# ══════════════════════════════════════════════════════════
# 2-3. イラスト（Codexの出したSVGを、規格どおりか見てから取りこむ）
# ══════════════════════════════════════════════════════════

def kenmon_ill(name, s, box, yurusu):
    """1枚ぶんの検問。かかったら Tomeru を投げる。"""
    f = 'src/ill/%s.svg' % name

    atama = s[:s.index('>') + 1] if '>' in s else s
    if re.search(r'\b(width|height)\s*=', atama):
        raise Tomeru('%s：<svg> に width / height が付いています。'
                     'CSSで伸縮させるので外してください' % f)

    if 'viewBox="0 0 %d %d"' % (box, box) not in s:
        raise Tomeru('%s：viewBox は "0 0 %d %d" にしてください（並びがそろわなくなります）'
                     % (f, box, box))

    if '<title>' not in s:
        raise Tomeru('%s：<title> がありません。読み上げたときに無言になります' % f)

    for warui, riyuu in (('<image',    '写真の混入（容量が破裂します）'),
                         ('data:image', '写真の混入（容量が破裂します）'),
                         ('<text',     '書体の無い端末で崩れます'),
                         ('<style',    '属性で塗ってください')):
        if warui in s:
            raise Tomeru('%s：%s が使われています。%s' % (f, warui, riyuu))

    warui_id = [i for i in re.findall(r'\sid="([^"]+)"', s) if not i.startswith('ill-')]
    if warui_id:
        raise Tomeru('%s：id は "ill-" で始めてください（本体と重なるとリンクが迷子になります）： %s'
                     % (f, '、'.join(warui_id)))

    soto = sorted(set(c.upper() for c in re.findall(r'#[0-9A-Fa-f]{3,8}', s))
                  - set(c.upper() for c in yurusu))
    if soto:
        raise Tomeru('%s：決めた5色の外の色が使われています： %s\n'
                     '     使ってよいのは %s です'
                     % (f, '、'.join(soto), '、'.join(yurusu)))

    kb = len(s.encode('utf-8')) / 1024.0
    if kb > ILL_KB_MAX[box]:
        raise Tomeru('%s：%.1fKB あります（上限 %.0fKB）。'
                     'npx svgo で軽くしてください' % (f, kb, ILL_KB_MAX[box]))
    return kb


def kokkaku(s):
    """場面の絵から骨格を測る。3枚そろっていないと、並べたときに崩れる。"""
    maru = [(float(a), float(b), float(r), c)
            for a, b, r, c in re.findall(
                r'<circle[^>]*cx="([\d.]+)"[^>]*cy="([\d.]+)"[^>]*r="([\d.]+)"[^>]*fill="([^"]+)"', s)]
    atama = [m for m in maru if m[3].upper() == '#1C1C1A' and m[2] >= 10]
    hikari = [m for m in maru if m[1] < 95 and m[2] >= 12]
    komono = [m for m in maru if m[1] >= 180]
    return (('(%d,%d) r%d' % (hikari[0][0], hikari[0][1], hikari[0][2])) if hikari else '－',
            ('(%d,%d) r%d' % (atama[0][0], atama[0][1], atama[0][2])) if atama else '－',
            len(komono))


def load_ill():
    """src/ill/*.svg を読んで検問する。戻りは {名前: SVGの中身} と、目で見るための一覧。"""
    e, hyo = {}, []
    for name, (box, iro, awa, sashi) in sorted(ILL_SPEC.items()):
        path = os.path.join(ILL, name + '.svg')
        if not os.path.exists(path):
            raise Tomeru('src/ill/%s.svg がありません（仮のままでよいので置いてください）' % name)
        s  = io.open(path, encoding='utf-8').read().strip()
        kb = kenmon_ill(name, s, box, BASE_IRO + (iro, awa, sashi))
        e[name] = s
        k = kokkaku(s) if box == 240 else ('－', '－', 0)
        hyo.append((name, box, kb, ('あり' if re.search(r'\srx="', s) else '－'),
                    sorted(set(re.findall(r'stroke-width="([\d.]+)"', s)), key=float),
                    '仮' if 'まだ仮です' in s else '本', k))
    return e, hyo


# ══════════════════════════════════════════════════════════
# 2-4. 広場の部品（方向A）。規律を機械で守らせる
# ══════════════════════════════════════════════════════════

def kenmon_buhin(name, s, doko='src/ill/buhin'):
    f = '%s/%s.svg' % (doko, name)

    atama = s[:s.index('>') + 1] if '>' in s else s
    if re.search(r'\b(width|height)\s*=', atama):
        raise Tomeru('%s：<svg> に width / height が付いています。'
                     '部品は viewBox だけで大きさを決めます' % f)

    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', s)
    if not m:
        raise Tomeru('%s：viewBox="0 0 幅 高さ" がありません' % f)
    w, h = float(m.group(1)), float(m.group(2))
    if w > HIROBA_W or h > HIROBA_H:
        raise Tomeru('%s：%g×%g は広場（%d×%d）より大きいです' % (f, w, h, HIROBA_W, HIROBA_H))

    if '<title>' not in s:
        raise Tomeru('%s：<title> がありません' % f)

    for warui, riyuu in (('<image', '写真の混入'), ('data:image', '写真の混入'),
                         ('<text', '書体の無い端末で崩れる'), ('<style', '属性で塗る'),
                         ('Gradient', 'グラデーションは使わない'), ('<filter', 'ぼかし・影は使わない')):
        if warui in s:
            raise Tomeru('%s：%s が使われています（%s）' % (f, warui, riyuu))

    warui_id = [i for i in re.findall(r'\sid="([^"]+)"', s) if not i.startswith('ill-')]
    if warui_id:
        raise Tomeru('%s：id は "ill-" で始めてください： %s' % (f, '、'.join(warui_id)))

    # ★ここが要。線の太さが1種類でないと、並べたとき「絵」ではなく「図形」に見える
    futosa = sorted(set(re.findall(r'stroke-width="([\d.]+)"', s)), key=float)
    hoka = [x for x in futosa if x != SEN]
    if hoka:
        if len(futosa) == 1:
            raise Tomeru('%s：線の太さが %s になっています。広場の線は %s です'
                         % (f, futosa[0], SEN))
        raise Tomeru('%s：線の太さが %d 種類あります（%s）。'
                     '広場の線は %s の1種類だけです。太さで遠近を出さないでください'
                     % (f, len(futosa), ' / '.join(futosa), SEN))

    soto = sorted(set(c.upper() for c in re.findall(r'#[0-9A-Fa-f]{3,8}', s)) - set(HIROBA_IRO))
    if soto:
        raise Tomeru('%s：決めた%d色の外の色が使われています： %s'
                     % (f, len(HIROBA_IRO), '、'.join(soto)))

    kb = len(s.encode('utf-8')) / 1024.0
    if kb > BUHIN_KB:
        raise Tomeru('%s：%.1fKB あります（上限 %.0fKB）。'
                     '大きすぎる部品は、もっと小さく分けてください' % (f, kb, BUHIN_KB))

    katachi = sum(len(re.findall(r'<%s[ />]' % t, s))
                  for t in ('path', 'circle', 'rect', 'ellipse', 'polygon', 'polyline', 'line'))
    return kb, w, h, katachi, sorted(set(c.upper() for c in re.findall(r'#[0-9A-Fa-f]{6}', s)))


def load_buhin():
    hako, hyo = {}, []
    for path in sorted(glob.glob(os.path.join(BUHIN, '*.svg'))):
        name = os.path.splitext(os.path.basename(path))[0]
        s = io.open(path, encoding='utf-8').read().strip()
        kb, w, h, katachi, iro = kenmon_buhin(name, s)
        naka = re.sub(r'^<svg[^>]*>', '', s).rsplit('</svg>', 1)[0].strip()
        hako[name] = (w, h, naka)
        hyo.append((name, '%g×%g' % (w, h), kb, katachi, len(iro)))
    return hako, hyo


# ── 絵を動かす入れ物（2026-09-23 依頼）────────────────────
# 人と雲を <g class="…"> で包みます。包むだけで、絵そのものは1本も変えません。
# 動かし方は src/style-hiroba.css の「広場の絵の動き」で決めます。
HADA = '#F6D8B8'          # 顔と手の色。これが入っていれば「人」

# 校庭のトラック（絵の中の3本の白い楕円のうち、真ん中のレーン）。
# 走る子4人は、もともとこの線の上に立っています。だから同じ線を走らせます。
TRACK = (1580.0, 1104.0, 478.0, 212.0)      # 中心x, 中心y, 横半径, 縦半径
TRACK_BYO = 28.0                            # 1周の秒数（2026-09-23 2回目：速すぎたので16→28秒）
# 青い服の2人は、1周したあと校舎の玄関へ入っていきます（2026-09-23 依頼）。
AO       = '#3A6EA5'                        # 青い服。この色を着ている子が入ります
GENKAN   = (2470.0, 604.0)                  # 校舎の玄関（緑の両開き戸の下まんなか。実測）
GENKAN_MICHI = ((2300.0, 1000.0),           # トラックを出てから玄関までの通り道。
                (2480.0, 820.0),            # 掲示板の右がわを通ります
                (2492.0, 700.0))
GENKAN_BYO = 8.0                            # トラックを出てから、入るまでの秒数
# 入れかわりに、黄色の2人が玄関から出てきます（2026-09-23 依頼）。
KI        = '#E8C547'                       # 黄色。出てくる2人の服の色
DERU_BYO  = 8.0                             # 玄関から校庭に出てくるのにかかる秒数
DERU_MA   = 1.6                             # 青が入ってから、黄が出るまでの間
DERU_ZURE = 1.3                             # 2人めが、1人めより遅れて出る秒数
# 玄関の戸（校舎の緑の両開き戸）。絵の中では、この値の四角として描かれています。
TOBIRA    = ('275', '407', '70', '85')      # x, y, 幅, 高さ
TOBIRA_TE = 'M310 407v85M298 447v13M322 447v13'   # まん中の線と、2つの取っ手
TOBIRA_ZEN = 60.0                           # 戸の開け閉めぜんぶの長さ（秒）
# 行人（鉢巻をした学校行事の案内役）は、走路のまんなかに立っていました。
# 子どもが回ると、必ずぶつかります。走路の外（手前）へ下がってもらいます。
GYOJIN  = 'M23 25c5-7'                      # 行人の鉢巻の帯。これで見分けます
GYOJIN_YOKE = (-60.0, 290.0)                # どれだけ動かすか（右へ、下へ）
TOBIRA_MA  = 1.4                            # 開くのにかかる秒数（閉まるのも同じ）
UGOKI_CSS = []                              # 1人ぶんずつの道（build_page が <style> に足す）
# 走る子の絵の「足もと」＝絵の中での位置（実測：translate＋scale×この値）。
# CSS の transform-origin:50% 100%（＝囲みの下まんなか）と同じ点です。
ASHI = (30.03, 82.0)
# 頭の上に「別置き」されていた白い鉢巻の弧。子どもと別の部品なので、
# 子どもが動くと鉢巻だけ取り残されます（2026-09-23 依頼で外しました）。
HACHIMAKI = 'q20-11 42 0'
UGOKI_KATA = (
    ('走っている',     'ug ug--hashiru'),   # はずむ
    ('手を挙げている', 'ug ug--te'),        # 手を上げ下げ
    ('椅子に座っている', 'ug ug--suwaru'),  # 小さくゆれる
)


def hachimaki_kesu(root):
    """子どもと別に置かれた鉢巻の弧を外す。戻り値は外した数。

       絵では、鉢巻が走る子の「上に重ねた別の部品」として置かれています。
       子どもを動かすと鉢巻だけが空中に残るので、動かすなら外すしかありません。"""
    kesu = [n for n in list(root)
            if n.tag.split('}')[-1] == 'path'
            and HACHIMAKI in (n.attrib.get('d') or '')
            and n.attrib.get('stroke') in ('#FFFEF4', '#FCFBF7')]
    for n in kesu:
        root.remove(n)
    return len(kesu)


def mawaru_suji(g):
    """走る子1人ぶんの「トラックのどこから走り出すか」を決める。

       返すのは (--sx, --sy, 出だしの遅れ)。
       --sx --sy は「その子の足もと → トラックの中心」までの差。
       これを足すと、どの子も同じ1本の線の上を回ります（CSSの ug-mawaru）。"""
    m = re.search(r'translate\(([-\d.]+)[ ,]([-\d.]+)\)', g.attrib.get('transform', ''))
    sc = re.search(r'scale\(([\d.]+)\)', g.attrib.get('transform', ''))
    if not m:
        return None
    s_ = float(sc.group(1)) if sc else 1.0
    ashi_x = float(m.group(1)) + s_ * ASHI[0]
    ashi_y = float(m.group(2)) + s_ * ASHI[1]
    cx, cy, rx, ry = TRACK
    # いま立っている場所が、楕円の何度のあたりかを出す（画面のyは下向き）
    kaku = math.degrees(math.atan2((ashi_y - cy) / ry, (ashi_x - cx) / rx))
    # 左回り（θが減る向き）に走らせる。1コマめは、いまの立ち位置とぴったり同じ。
    okure = -TRACK_BYO * (((360.0 - kaku) % 360.0) / 360.0)
    return cx - ashi_x, cy - ashi_y, okure, ashi_x, ashi_y, kaku


def hairu_michi(namae, ashi_x, ashi_y, kaku0):
    """「トラックを1周してから、校舎へ入っていく」1人ぶんの道をCSSにする。

       戻り値は (キーフレームの文, ぜんぶで何秒か)。
       玄関は絵の奥にあるので、近づくほど小さくして、最後に戸の前で消えます。"""
    cx, cy, rx, ry = TRACK
    zen = 360.0 + kaku0                      # 1周まわって、右はし（出口）まで
    hashiru = TRACK_BYO * zen / 360.0
    zenbu = hashiru + GENKAN_BYO
    de = hashiru / zenbu                     # 走っているあいだの割合
    gyo = []
    n = max(24, int(zen / 15.0))             # 15度ごとに1点
    for i in range(n + 1):
        w = i / float(n)
        k = math.radians(kaku0 - zen * w)
        gyo.append('  %.4f%%{translate:%.0fpx %.0fpx}'
                   % (de * 100 * w,
                      cx + rx * math.cos(k) - ashi_x,
                      cy + ry * math.sin(k) - ashi_y))
    michi = list(GENKAN_MICHI) + [GENKAN]
    for j, (mx, my) in enumerate(michi):
        w = (j + 1) / float(len(michi))
        gyo.append('  %.4f%%{translate:%.0fpx %.0fpx;scale:%.2f;opacity:1}'
                   % ((de + (0.96 - de) * w) * 100,
                      mx - ashi_x, my - ashi_y, 1.0 - 0.42 * w))
    gyo.append('  100%%{translate:%.0fpx %.0fpx;scale:.58;opacity:0}'
               % (GENKAN[0] - ashi_x, GENKAN[1] - ashi_y))
    return '@keyframes %s{\n%s\n}\n' % (namae, '\n'.join(gyo)), zenbu


def deru_michi(namae):
    """玄関から校庭へ出てくる道。hairu_michi の逆をたどります。
       戻り値は (キーフレームの文, トラックに着くまでの秒数)。
       足もとは玄関に置くので、translate は玄関からの差になります。"""
    cx, cy, rx, ry = TRACK
    deguchi = (cx + rx, cy)                      # トラックの右はし
    michi = [GENKAN] + list(reversed(GENKAN_MICHI)) + [deguchi]
    gx, gy = GENKAN
    gyo = ['  0%{translate:0px 0px;scale:.58;opacity:0}',
           '  6%{translate:0px 0px;scale:.58;opacity:1}']   # 戸のところで、ふっと現れる
    for j, (mx, my) in enumerate(michi):
        w = j / float(len(michi) - 1)
        gyo.append('  %.4f%%{translate:%.0fpx %.0fpx;scale:%.2f;opacity:1}'
                   % (6 + 94 * w, mx - gx, my - gy, 0.58 + 0.42 * w))
    return '@keyframes %s{\n%s\n}\n' % (namae, '\n'.join(gyo)), DERU_BYO


def tobira_css(aku, shimaru):
    """玄関の戸の開け閉め。aku＝開ききる秒、shimaru＝閉まりきる秒。"""
    p = lambda t: max(0.0, min(100.0, t / TOBIRA_ZEN * 100.0))
    return ('@keyframes ug-tobira{\n'
            '  0%%,%.3f%%{scale:1 1}\n'
            '  %.3f%%,%.3f%%{scale:.08 1}\n'
            '  %.3f%%,100%%{scale:1 1}\n}\n'
            % (p(aku - TOBIRA_MA), p(aku), p(shimaru - TOBIRA_MA), p(shimaru)))


def gyojin_sagaru(root):
    """行人を、走路の外（手前）へ下げる。

       絵では走路のまんなかに立っていて、回る子と必ず重なります（依頼）。
       絵そのものは直さず、置く場所だけをずらします。
       いちばん後ろに置きなおすので、もし近くを通っても、行人が手前に出ます。"""
    ns = '{http://www.w3.org/2000/svg}'
    for node in list(root):
        if node.tag != ns + 'g':
            continue
        moji = ET.tostring(node, encoding='unicode')
        if GYOJIN not in moji or HADA not in moji:
            continue
        naka = node[0] if node.get('class') else node      # 包んである場合は中身
        m = re.search(r'translate\(([-\d.]+)[ ,]([-\d.]+)\)', naka.attrib.get('transform', ''))
        if not m:
            return False
        x, y = float(m.group(1)) + GYOJIN_YOKE[0], float(m.group(2)) + GYOJIN_YOKE[1]
        naka.set('transform', re.sub(r'translate\([-\d., ]+\)',
                                     'translate(%g,%g)' % (x, y),
                                     naka.attrib['transform'], count=1))
        root.remove(node)
        root.append(node)
        return True
    return False


def tobira_wakeru(root):
    """1枚の四角で描かれている玄関の戸を、開けられる「両開き」に組みなおす。

       絵は直しません。同じ形を、奥（暗い中）・左の戸・右の戸の3つに分けて置きかえます。
       見た目は閉じているあいだ、前とまったく同じです。"""
    ns = '{http://www.w3.org/2000/svg}'
    oya_no = dict((c, p) for p in root.iter() for c in p)
    x, y, w, h = (float(v) for v in TOBIRA)
    for node in root.iter():
        if node.tag != ns + 'rect' or node.attrib.get('fill') != '#1F5C3F':
            continue
        if (node.attrib.get('x'), node.attrib.get('y'),
                node.attrib.get('width'), node.attrib.get('height')) != TOBIRA:
            continue
        oya = oya_no.get(node)
        if oya is None:
            continue
        ko = list(oya)
        i = ko.index(node)
        te = None
        for k in ko[i:i + 3]:
            if k.tag == ns + 'path' and k.attrib.get('d') == TOBIRA_TE:
                te = k
                break
        sen = dict(stroke='#1C1C1A', stroke_width='2.5')
        def yon(xx, ww, fill, cls=None, tex=None):
            g = ET.Element(ns + 'g', {'class': cls} if cls else {})
            r = ET.SubElement(g, ns + 'rect', {
                'x': '%g' % xx, 'y': '%g' % y, 'width': '%g' % ww, 'height': '%g' % h,
                'fill': fill, 'stroke': '#1C1C1A', 'stroke-width': '2.5',
                'stroke-linejoin': 'round'})
            if tex:
                ET.SubElement(g, ns + 'path', {
                    'd': tex, 'fill': 'none', 'stroke': '#FFFEF4',
                    'stroke-width': '2.5', 'stroke-linecap': 'round'})
            return g
        matome = ET.Element(ns + 'g')
        matome.append(yon(x, w, '#1C1C1A'))                       # 開けたときに見える、中の暗がり
        matome.append(yon(x, w / 2, '#1F5C3F', 'tobira-h', 'M%g 447v13' % (x + 23)))
        matome.append(yon(x + w / 2, w / 2, '#1F5C3F', 'tobira-m', 'M%g 447v13' % (x + 47)))
        oya.remove(node)
        if te is not None:
            oya.remove(te)
        oya.insert(i, matome)
        return True
    raise Tomeru('校舎の玄関の戸（%s の四角）が絵の中に見あたりません。'
                 '絵を入れかえたときは、build.py の TOBIRA を合わせてください'
                 % ' '.join(TOBIRA))


def deru_futari(root, tane_g, hairu_owari):
    """黄色の2人を、玄関の中から出てくるように置く。

       青い2人が入ったあと、入れかわりに出てきて、そのままトラックを回ります。
       絵には元から居ない2人なので、ここで作ります（走る子の絵を、黄色に着せかえ）。"""
    import copy
    ns = '{http://www.w3.org/2000/svg}'
    cx, cy, rx, ry = TRACK
    m = re.search(r'scale\(([\d.]+)\)', tane_g.attrib.get('transform', ''))
    s_ = float(m.group(1)) if m else 1.0
    gx = GENKAN[0] - s_ * ASHI[0]
    gy = GENKAN[1] - s_ * ASHI[1]
    owari = []
    for i in range(2):
        naka = copy.deepcopy(tane_g)
        naka.set('transform', 'translate(%g,%g) scale(%g)' % (gx, gy, s_))
        for e in naka.iter():
            if e.get('fill') in ('#3A6EA5', '#D2552A') and e.tag == ns + 'path':
                if e.get('fill') == '#3A6EA5' or 'M29 33C22' in (e.get('d') or ''):
                    e.set('fill', KI)          # 服だけ黄色に着せかえる
        ti = naka.find(ns + 'title')
        if ti is not None:
            ti.text = '校舎から出てくる子のイラスト'
        namae = 'ug-deru-%d' % (i + 1)
        css, byo = deru_michi(namae)
        UGOKI_CSS.append(css)
        deru = hairu_owari + DERU_MA + DERU_ZURE * i
        soto = ET.Element(ns + 'g', {
            'class': 'ug ug--hashiru ug--deru ug-p%d' % (i * 2),
            'style': ('--nm:%s;--byo:%.1fs;--sx:%.1fpx;--sy:%.1fpx;'
                      'animation-delay:%.2fs,%.2fs,-%.2fs'
                      % (namae, byo, cx - GENKAN[0], cy - GENKAN[1],
                         deru, deru + byo, .3 * i))})
        soto.append(naka)
        root.append(soto)
        owari.append(deru + byo)
    return owari


def ugoki_ireru(root):
    """人と雲を、動かせる入れ物に入れる。戻り値は包んだ数。

       絵は <defs> の1つを <use> で使い回しています。
       **この中にアニメーションを書いても <use> の側には出ません**（2026-09-22 実測）。
       だから「入れ物」だけを足して、外から CSS で動かします。
       ホームの絵は <use> ではなく、この本物を出すようにしてあります。"""
    ns = '{http://www.w3.org/2000/svg}'
    del UGOKI_CSS[:]
    kazu = 0
    ao_owari = []          # 青い子が、戸の中に消えきる秒
    ao_tane = None         # 走る子の絵。黄色の2人は、これを着せかえて作ります
    for i, node in enumerate(list(root)):
        if node.tag != ns + 'g':
            continue
        ti = node.find(ns + 'title')
        na = (ti.text or '') if ti is not None else ''
        moji = ET.tostring(node, encoding='unicode')
        if '雲' in na:
            cls = 'ukumo'
        elif HADA in moji:
            cls = 'ug ug--tatsu'
            for kotoba, c in UGOKI_KATA:
                if kotoba in na:
                    cls = c
                    break
        else:
            continue
        zokusei = {'class': '%s ug-p%d' % (cls, kazu % 6)}
        if 'ug--hashiru' in cls:
            suji = mawaru_suji(node)
            if suji:
                sx, sy, okure, ashi_x, ashi_y, kaku = suji
                fumu = -.07 * (kazu % 5)     # 足のふみこみを、人ごとにばらす
                if AO in moji:
                    # 青い服の子。1周したら、校舎へ入って出てきません。
                    namae = 'ug-hairu-%d' % (len(UGOKI_CSS) + 1)
                    css, byo = hairu_michi(namae, ashi_x, ashi_y, kaku)
                    UGOKI_CSS.append(css)
                    zokusei['class'] += ' ug--hairu'
                    zokusei['style'] = ('--nm:%s;--byo:%.1fs;animation-delay:0s,%.2fs'
                                        % (namae, byo, fumu))
                    ao_owari.append(byo)
                    ao_tane = node
                else:
                    # 赤い服の子。トラックを回りつづけます。
                    zokusei['style'] = ('--sx:%.1fpx;--sy:%.1fpx;animation-delay:%.2fs,%.2fs'
                                        % (sx, sy, okure, fumu))
        soto = ET.Element(ns + 'g', zokusei)
        soto.append(node)
        root[i] = soto
        kazu += 1

    # 青い2人が入るなら、戸を開けられるように組みなおして、
    # 入れかわりに黄色の2人を出します（順番は 戸が開く → 入る → 出る → 戸が閉まる）。
    if ao_owari and ao_tane is not None:
        tobira_wakeru(root)
        owari = deru_futari(root, ao_tane, max(ao_owari))
        tsuku = min(ao_owari) * 0.96                 # 青が戸の前に着くころ
        shimeru = max(owari) - DERU_BYO + 2.6        # 黄色が出きった少しあと
        UGOKI_CSS.append(tobira_css(tsuku - 0.6, shimeru))
        kazu += 2
    gyojin_sagaru(root)
    return kazu


def load_approved_svg(relative_path, ugokasu=False):
    """採用済みの完成イラストを読み、負の viewBox も <use> 用に正規化する。"""
    path = os.path.join(SRC, 'ill', 'approved', relative_path)
    try:
        root = ET.parse(path).getroot()
        x, y, w, h = (float(v) for v in root.attrib['viewBox'].split())
    except (OSError, ET.ParseError, KeyError, ValueError) as e:
        raise Tomeru('採用イラストを読めません：%s（%s）' % (relative_path, e))
    if w <= 0 or h <= 0:
        raise Tomeru('採用イラストの大きさが不正です：%s' % relative_path)
    # 完成画は旧部品の色・線幅制限とは別。スクリプトや外部参照は入れない。
    allowed = {'svg', 'g', 'path', 'rect', 'circle', 'ellipse', 'line',
               'polyline', 'polygon', 'defs', 'clipPath', 'title', 'text'}
    for node in root.iter():
        if node.tag.split('}')[-1] not in allowed:
            raise Tomeru('採用イラストに使えない要素があります：%s' % relative_path)
        for attr, value in node.attrib.items():
            name = attr.split('}')[-1]
            if name.lower().startswith('on') or name in ('href', 'style'):
                raise Tomeru('採用イラストに外部参照・動作があります：%s' % relative_path)
            if 'url(' in value and not re.fullmatch(r'url\(#[\w-]+\)', value):
                raise Tomeru('採用イラストに外部参照があります：%s' % relative_path)
    # 全面をおおう地の四角に枠線が付いていると、絵の上ふちが
    # 「横に1本の線」になって出ます（2026-09-23 依頼）。線だけ外します。
    for node in list(root):
        if node.tag.split('}')[-1] != 'rect':
            continue
        try:
            rx, ry = float(node.attrib.get('x', 0)), float(node.attrib.get('y', 0))
            rw, rh = float(node.attrib['width']), float(node.attrib['height'])
        except (KeyError, ValueError):
            continue
        if rx <= x and ry <= y and rw >= w and rh >= h and node.attrib.get('stroke'):
            node.set('stroke', 'none')
            node.attrib.pop('stroke-width', None)

    if ugokasu:
        hachimaki_kesu(root)
        ugoki_ireru(root)

    ET.register_namespace('', 'http://www.w3.org/2000/svg')
    body = ''.join(ET.tostring(n, encoding='unicode') for n in root)
    if x or y:
        body = '<g transform="translate(%g %g)">%s</g>' % (-x, -y, body)
    return w, h, body


def load_kyara():
    """キャラクター（学活くん・行人・児童会ちゃん・クラブマン）を読む。
       検問は部品とまったく同じ。画風がずれた1人だけを許すと、4人が別物に見えます。"""
    hako = {}
    for path in sorted(glob.glob(os.path.join(KYARA, '*.svg'))):
        name = os.path.splitext(os.path.basename(path))[0]
        s = io.open(path, encoding='utf-8').read().strip()
        kb, w, h, katachi, iro = kenmon_buhin(name, s, 'src/ill/kyara')
        naka = re.sub(r'^<svg[^>]*>', '', s).rsplit('</svg>', 1)[0].strip()
        hako[name] = (w, h, naka)
    inai = [n for n, na, _, _ in KYARA_MEN if n not in hako]
    if inai:
        raise Tomeru('キャラクターの絵がありません： %s'
                     '（src/ill/kyara/◯◯.svg を置いてください）'
                     % '、'.join('src/ill/kyara/%s.svg' % n for n in inai))
    # 各ポーズは別名で登録する。同じポーズはページ内に1回だけ埋め込まれる。
    for path in sorted(glob.glob(os.path.join(SRC, 'ill', 'approved', 'characters', '*.svg'))):
        name = os.path.splitext(os.path.basename(path))[0]
        hako[name] = load_approved_svg('characters/' + name + '.svg')
    return hako


def kenmon_mark(name, s):
    """しるし1枚ぶんの検問。札に並ぶので、大きさと色がそろっていないと崩れます。"""
    f = 'src/ill/mark/%s.svg' % name
    atama = s[:s.index('>') + 1] if '>' in s else s
    if re.search(r'\b(width|height)\s*=', atama):
        raise Tomeru('%s：<svg> に width / height が付いています。'
                     'CSSで伸縮させるので外してください' % f)
    if 'viewBox="0 0 %d %d"' % (MARK_BOX, MARK_BOX) not in s:
        raise Tomeru('%s：viewBox は "0 0 %d %d" にしてください'
                     '（8つの札で大きさがそろわなくなります）' % (f, MARK_BOX, MARK_BOX))
    if '<title>' not in s:
        raise Tomeru('%s：<title> がありません' % f)
    for warui, riyuu in (('<image', '写真の混入'), ('data:image', '写真の混入'),
                         ('<text', '書体の無い端末で崩れる'), ('<style', '属性で塗る'),
                         ('Gradient', 'グラデーションは使わない'),
                         ('<filter', 'ぼかし・影は使わない')):
        if warui in s:
            raise Tomeru('%s：%s が使われています（%s）' % (f, warui, riyuu))
    warui_id = [i for i in re.findall(r'\sid="([^"]+)"', s) if not i.startswith('ill-')]
    if warui_id:
        raise Tomeru('%s：id は "ill-" で始めてください： %s' % (f, '、'.join(warui_id)))
    soto = sorted(set(c.upper() for c in re.findall(r'#[0-9A-Fa-f]{6}', s))
                  - set(MARK_IRO))
    if soto:
        raise Tomeru('%s：決めた%d色の外の色が使われています： %s'
                     % (f, len(MARK_IRO), '、'.join(soto)))
    kb = len(s.encode('utf-8')) / 1024.0
    if kb > MARK_KB:
        raise Tomeru('%s：%.1fKB あります（上限 %.0fKB）。'
                     'しるしは、線を減らして simple にしてください' % (f, kb, MARK_KB))
    return kb


def load_mark():
    """src/ill/mark/*.svg を読む。戻りは {名前: (幅, 高さ, 中身)}。"""
    hako = {}
    for path in sorted(glob.glob(os.path.join(MARK, '*.svg'))):
        name = os.path.splitext(os.path.basename(path))[0]
        s = io.open(path, encoding='utf-8').read().strip()
        kenmon_mark(name, s)
        naka = re.sub(r'^<svg[^>]*>', '', s).rsplit('</svg>', 1)[0].strip()
        hako[name] = (MARK_BOX, MARK_BOX, naka)
    return hako


MIHON = '''<style>
body{background:#FCFBF7;font-family:"BIZ UDPGothic","Hiragino Sans",sans-serif;margin:0;padding:16px;color:#1C1C1A}
h2{font-size:13px;letter-spacing:.08em;margin:16px 0 6px;font-weight:700}
.sky{background:#A9E1F5;padding:16px 18px 0;display:flex;gap:20px;align-items:flex-end;flex-wrap:wrap}
.c{text-align:center;font-size:10.5px;color:#63625C}
.g{background:#E8C547;padding:0 16px;display:flex;align-items:flex-end;gap:8px;min-height:120px;flex-wrap:wrap}
p{font-size:12px;color:#63625C;margin:6px 0 0}
</style>
<h2>① そろい具合（実寸の2倍。接地線でそろえています）</h2>
<div class="sky">%s</div>
<h2>② 広場に置いたときの大きさ（実寸の0.4倍＝PCで見たとき）</h2>
<div class="g">%s</div>
<p>※ 同じ部品の服の色を振り分けています。置くときに朱・紺・緑・黄へ分けます。</p>
'''


def kaku_mihon(hyo):
    """部品の見本ページを書く。目で見て画風がそろっているかを確かめるため。"""
    import html as _h
    ue, shita = [], []
    for name, wh, kb, katachi, iroN in hyo:
        path = os.path.join(BUHIN, name + '.svg')
        s = io.open(path, encoding='utf-8').read()
        w, h = (float(x) for x in re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', s).groups())
        naka = re.sub(r'^<svg[^>]*>', '', s).rsplit('</svg>', 1)[0]
        ue.append('<div class="c"><svg viewBox="0 0 %g %g" width="%g" height="%g">%s</svg><br>%s<br>%g×%g</div>'
                  % (w, h, w * 2, h * 2, naka, _h.escape(name), w, h))
        for c in ('#D2552A', '#3A6EA5', '#1F5C3F', '#E8C547'):
            shita.append('<svg viewBox="0 0 %g %g" width="%g" height="%g">%s</svg>'
                         % (w, h, w * .4, h * .4, naka.replace('#D2552A', c)))
    io.open(os.path.join(ROOT, '_部品見本.html'), 'w', encoding='utf-8', newline='\n').write(
        MIHON % ('\n'.join(ue), '\n'.join(shita)))


def main_buhin():
    """python3 build.py --buhin … 部品だけを検問して、そろい具合を表にする
       --mihon を足すと、_部品見本.html を書いて目でも確かめられる"""
    try:
        hako, hyo = load_buhin()
    except Tomeru as e:
        print('')
        print('  ✕ 部品が規律を外れています')
        print('     %s' % e)
        print('')
        return 1
    print('')
    if not hyo:
        print('  src/ill/buhin/ に部品がまだ1つもありません。')
        print('')
        return 0
    print('  部品 %d個。線の太さは全部 %s、色は決めた%d色の中だけです。'
          % (len(hyo), SEN, len(HIROBA_IRO)))
    print('     名前               実寸        大きさ  図形  色数')
    zu = 0
    for n, wh, kb, k, i in hyo:
        zu += k
        print('     %-18s %-11s %4.1fKB  %3d   %d' % (n, wh, kb, k, i))
    print('')
    print('  図形の合計 %d個。広場に置くときは <use> で何度も使い回すので、' % zu)
    print('  たとえば「こども」を20回置けば、図形は増やさずに20人になります。')
    if '--mihon' in sys.argv:
        kaku_mihon(hyo)
        print('')
        print('  _部品見本.html を書きました。ブラウザで開くと、')
        print('  実寸の2倍と、広場に置いたときの大きさを並べて見られます。')
    else:
        print('')
        print('  目でも確かめるときは  python3 build.py --buhin --mihon')
    print('')
    return 0


# ══════════════════════════════════════════════════════════
# 2-5. 広場を組む（部品をどこに置くか。座標を決めるのはコードの仕事）
# ══════════════════════════════════════════════════════════

SEN_ZOKUSEI = (' stroke="#1C1C1A" stroke-width="%s" stroke-linejoin="round"'
               ' stroke-linecap="round"' % SEN)

# 服の色。同じ部品を置くときに振り分けると、1つの部品が4人ぶんになる
FUKU = ('#D2552A', '#3A6EA5', '#1F5C3F', '#E8C547')


def hiroba_naka(ill):
    """部品を広場に置く。ill は load_buhin() の戻り（名前 → (幅, 高さ, 中身)）。

    横に4つ。特別活動の4つの内容が、左から順に並びます。
        学級活動 ／ 学校行事 ／ 児童会活動 ／ クラブ活動
    """
    import random
    r = random.Random(31)                 # 毎回おなじ絵になるように種を固定
    o = []

    def oku(name, x, base, fuku=None, ashi=8, kage=0):
        """x＝まんなか、base＝地面に着く高さ。部品は拡大縮小しない。
           kage＝足もとに落とす影の横はば（0なら影なし）。"""
        w, h, naka = ill[name]
        e = ''
        if kage:
            e = ('<ellipse cx="%g" cy="%g" rx="%g" ry="%g" fill="#1C1C1A" opacity=".13"/>'
                 % (x, base + 2, kage, max(3, kage * 0.26)))
        return (e + '<g transform="translate(%g,%g)">%s</g>'
                % (x - w / 2.0, base - (h - ashi),
                   naka.replace('#D2552A', fuku) if fuku else naka))

    def hito(n, x1, x2, y1, y2, kazu, tane=None):
        for _ in range(kazu):
            o.append(oku(r.choice(tane) if tane else n,
                         r.randint(x1, x2), r.randint(y1, y2), r.choice(FUKU), kage=17))

    # ── 地紋（テクスチャ）。ベタ面に「手の跡」を足す ──
    o.append(
        '<defs>'
        '<pattern id="ill-ami" width="22" height="22" patternUnits="userSpaceOnUse">'
        '<circle cx="5" cy="5" r="2.1" fill="#1C1C1A"/>'
        '<circle cx="16" cy="16" r="2.1" fill="#1C1C1A"/>'
        '</pattern>'
        '<pattern id="ill-sen" width="16" height="16" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(38)">'
        '<path d="M0 0V16" stroke="#1C1C1A" stroke-width="2.5"/>'
        '</pattern>'
        '</defs>')

    # ── 空 ──
    o.append('<rect width="%d" height="%d" fill="#A9E1F5"/>' % (HIROBA_W, HIROBA_H))
    # ★この絵の中では動かしません。絵は <defs> に置いて <use> で使い回すので、
    #   中に付けたアニメーションは <use> の側に出ません（2026-09-22に実測）。
    #   動くものは、絵の「上に重ねる入れ物」として hero に置いてあります。
    o.append('<circle cx="2940" cy="140" r="88" fill="#E8C547"%s/>' % SEN_ZOKUSEI)
    for x, y in ((330, 150), (900, 96), (1620, 168), (2280, 110), (2720, 176)):
        o.append(oku('kumo', x, y, ashi=110))

    # 山と住宅は外しました（2026-09-21）。主役は学校なので、外を描くほど散ります。
    # 戻すときは、フェンスより奥に baseline 545／566 で置きます。

    # ── 地面（丘 → 芝 → 校庭） ──
    o.append('<path d="M0 520C400 470 830 516 1310 500S2270 452 3200 498V620H0Z" '
             'fill="#1F5C3F"%s/>' % SEN_ZOKUSEI)
    o.append('<path d="M0 580C450 534 930 592 1490 566S2560 520 3200 570V1200H0Z" '
             'fill="#2FBA68"%s/>' % SEN_ZOKUSEI)

    # 芝と校庭に地紋をかける（うっすら。強いとうるさくなる）
    o.append('<path d="M0 580C450 534 930 592 1490 566S2560 520 3200 570V1200H0Z" '
             'fill="url(#ill-ami)" opacity=".10"/>')

    # ── 木（間隔をばらす。等間隔だと並木になって単調） ──
    x = 40
    while x < HIROBA_W:
        o.append(oku('ki' if r.random() < .55 else 'ki-hoso', x, 610 + r.randint(-12, 12), kage=42))
        x += r.randint(150, 300)

    # ── フェンス（校庭のさかい目。これが「学校の校庭」を決める） ──
    for i in range(6):
        o.append(oku('fence', 300 + i * 600, 660))

    # ── 建物 ──
    o.append(oku('mon', 120, 800, kage=130))
    o.append(oku('taiikukan', 1180, 790, kage=270))
    o.append(oku('kosha', 2120, 800, kage=290))

    # ── 校庭 ──
    o.append('<path d="M0 828C560 786 1200 850 1790 818S2650 776 3200 812V1200H0Z" '
             'fill="#E8C547"%s/>' % SEN_ZOKUSEI)
    o.append('<path d="M0 828C560 786 1200 850 1790 818S2650 776 3200 812V1200H0Z" '
             'fill="url(#ill-sen)" opacity=".07"/>')
    o.append('<path d="M900 1060C900 978 1170 944 1510 944S1780 962 1780 1010" '
             'fill="none" stroke="#FCFBF7" stroke-width="7"/>')

    # ══ ① 学級活動（x 60〜760・切り取りの部屋。下端に接する） ══
    o.append('<path d="M74 946h660a14 14 0 0 1 14 14v240H60V960a14 14 0 0 1 14-14z" '
             'fill="#FCFBF7"%s/>' % SEN_ZOKUSEI)
    o.append(oku('kokuban', 234, 1076))
    o.append(oku('shihai', 454, 1090))
    for i, (xx, n, b) in enumerate(((594, 'ko-suwaru', 1092), (694, 'ko-suwaru', 1092),
                                    (644, 'ko-te', 1184), (534, 'ko-suwaru', 1184))):
        o.append(oku(n, xx, b, FUKU[i % 4]))
    o.append(oku('sensei', 124, 1192))

    # ══ ② 学校行事（x 800〜1700・卒業式と運動会） ══
    for i in range(5):
        o.append(oku('ko-ushiro', 850 + i * 56, 886, FUKU[i % 4], kage=17))
    o.append(oku('hana-arch', 990, 986, kage=140))
    o.append(oku('shosho', 990, 982))
    for xx in (820, 1700):
        o.append('<path d="M%g 806V960" fill="none"%s/>' % (xx, SEN_ZOKUSEI))
    for xx in (1090, 1520):
        o.append(oku('bankokki', xx, 806, ashi=130))
    o.append(oku('nyutaijo', 1280, 1014, kage=150))
    o.append(oku('kago', 1560, 1038, kage=42))
    hito(None, 1180, 1690, 1060, 1185, 9, ('ko-hashiru', 'ko-boushi'))
    o.append(oku('hata', 820, 1180))
    o.append(oku('hata', 1700, 1180))

    # ══ ③ 児童会活動（x 1740〜2400・集会と掲示） ══
    o.append(oku('keijiban', 1840, 930, kage=118))
    o.append(oku('nobori', 2330, 946, kage=22))
    o.append(oku('nobori', 2386, 962, kage=22))
    o.append(oku('maiku', 2110, 968, kage=30))
    o.append(oku('shihai', 2026, 966, kage=66))
    o.append(oku('sensei', 2214, 980, kage=19))
    for i in range(7):
        o.append(oku('ko-ushiro', 1800 + i * 58, 1060, FUKU[i % 4], kage=17))
    for i in range(7):
        o.append(oku('ko-ushiro', 1829 + i * 58, 1104, FUKU[(i + 2) % 4], kage=17))
    for i in range(6):
        o.append(oku('ko-ushiro', 1858 + i * 58, 1150, FUKU[(i + 1) % 4], kage=17))

    # ══ ④ クラブ活動（x 2440〜3180・音楽・図工・科学・運動） ══
    o.append(oku('taiko', 2545, 950, kage=70))
    o.append(oku('ko-tatsu', 2628, 952, '#D2552A', kage=17))
    o.append(oku('easel', 2800, 962, kage=58))
    o.append(oku('ko-tatsu', 2882, 964, '#3A6EA5', kage=17))
    o.append(oku('jikken', 3060, 972, kage=92))
    o.append(oku('ko-te', 2966, 974, '#1F5C3F', kage=17))
    o.append(oku('tetsubo', 2670, 1140, kage=95))
    o.append(oku('ko-hashiru', 2840, 1120, '#E8C547', kage=19))
    o.append(oku('sensei', 3070, 1130, kage=19))
    hito(None, 2460, 3150, 1060, 1185, 5, ('ko-tatsu', 'ko-boushi', 'ko-hashiru'))

    return '\n'.join(o)


def hiroba_svg(ill):
    return ('<svg class="hb" viewBox="0 0 %d %d" preserveAspectRatio="xMidYMid meet" '
            'xmlns="http://www.w3.org/2000/svg">'
            '<title>校庭で学級活動・学校行事・児童会活動・クラブ活動をしている'
            '学校の広場のイラスト</title>%s</svg>'
            % (HIROBA_W, HIROBA_H, hiroba_naka(ill)))



# ══════════════════════════════════════════════════════════
# 2-6. ページの頭の絵（2026-09-22）
#
#   ホームには広場の絵があるのに、そこから飛んだ先の頭には
#   何も無く、名前だけが置いてありました。だから「同じサイトの中だ」
#   という手がかりが、帯しかありません。
#
#   そこで、**同じ部品・同じ9色・同じ線2.5** で、ページごとに
#   遠目の絵を1本ずつ組みます。広場をただ切り出すのではなく、
#   そのページの中身（学級会・集会・板書・困りごと）を描きます。
#
#   ・canvas は 2400×420 の1つだけ。どのページでも帯の高さが同じになります
#   ・部品は拡大も縮小もしません（線の太さがそろわなくなるため）
#   ・絵は <defs> に1つだけ置き、広い窓とスマホ用の窓を <use> で切り出します
#     （2回そのまま書くと、ページが絵2枚ぶん重くなります）
# ══════════════════════════════════════════════════════════

KO_E_W, KO_E_H = 2400, 420

# 地面の線。どのページでも同じ高さにして、頭の帯がそろって見えるようにします
_OKA   = 'M0 140C420 112 900 146 1400 132S2060 104 2400 128V210H0Z'   # 奥の丘
_SHIBA = 'M0 190C440 164 980 204 1520 186S2120 160 2400 182V420H0Z'   # 芝
_NIWA  = 'M0 262C520 238 1140 276 1720 258S2180 236 2400 252V420H0Z'  # 校庭


class KoE:
    """ページの頭の絵に、部品を置く道具。決まりは hiroba_naka の oku と同じ。"""

    def __init__(self, ill, kyara, r):
        self.ill, self.kyara, self.r, self.o = ill, kyara, r, []

    def _hako(self, name):
        return self.ill[name] if name in self.ill else self.kyara[name]

    def oku(self, name, x, base, fuku=None, ashi=8, kage=0):
        w, h, naka = self._hako(name)
        e = ''
        if kage:
            e = ('<ellipse cx="%g" cy="%g" rx="%g" ry="%g" fill="#1C1C1A" opacity=".13"/>'
                 % (x, base + 2, kage, max(3, kage * 0.26)))
        self.o.append(e + '<g transform="translate(%g,%g)">%s</g>'
                      % (x - w / 2.0, base - (h - ashi),
                         naka.replace('#D2552A', fuku) if fuku else naka))

    def nama(self, s):
        self.o.append(s)

    def sora(self, kumo, hi=None, iro='#A9E1F5', hi_iro='#E8C547'):
        """空。iro を変えると時間帯が変わります（夕方は黄 #E8C547）。"""
        self.o.append('<rect width="%d" height="%d" fill="%s"/>' % (KO_E_W, KO_E_H, iro))
        if hi:
            self.o.append('<circle cx="%g" cy="%g" r="54" fill="%s"%s/>'
                          % (hi[0], hi[1], hi_iro, SEN_ZOKUSEI))
        for x, y in kumo:
            self.oku('kumo', x, y, ashi=110)

    def yama(self):
        """奥の山なみ。1200幅の部品を2つならべて、頭だけ出します。
           これが出ると「学校の外／まち」に見えます。"""
        self.oku('yama', 600, -40, ashi=420)
        self.oku('yama', 1800, -52, ashi=420)

    def kabe(self, yuka=340, iro='#E8C547'):
        """屋内。上が壁（地の色）、下が床。空は1ドットも出しません。"""
        self.o.append('<rect width="%d" height="%d" fill="#FCFBF7"/>' % (KO_E_W, KO_E_H))
        self.o.append('<path d="M0 %gH%dV%dH0Z" fill="%s"%s/>'
                      % (yuka, KO_E_W, KO_E_H, iro, SEN_ZOKUSEI))

    def mado(self, x, y, w=330, h=176):
        """窓。外に空が見えます。屋内でも「学校の中」だと分かる目じるし。"""
        self.o.append(
            '<rect x="%g" y="%g" width="%g" height="%g" rx="8" fill="#A9E1F5"%s/>'
            '<path d="M%g %gV%gM%g %gH%g" fill="none"%s/>'
            '<path d="M%g %gH%g" fill="none"%s/>'
            % (x, y, w, h, SEN_ZOKUSEI,
               x + w / 2, y, y + h, x, y + h / 2, x + w, SEN_ZOKUSEI,
               x - 14, y + h + 10, x + w + 14, SEN_ZOKUSEI))

    def kami(self, x, y, n=3, w=74, h=96):
        """壁に貼ってある紙。"""
        for i in range(n):
            self.o.append('<rect x="%g" y="%g" width="%g" height="%g" rx="4" '
                          'fill="#FCFBF7"%s/><path d="M%g %gh%gM%g %gh%g" '
                          'fill="none" stroke="#63625C" stroke-width="2.5" '
                          'stroke-linecap="round"/>'
                          % (x + i * (w + 16), y, w, h, SEN_ZOKUSEI,
                             x + i * (w + 16) + 14, y + 30, w - 28,
                             x + i * (w + 16) + 14, y + 52, w - 28))

    def jimen(self, niwa=True):
        self.o.append('<path d="%s" fill="#1F5C3F"%s/>' % (_OKA, SEN_ZOKUSEI))
        self.o.append('<path d="%s" fill="#2FBA68"%s/>' % (_SHIBA, SEN_ZOKUSEI))
        if niwa:
            self.o.append('<path d="%s" fill="#E8C547"%s/>' % (_NIWA, SEN_ZOKUSEI))

    def ki(self, xs, base=250):
        for i, x in enumerate(xs):
            self.oku('ki' if i % 2 == 0 else 'ki-hoso', x,
                     base + self.r.randint(-10, 10), kage=38)

    def fuki(self, x, y, w, h, muki=1):
        """まるい吹き出し。しっぽは下向き（muki＝1で右下、-1で左下）。
           中は「…」の3つの点。言葉を入れないので、どの困りごとにも合います。"""
        self.o.append(
            '<rect x="%g" y="%g" width="%g" height="%g" rx="%g" fill="#FCFBF7"%s/>'
            '<path d="M%g %gl%g 26 %g-6z" fill="#FCFBF7"%s/>'
            '<circle cx="%g" cy="%g" r="7" fill="#1C1C1A"/>'
            '<circle cx="%g" cy="%g" r="7" fill="#1C1C1A"/>'
            '<circle cx="%g" cy="%g" r="7" fill="#1C1C1A"/>'
            % (x, y, w, h, h / 2.4, SEN_ZOKUSEI,
               x + w / 2 - 12 * muki, y + h, 14 * muki, -26 * muki, SEN_ZOKUSEI,
               x + w / 2 - 30, y + h / 2, x + w / 2, y + h / 2, x + w / 2 + 30, y + h / 2))


# ══ 場所を、ページごとに変える（2026-09-22 夜）═══════════
#   はじめ5枚とも「校庭」で描きました。そろってはいるのですが、
#   ページを移っても同じ景色なので、飛んだ気がしませんでした。
#   そこで **場所そのものを変えます**。
#       特活とは・4つの内容 … 山のふもとの校庭（いちばん引いた眺め）
#       学ぶ・実践         … 教室の中（空を1ドットも出さない）
#       ニュース・研究会    … まち（山と家。学校の外＝各地）
#       板書               … ろうか（窓がならぶ。黒板が壁ぎわに立つ）
#       困りごと           … 夕方の校門前（空が黄。帰りぎわ）
#   ★地面の線（丘・芝・校庭）は、外を描く3枚だけで使い回します。
#     屋内の2枚は kabe() で、床と壁にします。
# ══════════════════════════════════════════════════════════

# ══ ① 知る（特活とは・4つの内容）══════════════════════════
#   場所 … 山のふもとの校庭。5枚のうち、いちばん引いた眺めです。
#   4人のキャラクターが、それぞれの持ち場に立っています。
def _e_shiru(k):
    k.sora(((250, 58), (1180, 38), (2010, 70)), hi=(1560, 56))
    k.yama()
    k.jimen()
    k.ki((70, 1350, 2350))
    k.oku('kokuban', 360, 398)                      # 学級活動
    k.oku('gakkatsu', 556, 404, kage=24)
    k.oku('bankokki', 940, 196, ashi=130)           # 学校行事
    k.oku('nyutaijo', 940, 406, kage=132)
    k.oku('gyoji', 1160, 410, kage=24)
    k.oku('keijiban', 1540, 402, kage=96)           # 児童会活動
    k.oku('jidokai', 1724, 408, kage=24)
    k.oku('taiko', 2040, 406, kage=64)              # クラブ活動
    k.oku('club', 2186, 412, kage=24)


# ══ ② 学ぶ（学ぶ・実践）══════════════════════════════════
#   場所 … 教室の中。空は窓の中にしか出しません。
#   黒板が奥のかべ、子どもは左右にわかれて向かい合う（コの字）。
def _e_manabu(k):
    k.kabe(yuka=236)
    k.mado(110, 40, 350, 176)
    k.mado(1990, 40, 340, 176)
    k.kami(1560, 54, 3)
    k.nama('<path d="M0 320H%d" fill="none" stroke="#FCFBF7" stroke-width="5"/>'
           % KO_E_W)
    k.oku('kokuban', 1100, 392)
    k.oku('shihai', 1420, 406)
    # 黒板を見ている後ろ姿。黒板（930〜1270）には重ねません
    for i, x in enumerate((700, 792, 1480, 1572)):
        k.oku('ko-ushiro', x, 368, FUKU[i % 4])
    k.oku('ko-te', 560, 414, '#D2552A')
    for i, x in enumerate((670, 762, 854)):
        k.oku('ko-suwaru', x, 414, FUKU[i % 4])
    for i, x in enumerate((1640, 1732, 1824)):
        k.oku('ko-suwaru', x, 414, FUKU[(i + 2) % 4])
    k.oku('sensei', 1990, 414)


# ══ ③ 集まる（ニュース・日本の研究会）════════════════════
#   場所 … まち。山なみと家がならびます（＝学校の外、各地）。
#   2026-09-22 に2回 作りなおしました。
#     1回め「マイクの前に子どもが整列」→ それは児童会活動の絵でした
#     2回め 校庭のまま → 5枚とも同じ場所で、飛んだ気がしませんでした
#   このページに載っているのは
#       ・ニュース … 外から届いた知らせ
#       ・日本の研究会 … 各地で、先生が集まって研究している
#   の2つなので、絵も「知らせの掲示板」と「各地ののぼり」に分けます。
#   ★子どもを整列させない（集会＝児童会活動に見える）
#   ★のぼりの下に立つのは先生だけ（研究会は大人が集まる場なので）
#   ★家と木で3つのかたまりを仕切る（同じ町ではなく「各地」に見せる）
def _e_atsumaru(k):
    k.sora(((520, 44), (1880, 38)), hi=(1300, 52))
    k.yama()
    k.jimen(niwa=False)
    for x, base in ((190, 248), (1230, 242), (2300, 252)):
        k.oku('ie', x, base, kage=96)
    k.ki((660, 1760))
    k.nama('<path d="M0 330C520 312 1140 346 1720 328S2180 312 2400 322V420H0Z" '
           'fill="#FCFBF7"%s/>' % SEN_ZOKUSEI)          # まちの道
    k.nama('<path d="M0 376C520 358 1140 392 1720 374S2180 358 2400 368" '
           'fill="none" stroke="#E8C547" stroke-width="5"/>')

    # ── 左：ニュース。知らせが3枚 貼られた掲示板を、子どもが見ている ──
    k.oku('keijiban', 330, 400, kage=96)
    k.oku('ko-ushiro', 215, 414, FUKU[0], kage=15)
    k.oku('ko-ushiro', 440, 416, FUKU[1], kage=15)

    # ── 右：日本の研究会。のぼりの下に、先生のかたまりが3つ ──
    for nobori, sensei in (
            ((( 900, 386, '#D2552A'), ( 956, 394, '#E8C547')),
             ((1030, 408), (1082, 412))),
            (((1500, 390, '#3A6EA5'), (1556, 398, '#D2552A')),
             ((1630, 410), (1682, 414), (1734, 408))),
            (((2010, 398, '#E8C547'), (2066, 406, '#3A6EA5')),
             ((2140, 412), (2192, 416)))):
        for x, base, iro in nobori:
            k.oku('nobori', x, base, iro, kage=20)
        for x, base in sensei:
            k.oku('sensei', x, base, kage=17)


# ══ ④ 板書 ═══════════════════════════════════════════════
#   場所 … ろうか。窓がならび、黒板が壁ぎわに立てかけてあります。
#   「送られた板書が溜まっていく」ところなので、教室（学ぶ）ではなく、
#   通りすがりに見る場所にしました。
def _e_bansho(k):
    k.kabe(yuka=330)
    for x in (700, 1390, 2080):                     # 窓は黒板と黒板のあいだ
        k.mado(x, 44, 250, 140)
    k.nama('<path d="M0 288H%d V330H0Z" fill="#3A6EA5"%s/>' % (KO_E_W, SEN_ZOKUSEI))
    k.nama('<path d="M0 378H%d" fill="none" stroke="#FCFBF7" stroke-width="5"/>'
           % KO_E_W)
    for x in (390, 1080, 1770):
        k.oku('kokuban', x, 380)
    for i, (x, n) in enumerate(((160, 'sensei'), (640, 'ko-ushiro'), (830, 'ko-te'),
                                (1330, 'ko-ushiro'), (1520, 'ko-ushiro'),
                                (2020, 'ko-te'), (2230, 'ko-ushiro'))):
        k.oku(n, x, 410, None if n == 'sensei' else FUKU[i % 4])


# ══ ⑤ 困りごと ═══════════════════════════════════════════
#   場所 … 夕方の校門前。空だけ黄にして、帰りぎわにしました。
#   「授業中に手を挙げる」のではなく「帰りぎわに、ちょっと聞きたい」。
def _e_komari(k):
    k.sora(((420, 62), (1960, 48)), hi=(1560, 128), iro='#E8C547', hi_iro='#D2552A')
    k.jimen(niwa=False)     # 校庭（黄）は敷きません。空と同じ色で縞に見えるため
    k.ki((120, 2320))
    k.oku('mon', 640, 372, kage=118)
    for x, muki, kumi in ((260, 1, 'te'), (900, -1, 'futari'),
                          (1500, 1, 'te'), (2060, -1, 'futari')):
        k.fuki(x, 186 if muki > 0 else 200, 196, 92, muki)
        if kumi == 'te':
            k.oku('ko-te', x + 56, 404, '#D2552A', kage=22)
            k.oku('sensei', x + 152, 406, kage=24)
        else:
            k.oku('ko-tatsu', x + 58, 402, '#3A6EA5', kage=22)
            k.oku('ko-te', x + 138, 404, '#E8C547', kage=22)


# （ファイル名, 絵を組む関数, 絵の説明, スマホ用の窓）
#   窓は「その絵でいちばん見せたい所」を 880幅で切り出します。
# （絵を組む関数, 絵の説明, スマホ用の窓, 屋内かどうか）
#   ★屋内の絵は、頭の地を空色ではなく壁の色にします。そうしないと
#     水色の帯のすぐ下に白い壁が来て、絵が貼り紙に見えます（実機で確認）。
KO_E = {
    'shiru.html':    (_e_shiru,    '山のふもとの校庭。黒板・入退場門と万国旗・掲示板・'
                                   'たいこと、4つの内容のキャラクター',
                                   '480 0 880 420', False),
    'manabu.html':   (_e_manabu,   '黒板を囲んで学級会をしている教室の中',
                                   '400 0 880 420', True),
    'atsumaru.html': (_e_atsumaru, '山と家のならぶまち。知らせが貼られた掲示板と、'
                                   'のぼり旗の下で集まって話している先生たち',
                                   '160 0 880 420', False),
    'bansho.html':   (_e_bansho,   '窓のならぶろうかに、黒板が3枚 立ててある',
                                   '820 0 880 420', True),
    'komari.html':   (_e_komari,   '夕方の校門前で話している、こどもと先生。'
                                   '頭の上に吹き出し', '260 0 880 420', False),
}


def ko_e_naka(f, ill, kyara):
    """ページの頭の絵の中身。種は固定（毎回おなじ絵になります）。"""
    import random
    k = KoE(ill, kyara, random.Random(7))
    KO_E[f][0](k)
    return ''.join(k.o)


# 本体の各タブの頭に置く「帯」。広場のどこを切り出すか（x y 幅 高さ）。どれも 5:1
OBI = {
    'home':   ('0 600 3200 640',   '校庭で特別活動をしている学校の広場'),
    'news':   ('1600 680 1500 300', '校舎と児童会の集まり'),
    'manabu': ('30 930 1000 200',  '学級会。黒板の真ん中に提案理由の紙がある'),
    'hiroba': ('1740 940 1000 200', '児童会の集会と掲示板'),
    'my':     ('2440 940 740 148', 'クラブ活動。音楽・図工・科学'),
}


def build_obi(ill):
    """広場を1回だけ埋めこみ、各タブは <use> で別の場所を切り出して見せる。"""
    tane = ('<svg class="hb-tane" aria-hidden="true" focusable="false" '
            'width="0" height="0"><defs><g id="ill-hiroba">%s</g></defs></svg>'
            % hiroba_naka(ill))
    obi = {}
    for tab, (win, setsumei) in OBI.items():
        obi[tab] = ('<div class="obi"><svg viewBox="%s" role="img" '
                    'aria-label="%s のイラスト"><use href="#ill-hiroba"/></svg></div>'
                    % (win, setsumei))
    return tane, obi


# ══════════════════════════════════════════════════════════
# 3. 組み立て（本体 index.html と、簡素版）
# ══════════════════════════════════════════════════════════

# 簡素版は色を使わない（墨1色）。
# 「赤は／緑は」と色で説明している文だけ、印の形での説明に言いかえる。
# ここで直すのは出力だけ。src/body.html は触らない。
IIKAE_SIMPLE = [
    ('赤は研究会の当日、緑は申込の締切日です。',
     '黒くぬった印は申込の締切日、白ぬきの印は研究会の当日です。'),
    ('الأحمر: يوم انعقاد اللقاء / الأخضر: آخر موعد للتسجيل',
     'المربّع الأسود: آخر موعد للتسجيل / المربّع الأبيض: يوم انعقاد اللقاء'),
]


def build(css=CSS, out_name='公開用/index.html'):
    _GOUKEI.clear()
    kiji, tobashita = load_news()
    goods = load_goods()
    jissen, tobashita_j = load_jissen(goods)
    tobashita = tobashita + tobashita_j

    body = rd('src/body.html')
    for mark, html in (('    <!--BUILD:NEWS_HOME-->',   build_home_rows(kiji)),
                       ('  <!--BUILD:NEWS-->',          build_articles(kiji)),
                       ('    <!--BUILD:JISSEN_HOME-->', build_jissen_home(jissen)),
                       ('  <!--BUILD:JISSEN-->',        build_jissen(jissen, goods)),
                       ('    <!--BUILD:GOODS-->',       build_goods(goods))):
        if mark not in body:
            raise Tomeru('src/body.html に目じるし %s がありません' % mark.strip())
        body = body.replace(mark, html)

    if css == CSS_S:
        for mae, ato in IIKAE_SIMPLE:
            if mae not in body:
                raise Tomeru('簡素版の言いかえが当たりません（body.html が変わった？）： %s' % mae[:24])
            body = body.replace(mae, ato)

    # 外のURL（フォームなど）は LINKS から差しこむ。置きかえ残りがあれば止める
    for k, v in LINKS.items():
        body = body.replace('{{%s}}' % k, v)
    nokori = re.findall(r'\{\{([A-Z_]+)\}\}', body)
    if nokori:
        raise Tomeru('src/body.html に、LINKS に無い目じるしがあります： %s' % '、'.join(sorted(set(nokori))))

    html = '\n'.join([
        '<!DOCTYPE html>', '<html lang="ja" dir="ltr" class="no-js">', '<head>',
        rd('src/head.html'),
        '<style>', rd(css), '</style>',
        '<script>',
        '/* ══ storage.js を取りこみ（保存はここだけ。差しかえるときはこのブロックごと） ══ */',
        rd('src/storage.js'), '</script>',
        '<script>', rd('src/boot.js'), '</script>',
        '</head>', '<body>', body, '',
        '<script>', rd('src/app.js'), '</script>',
        '</body>', '</html>',
    ]) + '\n'
    ngword_check(html, out_name)
    return html, kiji, tobashita, jissen, goods


def tenken(html):
    """止めるほどではないけれど、目には入れておきたいこと。"""
    warn = []
    for m in re.finditer(r'<p class="sum"[^>]*>(.*?)</p>', html, re.S):
        t = re.sub(r'<[^>]+>', '', m.group(1))
        if len(t) > 220:
            warn.append('要約が %d字 あります（長いと読まれません）： %s…' % (len(t), t[:24]))
    nuke = [u for u in re.findall(r'href="(https?://[^"]+)"', html)
            if u.startswith('http://') and 'tosho-tokkatsu' not in u]
    kb = len(html.encode('utf-8')) / 1024.0
    if kb > 3000:
        warn.append('%.0fKB あります。配るには重いかもしれません' % kb)
    return warn


# ══════════════════════════════════════════════════════════
# 3-2. 研究会のこよみ（src/app.js の EVENTS を1つの出どころにする）
# ══════════════════════════════════════════════════════════

KOYOMI_TSUKI_MAX = 4      # こよみに出す月の数（今月から）
KEN_UE_N = 3              # こよみの右の一覧に、近いものから何件出しておくか（のこりはふたの中）
YOUBI = ('日', '月', '火', '水', '木', '金', '土')

# 会の名前から研究部を見わける。見わけた人が、こよみの丸と一覧の顔になる
KEN_KAO = (('行事', 'gyoji'), ('学活', 'gakkatsu'), ('学級', 'gakkatsu'),
           ('クラブ', 'club'), ('児童会', 'jidokai'))


def load_kenkyukai(kyou=None):
    """新版はJSを使わないので、ビルド時に読んで日付順に並べる。
       app.js の EVENTS を1つの出どころにして、二重管理にしない。"""
    src = rd('src/app.js')
    m = re.search(r'var EVENTS = \[(.*?)\n  \];', src, re.S)
    if not m:
        raise Tomeru('src/app.js に EVENTS の配列が見あたりません（カレンダーが作れません）')
    kyou = kyou or kyou_jst()
    out = []
    for blk in re.findall(r'\{(.*?)\}', m.group(1), re.S):
        def hiku(k):
            mm = re.search(r"\b%s\s*:\s*'([^']*)'" % k, blk)
            return mm.group(1) if mm else ''
        mm = re.search(r'days\s*:\s*\[([^\]]*)\]', blk)
        days = re.findall(r"'(\d{4}-\d{2}-\d{2})'", mm.group(1)) if mm else []
        shimekiri = hiku('deadline')
        for hi, shurui in [(d, '当日') for d in days] + ([(shimekiri, '申込〆切')] if shimekiri else []):
            try:
                d = datetime.date(*(int(x) for x in hi.split('-')))
            except Exception:
                continue
            nokori = (d - kyou).days
            if nokori < 0:
                continue
            out.append({'d': d, 'nokori': nokori, 'shurui': shurui,
                        'ja': hiku('s_ja') or hiku('ja'), 'org': hiku('org_ja'),
                        'basho': hiku('place_ja'), 'url': hiku('url'),
                        # 2026-09-21：ここから下は、押したときページの中で出すぶん。
                        #   app.js には前から入っていたのに、1つも画面に出していませんでした。
                        'seishiki': hiku('ja'), 'venue': hiku('venue'),
                        'naka': hiku('about_ja'), 'moushikomi': hiku('apply_ja')})
    out.sort(key=lambda a: a['d'])
    # ★ 原則③（単なるリンク集にしない）の検問。
    #   名前と日付だけ並べて外へ投げるのは、このサイトではやらないと決めています。
    for a in out:
        if len(a['naka'].strip()) < 10:
            raise Tomeru('研究会「%s」に about_ja（中身の1行）がありません。'
                         '名前とURLだけ並べるのは、このサイトではやらないと'
                         '決めています（src/app.js の EVENTS）' % a['ja'])

    # ★ここから下は、サイトから送られたぶん（2026-09-22）。
    #   上の検問（raise）は通しません。送られた1件が変でも、
    #   **サイト全体が出なくなってはいけない**ためです。飛ばして、理由を控えます。
    okurareta, tobashita = load_nittei(kyou)
    del NITTEI_TOBASHITA[:]
    NITTEI_TOBASHITA.extend(tobashita)
    out.extend(okurareta)
    out.sort(key=lambda a: (a['d'], a['ja']))
    return out


# ══════════════════════════════════════════════════════════
# 3-2の2. サイトから送られた研究日程（2026-09-22）
# ══════════════════════════════════════════════════════════
#   これまで研究日程の出どころは src/app.js の EVENTS だけでした。
#   手で書き足すしかないので、知っている人が居ても、その人からは載せられません。
#   サイトの中の入力欄（#nittei）から送れるようにして、送られたぶんは
#   src/nittei/*.md で受けます。app.js のほうは、これまでどおり手で書くぶんです。
#   （二重管理に見えますが、出どころが「こちらの調べ」と「人からの知らせ」で
#     別ものなので、混ぜないほうが、あとで直すときに分かります）
#
#   ★この節では Tomeru を投げません。1件のせいでサイトが止まらないためです。

NITTEI_MOJI_MAX = 300     # 中身（何をやる会か、の説明）の上限
NITTEI_HI_MAX   = 2       # 1件で受ける「当日」の数（2日開催まで）
NITTEI_TOBASHITA = []     # 飛ばした理由。ビルドの終わりに出します


def _nittei_hi(s):
    """2026-10-02 → date。読めなければ None（止めません）。"""
    try:
        return datetime.date(*(int(x) for x in str(s).strip().split('-')))
    except Exception:
        return None


def load_nittei(kyou=None):
    """src/nittei/*.md を読む。戻りは load_kenkyukai() と同じ形の並びと、
       飛ばした理由の並び。日が過ぎたものは、こよみに出しません。"""
    kyou = kyou or kyou_jst()
    out, tobashita = [], []
    for path in sorted(glob.glob(os.path.join(NITTEI, '*.md'))):
        f = os.path.basename(path)
        if f.startswith('_'):
            continue                      # _つかいかた.md のような控えは読みません
        try:
            fm = parse_md(path)
        except Tomeru as e:
            tobashita.append('%s … %s' % (f, e))
            continue
        if (fm.get('share') or '').strip().lower() != 'true':
            tobashita.append('%s … share: true が無いので出しません' % f)
            continue

        na   = (fm.get('title') or '').strip()
        naka = fm['summary'].strip()
        if not na:
            tobashita.append('%s … title（会の名前）がありません' % f)
            continue
        # 原則③（単なるリンク集にしない）。ここでも同じ線で見ます。
        # ただし止めずに、この1件だけ出しません。
        if len(naka) < 10:
            tobashita.append('%s … 中身の1行がありません（10字以上）' % f)
            continue
        w = ngword_aru(' '.join((na, naka, fm.get('org', ''),
                                 fm.get('venue', ''), fm.get('place', ''),
                                 fm.get('by', ''))))
        if w:
            tobashita.append('%s … 出してはいけない語「%s」が入っています' % (f, w))
            continue

        hiduke = [x for x in (_nittei_hi(d) for d in
                              (fm.get('days') or '').split('|')) if x][:NITTEI_HI_MAX]
        if not hiduke:
            tobashita.append('%s … days が 2026-10-02 の形ではありません' % f)
            continue
        shime = _nittei_hi(fm.get('deadline', ''))

        # 外へ出る道は、http(s) だけ通します（javascript: などを入れさせない）
        url = (fm.get('url') or '').strip()
        if url and not (url.startswith('https://') or url.startswith('http://')):
            url = ''

        deta = 0
        for d, shurui in ([(x, '当日') for x in hiduke]
                          + ([(shime, '申込〆切')] if shime else [])):
            if (d - kyou).days < 0:
                continue
            deta += 1
            out.append({'d': d, 'nokori': (d - kyou).days, 'shurui': shurui,
                        'ja': na, 'seishiki': na,
                        'org':   (fm.get('org') or '').strip(),
                        'basho': (fm.get('place') or '').strip(),
                        'venue': (fm.get('venue') or '').strip(),
                        'naka':  naka[:NITTEI_MOJI_MAX],
                        'moushikomi': (fm.get('apply') or '').strip(),
                        'url': url,
                        # ここから下は、送られたものだけが持ちます
                        'okuri': True, 'by': (fm.get('by') or '').strip(),
                        'slug': slug_of(path)})
        if not deta:
            tobashita.append('%s … 日が過ぎているので、こよみには出しません' % f)
    return out, tobashita


def ken_bu(a):
    """会の名前から、どの研究部かを見わける（顔の絵と、こよみの色の両方で使う）。"""
    moji = (a.get('ja') or '') + (a.get('org') or '')
    for kotoba, kao in KEN_KAO:
        if kotoba in moji:
            return kao
    return 'hata'      # 当たらなければ旗


def ken_kao(a, kyara, buhin):
    """丸に入れるので顔だけを切り出す。"""
    kao = ken_bu(a)
    if kao != 'hata':
        return 'ill-k-' + kao, kao, '8 0 80 60'          # 顔（髪とおさげが入る幅）
    w, h, _ = buhin['hata']
    return 'ill-b-hata', 'hata', '0 0 %g %g' % (w, h)


# 2026-09-21：前は、押すといきなり外のサイトが開いていました。
#   いまは1回めで「ここで」中身がひらき、申し込みたい人だけが外へ出ます。
#   （原則「押した先で見た目を変えない」の、最後まで残っていたところ）
KEN_T = """      <details class="gyo ken{tsugi}" id="ken-{ban}">
        <summary>
        <span class="hizuke"><b aria-hidden="true">{md}</b><i aria-hidden="true">{youbi}</i>\
<span class="kakure">{ja_date}（{youbi}）</span></span>
        <span class="kao kao--{kao}"><svg viewBox="{win}" aria-hidden="true" focusable="false"><use href="#{ref}"/></svg></span>
        <span class="t">{ja}<span class="sub">{shurui}{basho}</span></span>
        <span class="nokori"><b>{nokori}</b>日後</span>
        <span class="pm" aria-hidden="true"></span>
        </summary>
        <div class="ken-naka">
{gyou}{soto}        </div>
      </details>"""

KEN_GYOU = """          <div class="ken-g"><dt>{na}</dt><dd>{atai}</dd></div>
"""
KEN_SOTO = """          <p class="ken-soto"><a class="btn btn--soto" href="{url}" target="_blank" rel="noopener noreferrer">{ji}<span class="btn-ya">↗</span></a></p>
"""


# ══ よこにスライドする器（2026-09-21）════════════════════
#   「縦にめっちゃ長い」という声から、こよみを月ごとの横スライドにしました。
#   そのあと「各々の下の項目も横スライドできるように」と言われたので、
#   こよみと一覧で同じ器を使い回します。スワイプでも ‹ › でも動きます。
#   JSは scrollBy を呼ぶだけ。何も送信しません。

def yoko_ban(gyo, yomi, mae='前を見る', tsugi='次を見る', ji=6, haba='', cls=''):
    """gyo … 中に並べるHTMLの並び。ji … 字下げの深さ。
       cls … 器そのものに足すクラス（中の札の見た目は、ここに付いています）"""
    a = ' ' * ji
    return (a + '<div class="yoko"%s>\n' % (' style="--yoko-w:%s"' % haba if haba else '')
            + a + '  <div class="yoko-ue">\n'
            + a + '    <p class="yoko-hint">よこにスライド</p>\n'
            + a + '    <p class="yoko-okuri">\n'
            + a + '      <button type="button" class="yoko-b" data-yoko="-1"'
                  ' aria-label="%s">‹</button>\n' % esc_html(mae)
            + a + '      <button type="button" class="yoko-b" data-yoko="1"'
                  ' aria-label="%s">›</button>\n' % esc_html(tsugi)
            + a + '    </p>\n'
            + a + '  </div>\n'
            + a + '  <div class="yoko-ban%s" tabindex="0" role="group" aria-label="%s">\n'
                  % ((' ' + cls) if cls else '', esc_html(yomi))
            + '\n'.join(gyo) + '\n'
            + a + '  </div>\n'
            + a + '</div>')


def build_koyomi(ken, kyou):
    """ken は load_kenkyukai() の戻り（日付順）。kyou は今日。"""
    hi = {}
    for i, a in enumerate(ken):
        hi.setdefault(a['d'], []).append((i, a))

    # 出す月 … 今月から、予定のある最後の月まで（上限 KOYOMI_TSUKI_MAX）
    tsuki = []
    y, m = kyou.year, kyou.month
    owari = max(hi) if hi else kyou
    while len(tsuki) < KOYOMI_TSUKI_MAX:
        tsuki.append((y, m))
        if (y, m) >= (owari.year, owari.month):
            break
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)

    out = []
    for y, m in tsuki:
        hajime, nissu = calendar.monthrange(y, m)      # hajime は月曜=0
        zure = (hajime + 1) % 7                        # 日曜はじまりに直す
        masu = []
        for _ in range(zure):
            masu.append('<td class="hi-soto"></td>')
        for d in range(1, nissu + 1):
            kono = datetime.date(y, m, d)
            youbi = (calendar.weekday(y, m, d) + 1) % 7
            cls = ['hi']
            if youbi == 0:
                cls.append('hi--nichi')
            if youbi == 6:
                cls.append('hi--do')
            if kono == kyou:
                cls.append('hi--kyou')
            koto = hi.get(kono)
            if not koto:
                if kono < kyou:
                    cls.append('hi--mae')
                masu.append('<td class="%s"><span>%d</span></td>' % (' '.join(cls), d))
                continue
            i0, a0 = koto[0]
            yomi = '、'.join('%s（%s）' % (a['ja'], a['shurui']) for _, a in koto)
            fuda = ('<i class="hi-kazu">%d</i>' % len(koto)) if len(koto) > 1 else ''
            masu.append('<td class="%s hi--aru"><a class="maru maru--%s%s" href="#ken-%d" '
                        'aria-label="%d月%d日 %s">%d%s</a></td>'
                        % (' '.join(cls), ken_bu(a0),
                           ' maru--shime' if a0['shurui'] != '当日' else '',
                           i0, m, d, attr(yomi), d, fuda))
        while len(masu) % 7:
            masu.append('<td class="hi-soto"></td>')
        gyo = ['        <tr>%s</tr>' % ''.join(masu[i:i + 7]) for i in range(0, len(masu), 7)]
        out.append(
            '      <div class="tsuki">\n'
            '        <p class="tsuki-na">%d年<b>%d月</b></p>\n'
            '        <table class="masu"><caption class="kakure">%d年%d月の研究会</caption>\n'
            '        <thead><tr>%s</tr></thead>\n'
            '        <tbody>\n%s\n        </tbody></table>\n'
            '      </div>'
            % (y, m, y, m,
               ''.join('<th scope="col">%s</th>' % w for w in YOUBI),
               '\n'.join(gyo)))

    hanrei = (
        '      <ul class="hanrei">\n'
        '        <li><i class="maru maru--gakkatsu">1</i>学活部</li>\n'
        '        <li><i class="maru maru--gyoji">2</i>行事部</li>\n'
        '        <li><i class="maru maru--jidokai">3</i>児童会部</li>\n'
        '        <li><i class="maru maru--club">4</i>クラブ部</li>\n'
        '        <li><i class="maru maru--shime">5</i>申込〆切（点線）</li>\n'
        '      </ul>\n'
        '      <p class="koyomi-chu">色のついた日を押すと、下の一覧のその1件にとびます。</p>')
    # 2026-09-21：月を縦に積むと、それだけで画面何枚ぶんにもなりました。
    #   よこに並べて、1月ずつスライドさせます（スワイプでも、‹ › でも動きます）。
    naka = yoko_ban(out, '研究会のこよみ。%dか月ぶんを、よこにスライドして見ます' % len(out),
                    mae='前の月を見る', tsugi='次の月を見る', ji=6)
    return '    <div class="koyomi">\n' + naka + '\n' + hanrei + '\n    </div>'


def ken_moto(a):
    """送られた日程だけ、そう書きます。こちらで調べたぶんは空（＝行が出ません）。"""
    if not a.get('okuri'):
        return ''
    return ('サイトから知らせてもらった日程です（提供：%s）。念のため、'
            'お出かけの前に主催の案内をご確認ください。'
            % (a.get('by') or '送ってくださった先生'))


def build_kenkyukai(ken, kyara, buhin, kyou=None):
    kyou = kyou or kyou_jst()

    def gyo(a, i):
        ref, kao, win = ken_kao(a, kyara, buhin)
        d = a['d']
        youbi = YOUBI[(calendar.weekday(d.year, d.month, d.day) + 1) % 7]
        basho = '　'.join(x for x in (a['venue'], a['basho']) if x)
        # 押したとき、ページの中に出すぶん。空の行は出しません
        gyou = ''.join(
            KEN_GYOU.format(na=na, atai=esc_html(atai))
            for na, atai in (('日にち', '%s（%s）・%s' % (ja_md(d), youbi, a['shurui'])),
                             ('会　場', basho),
                             ('中　身', a['naka']),
                             ('主　催', a['org']),
                             ('申込み', a['moushikomi']),
                             # 送られたものは、そう書きます（2026-09-22）。
                             #   こちらで調べたぶんと、人から知らせてもらったぶんは
                             #   確かさが違います。黙って混ぜません。
                             ('出どころ', ken_moto(a)))
            if atai)
        soto = (KEN_SOTO.format(url=esc_html(a['url']),
                                ji='申込み・くわしくは、この会のサイト')
                if a['url'] else '')
        return KEN_T.format(
            tsugi=(' gyo--tsugi' if i == 0 else ''), ban=i,
            ref=ref, kao=kao, win=win,
            md='%d/%d' % (d.month, d.day), youbi=youbi,
            ja=esc_html(a['seishiki'] or a['ja']), shurui=a['shurui'], ja_date=ja_md(d),
            basho=('・' + esc_html(a['basho'])) if a['basho'] else '',
            nokori=a['nokori'], gyou=gyou, soto=soto)
    # 2026-09-21：一覧も、こよみと同じ「よこにスライド」にしました。
    #   横に並ぶので、ぜんぶ出してもページは伸びません。ふたは要らなくなりました。
    hyo = yoko_ban([gyo(a, i) for i, a in enumerate(ken)],
                   '近い研究会の一覧。%d件を、よこにスライドして見ます' % len(ken),
                   mae='前の研究会を見る', tsugi='次の研究会を見る', ji=6,
                   haba='min(420px,92%)', cls='hyo hyo--ken')
    return ('    <div class="ima-2">\n'
            + build_koyomi(ken, kyou) + '\n'
            + '    <div class="ima-migi">\n' + hyo + '\n    </div>\n'
            + '    </div>')


# ══════════════════════════════════════════════════════════
# 3-3. ほかの研究会（単なるリンク集にしない＝様子の1行とタグが要る）
# ══════════════════════════════════════════════════════════

# ── 47都道府県と、地方のまとまり（2026-09-22）────────────────
#   ここは2か所で使います。
#     ① 研究会を「地方ごと」に束ねる（このすぐ下の KAI）
#     ② 届いた実践の「地域」を確かめる（kenmon_jissen の ★地域）
#   数が30・40と増えたら、この表がそのまま「地図から絞る」の土台になります。
#   ★並びは北から南。地図を出すときも、この順に読みます。
CHIHO = (
    ('北海道・東北', ('北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県')),
    ('関東',         ('茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県')),
    ('中部',         ('新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県',
                      '岐阜県', '静岡県', '愛知県')),
    ('近畿',         ('三重県', '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県', '和歌山県')),
    ('中国・四国',   ('鳥取県', '島根県', '岡山県', '広島県', '山口県',
                      '徳島県', '香川県', '愛媛県', '高知県')),
    ('九州・沖縄',   ('福岡県', '佐賀県', '長崎県', '熊本県', '大分県', '宮崎県',
                      '鹿児島県', '沖縄県')),
)
KEN_ZEN = tuple(k for _, ks in CHIHO for k in ks)          # 47

# ── 日本の地図（2026-09-22 依頼）────────────────────────────
#   「みんなの実践」を、県から絞るための地図です。
#
#   ★形は、ここに書いた **経度・緯度** から組み立てます。
#     画像は1枚も使いません。外からも1バイトも取りにいきません
#     （Googleマップ等は開いただけで通信が飛びます。原則2に触れます）。
#   ★海岸線は ざっくりです。岬と湾の大きいところだけ拾っています。
#     細かくすると重くなるうえ、スマホでは どのみち見えません。
#   ★押すのは **県の札**（HTMLのボタン）で、絵の上に重ねています。
#     絵そのものを押させると、香川県が指より小さくなって押せません。
#
#   直したいとき … 下の数（経度, 緯度）を動かすだけで形が変わります。
#   CSSも画像もさわりません。

# 地図の枠。ここに入る範囲だけを描きます（沖縄は別枠）。
CHIZU_W, CHIZU_H = 480.0, 532.0
CHIZU_LON0, CHIZU_LAT0 = 129.0, 45.9      # 左上のかど
CHIZU_K = 34.0                            # 1度あたりの大きさ
CHIZU_YOKO = 0.809                        # 北緯36度での、経度1度のちぢみ


def chizu_ten(lon, lat):
    """経度・緯度を、地図の中の位置に直す（ふつうの正距円筒図法）。"""
    return ((lon - CHIZU_LON0) * CHIZU_YOKO * CHIZU_K,
            (CHIZU_LAT0 - lat) * CHIZU_K)


# 島のかたち。時計まわりに、岬と湾をたどります。
CHIZU_SHIMA = {
    '北海道': (
        (141.9, 45.5), (142.6, 44.8), (143.9, 44.3), (144.8, 43.9),
        (145.3, 44.35), (145.55, 43.3), (145.0, 43.0), (144.3, 42.95),
        (143.3, 42.3), (143.25, 41.9), (142.5, 42.5), (141.6, 42.6),
        (140.9, 42.35), (140.5, 41.75), (140.05, 41.45), (139.85, 41.9),
        (140.3, 42.55), (139.8, 43.25), (140.5, 43.4), (140.3, 43.9),
        (141.4, 44.6), (141.6, 45.2),
    ),
    '本州': (
        (141.45, 41.45), (140.9, 41.2), (140.3, 41.25), (140.0, 40.5),
        (139.85, 39.9), (139.9, 38.9), (139.4, 38.2), (138.9, 37.8),
        (138.3, 37.2), (137.35, 36.75), (137.0, 37.5), (136.75, 36.85),
        (136.05, 36.2), (135.75, 35.55), (135.15, 35.75), (134.2, 35.6),
        (133.0, 35.55), (132.0, 35.15), (130.95, 34.4), (130.9, 34.0),
        (131.4, 33.85), (132.0, 34.05), (132.55, 34.25), (133.4, 34.4),
        (134.4, 34.55), (135.2, 34.4), (135.15, 33.9), (135.75, 33.45),
        (136.4, 34.2), (136.85, 34.25), (136.85, 34.75), (137.5, 34.65),
        (138.3, 34.6), (138.85, 34.6), (139.15, 35.15), (139.7, 35.25),
        (139.85, 34.9), (140.4, 35.1), (140.85, 35.7), (140.65, 36.4),
        (140.95, 37.0), (141.05, 38.25), (141.6, 38.3), (141.55, 39.0),
        (142.05, 39.5), (141.95, 40.45), (141.4, 40.6),
    ),
    '四国': (
        (134.6, 34.3), (134.75, 33.85), (134.2, 33.55), (134.18, 33.25),
        (133.5, 33.5), (133.0, 33.15), (132.8, 32.9), (132.45, 33.3),
        (132.4, 33.95), (132.75, 34.15), (133.6, 34.35),
    ),
    '九州': (
        (130.95, 33.95), (131.35, 33.7), (131.75, 33.75), (131.9, 33.3),
        (131.55, 32.8), (131.5, 31.9), (131.05, 31.4), (130.7, 31.0),
        (130.6, 31.45), (130.3, 31.2), (130.2, 31.95), (130.05, 32.6),
        (129.8, 32.75), (129.6, 33.0), (129.95, 33.4), (129.8, 33.6),
        (130.25, 33.6), (130.4, 33.9), (130.75, 33.9),
    ),
}

# 沖縄は、そのままの位置だと地図が縦にのびて、本州が小さくなります。
#   だから左下に別枠を置きます（日本の地図の、ふつうのやり方です）。
#   ★置き場所は **右下（太平洋がわ）**です。左下は九州が立っているので、
#     そこに置くと枠が九州に重なります（実測で踏みました）。
CHIZU_OKI_WAKU = (348.0, 404.0, 120.0, 120.0)    # x y 幅 高さ
#   沖縄本島は、北東から南西へ ほそ長くのびた島です。
CHIZU_OKI = (
    (128.33, 26.87), (128.36, 26.70), (128.14, 26.54), (127.97, 26.45),
    (127.85, 26.29), (127.76, 26.08), (127.64, 26.10), (127.70, 26.26),
    (127.79, 26.41), (127.89, 26.52), (128.06, 26.64), (128.19, 26.79),
)

# 47都道府県を置くところ（経度, 緯度）。県庁ではなく、県の真ん中あたり。
#   札が重なったら、build_chizu が下へずらします（手で直さなくて大丈夫）。
KEN_ICHI = {
    '北海道': (142.9, 43.4), '青森県': (140.75, 40.75), '岩手県': (141.4, 39.6),
    '宮城県': (140.95, 38.45), '秋田県': (140.4, 39.75), '山形県': (140.15, 38.45),
    '福島県': (140.3, 37.5), '茨城県': (140.3, 36.3), '栃木県': (139.8, 36.7),
    '群馬県': (138.95, 36.5), '埼玉県': (139.35, 36.0), '千葉県': (140.2, 35.5),
    '東京都': (139.4, 35.7), '神奈川県': (139.3, 35.4), '新潟県': (138.9, 37.5),
    '富山県': (137.2, 36.6), '石川県': (136.75, 36.65), '福井県': (136.2, 35.85),
    '山梨県': (138.6, 35.6), '長野県': (138.1, 36.15), '岐阜県': (137.0, 35.8),
    '静岡県': (138.3, 34.95), '愛知県': (137.2, 35.05), '三重県': (136.4, 34.5),
    '滋賀県': (136.1, 35.2), '京都府': (135.6, 35.2), '大阪府': (135.5, 34.6),
    '兵庫県': (134.85, 35.0), '奈良県': (135.9, 34.3), '和歌山県': (135.4, 33.9),
    '鳥取県': (133.95, 35.4), '島根県': (132.5, 35.1), '岡山県': (133.8, 34.85),
    '広島県': (132.75, 34.6), '山口県': (131.6, 34.2), '徳島県': (134.3, 33.9),
    '香川県': (134.0, 34.2), '愛媛県': (132.9, 33.7), '高知県': (133.4, 33.5),
    '福岡県': (130.6, 33.5), '佐賀県': (130.15, 33.3), '長崎県': (129.85, 32.95),
    '熊本県': (130.8, 32.6), '大分県': (131.4, 33.2), '宮崎県': (131.35, 32.2),
    '鹿児島県': (130.6, 31.6), '沖縄県': (127.9, 26.4),
}

if sorted(KEN_ICHI) != sorted(KEN_ZEN):
    # ★検問。1県でも落ちると、その県の実践が地図からさがせなくなります。
    _nai = [k for k in KEN_ZEN if k not in KEN_ICHI]
    _yobun = [k for k in KEN_ICHI if k not in KEN_ZEN]
    raise SystemExit('KEN_ICHI（地図の位置）がそろっていません。'
                     '足りない：%s ／ 余分：%s'
                     % ('、'.join(_nai) or '無し', '、'.join(_yobun) or '無し'))

KEN_CHIHO = dict((k, ch) for ch, ks in CHIHO for k in ks)  # 県 → 地方

if len(KEN_ZEN) != 47 or len(KEN_CHIHO) != 47:
    raise SystemExit('CHIHO の都道府県が47ではありません（%d）' % len(KEN_ZEN))


# (範囲, 範囲の字, だれ向け, 都道府県, 会の名前, URL, 様子の1行, 置いてあるもののタグ)
#
#   都道府県は、地方ごとに束ねるための鍵です。全国の会は '' にします。
#   市の会は、その市がある県を書きます（川崎市→神奈川県）。
KAI = (
    ('zen', '全国', '小・中・高', '',
     '全国特別活動研究会',
     'https://zentokkatsu.com/',
     '全国大会と冬季研・夏季ゼミの案内。この一覧そのものの出どころです。',
     ('大会案内', '各地の会の一覧')),
    ('zen', '全国', '小中高・研究者', '',
     '日本特別活動学会',
     'https://jaseatokkatsu.jimdoweb.com/',
     'オンラインの勉強会「特活カフェ」と研究会の案内。紀要と会報はPDFで読めます。',
     ('研究会案内', '紀要・会報PDF')),
    ('zen', '全国', '小学校', '',
     '特別活動 希望の会',
     'https://kibounokai.web.wox.cc/',
     '教科調査官と実践者のネットワーク。小学校特別活動の映像資料と大会の案内。',
     ('映像資料', '大会案内')),
    ('zen', '全国', '小学校', '',
     '全国小学校学校行事研究会',
     'https://zensyo-gyou.com/',
     '学校行事のガイドラインと研究報告。行事を「思い出づくり」から動かしたいときに。',
     ('行事のガイドライン', '研究報告')),
    ('zen', '全国', '小・中', '',
     '全国道徳特別活動研究会',
     'https://doutokutokkatukatarukai.jimdofree.com/',
     '昭和33年から続く会。全国大会と、月例会「大いに語る会」の案内。道徳といっしょに考えます。',
     ('全国大会', '月例会')),
    ('ken', '都', '小学校', '東京都',
     '東京都小学校特別活動研究会',
     'http://tosho-tokkatsu.tokyo/',
     '検証授業の予定一覧と研究紀要、会報「都小特活」。ホームの研究日程は、ここから拾っています。',
     ('研究会の日程', '研究紀要')),
    ('ken', '都', '中学校', '東京都',
     '東京都中学校特別活動研究会',
     'https://www.tochutokkatsu.com/',
     '月例研修会の予定、生徒会長サミット、研究紀要、講師派遣の窓口。',
     ('月例研修会', '生徒会長サミット')),
    ('ken', '都', '高等学校', '東京都',
     '東京都高等学校特別活動研究会',
     'http://tokkatsu.com/',
     '都高特活。高校の特別活動の研究協議会と、新しく担当になった先生への案内。',
     ('研究協議会',)),
    ('ken', '県', '小・中', '埼玉県',
     '埼玉県特別活動研究会',
     'http://saitokkatsu.sub.jp/',
     '研究主題と年間計画、研究集録のバックナンバー、資料のダウンロード。',
     ('資料ダウンロード', '研究集録')),
    ('shi', '市', '小学校', '神奈川県',
     '川崎市立小学校特別活動研究会',
     'https://kawasaki-edu.jp/9/2kenkyukai/index.cfm/12,0,60,html',
     '特活データベース。実践事例集・司会台本・学級会ノート・板書グッズ。刷ってすぐ使えるものが多いです。',
     ('実践事例集', '司会台本・板書グッズ')),
    ('shi', '市', '小学校', '神奈川県',
     '横浜市立小学校特別活動研究会',
     'http://yokohamatokkatu.cool.coocan.jp/index.html',
     '研究紀要と現況調査報告書。紀要で使ったワークシートがダウンロードできます。',
     ('ワークシート', '現況調査')),
    ('shi', '市', '小学校', '愛知県',
     '名古屋市特別活動実践研究会',
     'http://www.nagoyatokkatsu.com/',
     'なごやとっかつ。「とっかつ 学びの扉」と「特活だより」。読み物として読めるものが多いです。',
     ('読み物', '特活だより')),
    ('ken', '県', '中学校', '広島県',
     '広島県中学校教育研究会 特別活動部会',
     'https://www.pref.hiroshima.lg.jp/site/kyougikai/tokukatu.html',
     '広島県の研究団体連絡協議会の中のページ。県の研究大会の予定が出ます。',
     ('県の研究大会',)),
    ('ken', '県', '小学校', '熊本県',
     '熊本県特別活動研究会',
     'https://estokkatsu.wixsite.com/index',
     '研究資料室に、活動報告書・年間指導計画・実態調査。会報「特活通信」のバックナンバーもあります。',
     ('年間指導計画', '会報')),
    ('shi', '市', '小学校', '北海道',
     '札幌市特別活動研究会',
     'http://www.sattokkatu.com/',
     '研究の足跡と実践事例、研究・研修会のお知らせ。北海道（北特活）のコーナーもあります。',
     ('実践事例', '研修会')),
)

# 2026-09-22：上から3件、という切り方をやめました。
#   前は「上から KAI_UE_N 件だけ出して、のこりはふた」でした。
#   切れ目が会の並びの途中に来るので、押した人は
#   「いま何を見ているのか」が分かりませんでした。
#   いまは **全国の会だけを出して、各地の会はふたの中**に分けます。
#   ふたの見出しに地方の名前を並べるので、開く前から
#   「どこの会が入っているか」が読めます。

# 地方ごとの小見出し。会が1つもない地方は、そもそも出しません
#   （空の見出しを置かない。「近畿には会が無い」とは言えないためです）。
KAIGUMI_T = """      <div class="kaigumi">
        <h3 class="kaigumi-h"><span class="kaigumi-ji">{ch}</span><span class="kaigumi-n">{n}会</span></h3>
        <div class="kaiban">
{naka}
        </div>
      </div>"""

KAI_T = """      <a class="kai" data-ken="{ken}" href="{url}" target="_blank" rel="noopener noreferrer">
        <span class="kai-ue"><span class="kai-han han--{han}">{han_ji}</span><span class="kai-muke">{muke}</span><span class="kai-soto">外部</span></span>
        <b class="kai-na">{na}</b>
        <span class="kai-yo">{yo}</span>
        <span class="kai-shita">{tag}<span class="kai-do">{do}</span></span>
      </a>"""


# 研究会の地図（2026-09-23 依頼）。
#   2026-09-22 には「会が7都道県しかなく、40県が真っ白になるので地図にしない」
#   と決めていました。依頼で入れます。かわりに、白い県が
#   「会が無い」ではなく「まだ載せていない」ことを、字で必ず出します。
#   ★カードの形は、そのままです。地図は **絞りこみの札** として上に置きます。
#   ★全国の会は、どの県を押しても出したままにします（どこに居ても関わるため）。
KAI_CHIZU_T = """    <div class="kaichizu" id="kaichizu">
{chizu}      <p class="chizu-ima" id="kaichizu-ima" hidden><span></span>
        <button type="button" class="chizu-modosu">ぜんぶに戻す</button></p>
    </div>
"""

KAI_CHIZU_YOMI = ('押すと、その県の会だけになります。もう一度押すと もどります。<br>\n'
                  '          <b>札が立っているのが、いま載せている県です。</b>札の無い県は\n'
                  '          「そこに会が無い」のではなく、<b>まだ載せていないだけ</b>です。<br>\n'
                  '          <b>全国の会は、どの県を押しても出したままにします。</b>')


def kai_chizu(aru_ken):
    """研究会の地図。1つも県が無いときは、地図ごと出しません。"""
    return build_chizu(
        aru_ken, mid='kai-k', yomi=KAI_CHIZU_YOMI,
        nashi='いまは %(ken)d都道県に %(kazu)d会。'
              'のこり %(nokori)d県は、まだ載せていないだけです。')


def build_kai():
    """研究会の一覧。全国の会をそのまま出し、各地の会は地方ごとに束ねて
       ページの中のふたへ入れます（2026-09-22 依頼）。

       なぜ地方で束ねるのか
         15会を均等に並べると、どこの会かは範囲の2文字（全国／都／県／市）
         でしか分かりませんでした。地方の小見出しを入れると、
         自分の近くの会が一目で見つかります。
       地図について（2026-09-23 に入れました）
         2026-09-22 には「会があるのは7都道県だけで、のこり40県が真っ白に
         なる。白いのは"会が無い"ではなく"まだ載せていない"だけなので、
         事実とちがうことを伝えてしまう」として、地図を入れませんでした。
         依頼で入れます。**そのかわり、白い県の意味を地図の上に必ず書きます。**
         形は、そのときに決めておいたとおりです ──
         **地図は絞りこみの札。カードの形は、そのまま残す。**
         全国の会は、どの県を押しても出したままにします
         （どこに住んでいても関わる会なので、消すと不便になるため）。
    """
    from urllib.parse import urlsplit
    mita = set()
    zen, chihou, aru_ken = [], {}, []
    for han, han_ji, muke, ken, na, url, yo, tags in KAI:
        if han not in ('zen', 'ken', 'shi'):
            raise Tomeru('ほかの研究会「%s」の範囲が %s です（zen／ken／shi のどれか）' % (na, han))
        if not url.startswith(('http://', 'https://')):
            raise Tomeru('ほかの研究会「%s」のURLが http(s) で始まっていません（%s）' % (na, url))
        if url in mita:
            raise Tomeru('ほかの研究会で、同じURLが2回出ています（%s）' % url)
        mita.add(url)
        # ★ ここが原則③（単なるリンク集にしない）の検問です
        if len(yo.strip()) < 12:
            raise Tomeru('ほかの研究会「%s」の「様子の1行」が短すぎます。'
                         '名前とURLだけ並べるのは、このサイトではやらないと決めています' % na)
        if not tags:
            raise Tomeru('ほかの研究会「%s」に、置いてあるもののタグが1つもありません' % na)
        # ★ 2026-09-22 に足した検問。地方ごとに束ねる鍵なので、
        #   ここが空だったり ずれていたりすると、会が静かに消えます。
        if han == 'zen':
            if ken:
                raise Tomeru('ほかの研究会「%s」は全国の会なのに 都道府県（%s）が'
                             '書いてあります。全国の会は空にしてください' % (na, ken))
        else:
            if not ken:
                raise Tomeru('ほかの研究会「%s」に 都道府県が書いてありません。'
                             '地方ごとに束ねられません（市の会は、その市のある県を書く）' % na)
            if ken not in KEN_CHIHO:
                raise Tomeru('ほかの研究会「%s」の都道府県「%s」が 47都道府県に'
                             'ありません（「東京都」「神奈川県」のように書く）' % (na, ken))
        fuda = ''.join('<span class="kai-tag">%s</span>' % esc_html(t) for t in tags)
        gyo = KAI_T.format(
            url=esc_html(url), han=han, han_ji=esc_html(han_ji), muke=esc_html(muke),
            ken=esc_html(ken),
            na=esc_html(na), yo=esc_html(yo), tag=fuda,
            do=esc_html(urlsplit(url).netloc.replace('www.', '')))
        if han == 'zen':
            zen.append(gyo)
        else:
            chihou.setdefault(KEN_CHIHO[ken], []).append(gyo)
            aru_ken.append({'ken': ken})

    honbun = ('    <div class="kaigumi kaigumi--zen">\n'
              '      <h3 class="kaigumi-h"><span class="kaigumi-ji">全国</span>'
              '<span class="kaigumi-n">%d会</span></h3>\n'
              '      <div class="kaiban">\n%s\n      </div>\n'
              '    </div>' % (len(zen), '\n'.join(zen)))

    # 地方は、北から南へ。会が1つもない地方は出しません。
    kumi, na_zoro, kazu = [], [], 0
    for ch, _ in CHIHO:
        if ch not in chihou:
            continue
        naka = chihou[ch]
        kazu += len(naka)
        na_zoro.append(ch)
        kumi.append(KAIGUMI_T.format(ch=esc_html(ch), n=len(naka), naka='\n'.join(naka)))
    if not kumi:
        return KAI_CHIZU_T.format(chizu=kai_chizu(aru_ken)) + honbun
    return (KAI_CHIZU_T.format(chizu=kai_chizu(aru_ken))
            + tsunagu(honbun, '\n'.join(kumi), kazu,
                      a='各地の研究会 %d会を、このページで開く（%s）'
                        % (kazu, '／'.join(na_zoro))))


# ══════════════════════════════════════════════════════════
# 3-4. 新版（縦スクロール1枚）を組み立てる
# ══════════════════════════════════════════════════════════

# 4つの内容。採用した学校全景の各活動を切り出す（x y 幅 高さ）。
#
# このサイトの背骨です。広場で出た悩みも、届いた実践も、ぜんぶこの4つに集めます。
#
# 2026-09-21：ここは本体サイトの #manabu へ飛んでいました。
# 飛び先は別のデザインなので、押した人は「別のサイトへ出された」と感じます。
# だから、いまは **どこへも飛ばしません**。カードの中で、その内容の
# 悩み（src/komari の naiyo）と実践（src/jissen の naiyo）が、その場で開きます。
YOTSU = (
    ('n-gakkyu',  'GAKKYU KATSUDO',  '学級活動',   '35 740 935 725',
     '学級会・係・当番・給食。子どもが自分たちで決める時間です。'),
    ('n-gyoji',   'GAKKO GYOJI',     '学校行事',   '1020 755 1150 790',
     '運動会・卒業式・遠足。思い出をつくる時間ではなく、子どもが育つ時間です。'),
    ('n-jidokai', 'JIDOKAI KATSUDO', '児童会活動', '2280 550 875 560',
     '代表委員会・集会・あいさつ運動。学年をこえて学校をつくります。'),
    ('n-club',    'CLUB KATSUDO',    'クラブ活動', '2280 1100 875 445',
     '音楽・図工・科学・運動。好きなことを、学年をこえて。'),
)


def sensei_ja(by):
    """送ってくださったお名前に「先生」を付ける（2026-09-23 依頼）。
       「西野穂乃花（徳島県…千松小学校）」→「西野穂乃花先生（徳島県…千松小学校）」
       ★学校名（かっこの中）は、そのまま残します。どこの実践かが分かるためです。
       ★もう「先生」が付いているときは、足しません。
       ★名前が無いとき（出してよい に印が無いとき）は、そのまま返します。"""
    t = (by or '').strip()
    if not t:
        return t
    i = min([x for x in (t.find('（'), t.find('(')) if x >= 0] or [len(t)])
    na, ato = t[:i].strip(), t[i:]
    if not na or re.search(r'(先生|教諭|教員|さん)$', na):
        return t
    return na + '先生' + ato


def naiyo_ichiran():
    """('gakkyu', '学級活動') の組。4つの内容の id は クラス名の n- を取ったもの。"""
    return [(c[2:], ja) for c, _, ja, _, _ in YOTSU]


def naiyo_ja(nid):
    return dict(naiyo_ichiran())[nid]


# ── 広場で出た悩み ────────────────────────────────
#
# ★2026-09-22、**書き置きをやめました。**
#   ここには手で書いた悩みが24件ありました。読みものとしては良かったのですが、
#   「最初から全部そろっている」ので、**みんなで作っている感じになりません**。
#   いまは `src/komari/*.md` ＝ **送られた困りごと** が、そのまま悩みになります。
#   消した24件は `src/komari/_LINEから書き出したもの.md` に控えてあります
#   （頭が _ なので出ません）。1件ずつ .md にすれば、また並びます。
#
# ★悩みが「解ける」しくみ
#   送られたときは、naiyo も saki も空です。＝ まだ答えがついていない悩み。
#   人があとから .md に saki: 2 と足すと、押せる札になり、学習過程の②が開きます。
#   naiyo: gakkyu と足すと、4つの内容のカードにも並びます。
#   **答えが増えるほど、押せる札が増えていきます。**それが見えるのが狙いです。
#
# 載せるときの約束（送られたぶんにも、同じことが要ります）
#   1. 発言をそのまま引用しない。**悩みの言葉に言いかえる**（title: で直せます）
#   2. 発言者・学校・地域は**一切載せない**
#   3. 1人の個別事情が分かる書き方にしない。**同じ困りごとの一般形**にする
#   4. 答えを置けていないものも消さない。**「まだ答えが無い」ことが情報**です

# 「学ぶ」のお悩み別の入口に出す数。
# ぜんぶ出すと入口が長くなって、入口の役をしなくなります。
NAYAMI_IRIGUCHI = 6

MARU = '①②③④⑤'


def nayami_gyo(a, ji=' ' * 8):
    """悩み1つぶんの行。
       saki があれば押せる札（学習過程のそこが開く）。
       無ければ、その悩みの本文へ行く札（困りごとのページ）。"""
    kotoba = esc_html(a['mijikai'])
    if a['saki']:
        return ('%s<li><button type="button" data-learn-step="%s">'
                '<span>%s</span><span class="to">%sへ</span></button></li>'
                % (ji, a['saki'], kotoba, MARU[int(a['saki']) - 1]))
    return ('%s<li class="mada"><a href="#k-%s"><span>%s</span>'
            '<span class="to to--mada">まだ答えなし</span></a></li>'
            % (ji, a['slug'], kotoba))


NAYAMI_KARA = """      <p class="nayami-mada">まだ1件もありません。<br>
      いま困っていることを <a href="#komari">ちょっと聞きたい</a> から送ってください。
      送られたものが、そのままここに並びます。</p>"""


def build_nayami(komari):
    """「学ぶ」から困りごとへの行き先。**中身はもう出しません**（2026-09-22）。

       前は、届いた困りごとの札を6つ、ここにも並べていました。同じ札が
       困りごと・学ぶ・4つの内容 の3か所にあり、読む人は同じものを何度も
       見せられていました。**中身は1か所**と決めたので、ここは
       「いくつあるか」と「どこへ行けば読めるか」だけにします。

       答えが付いたもの（saki あり）の数は、別に出します。
       「答えが付いている」こと自体が、学ぶへ来た人の知りたいことなので。"""
    if not komari:
        return NAYAMI_KARA
    tsuita = sum(1 for a in komari if a['saki'])
    return ('      <p class="nayami-saki"><a href="#komari">'
            '届いた困りごと %d件を読む<i>→</i></a>'
            '<span class="nayami-uchi">うち %d件は、答えが見つかっています</span></p>'
            % (len(komari), tsuita))


YOTSU_T = """      <div class="naiyo {cls}" id="naiyo-{nid}">
        <div class="naiyo-e"><svg viewBox="{win}" role="img" aria-label="{ja}のイラスト"><use href="#ill-hiroba"/></svg>
          <i class="naiyo-kao" aria-hidden="true"><svg viewBox="0 0 {kw} {kh}" focusable="false"><use href="#ill-k-{n}"/></svg></i>
        </div>
        <div class="naiyo-t">
          <span class="ban"><i></i>{en}</span>
          <h3>{ja}</h3>
          <p class="na">案内は<b>{na}</b></p>
          <p>{setsumei}</p>
{atsume}        </div>
      </div>"""

YOTSU_OKURU = """          <p class="naiyo-okuru"><a href="#okuru">{ja}の実践を送る<span class="d">→</span></a></p>
"""


def yotsu_atsume(nid, ja, nayami, jissen):
    """カードの下に置く、1行だけ。

       2026-09-22：ここには その内容の悩みと実践を集めていました。
       同じ札が 困りごと・学ぶ・4つの内容 の3か所に出ていたためです。
       **索引は外して、カードは「4つとは何か」の説明に戻しました。**
       残すのは、送るところへの行き1本だけです（これは索引ではなく、
       その場でできることなので）。"""
    return YOTSU_OKURU.format(ja=esc_html(ja))


# 「中身は1か所」の決めごと（2026-09-22）──────────────────
#   同じ札が、困りごと・学ぶ・4つの内容 の3か所に出ていました。
#   実践の題名も、みんなの実践 と 4つの内容 の2か所に出ていました。
#   読む人は、同じものを何度も見せられて、どこが本物か分からなくなります。
#
#   だから決めました。**中身（札そのもの）は1か所だけ。**
#   ほかの場所に置くのは「いくつあるか」と「どこへ行けば読めるか」だけです。
#
#     困りごと … 中身は 困りごと。ほかは 数＋行き先
#     実践　　 … 中身は みんなの実践。ほかは 数＋行き先
#     道具　　 … 中身は すぐ使える道具。ほかは 数＋行き先


def build_yotsu(kyara, jissen, komari):
    # どのカードに だれが立つかは KYARA_MEN の4つめ（クラス名）で結びます
    dare = dict((cls, (n, na)) for n, na, _, cls in KYARA_MEN)
    gyo = []
    for c, en, ja, w, se in YOTSU:
        if c not in dare:
            raise Tomeru('4つの内容 %s に立つキャラクターが決まっていません'
                         '（build.py の KYARA_MEN を見てください）' % c)
        nid = c[2:]
        n, na = dare[c]
        gyo.append(YOTSU_T.format(
            cls=c, nid=nid, en=en, ja=ja, win=w, setsumei=se,
            n=n, na=na, kw=kyara[n][0], kh=kyara[n][1],
            atsume=yotsu_atsume(nid, ja,
                                [a for a in komari if a['naiyo'] == nid],
                                [a for a in jissen if a['naiyo'] == nid])))
    return '    <div class="yotsu">\n' + '\n'.join(gyo) + '\n    </div>'


# ══ のこりを「このページの中で」開く ふた ══════════════════
#   2026-09-21：以前は「ぜんぶ見る→」で本体サイトへ飛ばしていました。
#   飛び先は別のデザインなので、押した人は別のサイトに出されたと感じます。
#   ふたを開けるだけにすれば、見た目も、いる場所も変わりません。
MOTTO = """    <details class="motto">
      <summary><span class="a">{a}</span><span class="b">とじる</span></summary>
{naka}
    </details>"""


def tsunagu(ue, nokori_html, n, a=None):
    """上に出すぶん ＋（のこりがあれば）ふたの中。

       a … ふたの見出しの字。書かなければ「のこり◯件を、このページで開く」。
           研究会は、開く前から中身が読めるように
           「各地の研究会 10会を、このページで開く（北海道・東北／関東／…）」
           と地方の名前まで出します（2026-09-22）。
    """
    if not n:
        return ue
    return ue + '\n' + MOTTO.format(
        n=n, naka=nokori_html,
        a=esc_html(a) if a else 'のこり%d件を、このページで開く' % n)


# ══ すぐ使える実践（中身まで、この1枚の中で開く） ══════════
#   前は一覧の行で、押すと本体サイトの「まなぶ」タブへ飛んでいました。
#   いまは 準備・流れ・板書・つまずき まで、ここで開きます。
#   JSは1行も使いません（<details> だけ）。だから何も送信しません。
JFUDA = """      <article class="fuda{kcls}" id="j-{slug}">
        <p class="fuda-me"><a class="fuda-tag t--{nid}" href="#naiyo-{nid}">{naiyo}</a>{kindtag}{meta}</p>
        <h3 class="fuda-h">{title}</h3>
        <p class="fuda-lead">{lead}</p>
{more}{setb}{weekly}        <p class="fuda-by">実践者：{by}</p>
      </article>"""

JFUDA_MORE = """        <details class="hiraku">
          <summary><span class="a">くわしく（準備・流れ・板書）</span><span class="b">とじる</span></summary>
          <div class="fuda-naka">
{body}
          </div>
        </details>
"""

JFUDA_SET = """        <p class="fuda-set"><b>セットで使うもの</b>{items}</p>
"""

JFUDA_SHU = """        <p class="shuan"><span class="shuan-l">週案に貼る1行</span><span class="shuan-t">{weekly}</span></p>
"""

# 持ち帰れる資料（指導案・スライド・板書の写真など）。
# ★埋めこまずにリンクにする。iframe で埋めると、ページを開いただけで
#   外部に通信が飛んで「何も送信しない」が崩れるため。
JFUDA_SHIRYO = """        <p class="fuda-shiryo"><b>持ち帰れる資料</b>{items}</p>
"""

# 板書への渡り。写真そのものは **板書のページにだけ** 入っています。
#   同じ画像を2ページに埋めると重さが倍になるので、ここはリンク1本です。
#   飛び先は同じCSS・同じ帯・戻り道あり（2026-09-21に決めた条件）。
JFUDA_BANSHO = """        <p class="fuda-bansho"><a class="bansho-b" href="#b-{slug}">写真を大きく見る（{n}枚）<i>→</i></a></p>
"""


JISSEN_UE_N = 2   # 実践を、上から何枚だけ出しておくか（のこりはページの中のふた）


def bansho_kazu(oki):
    """板書のフォルダに画像が何枚あるかだけ数える（読みこみません）。"""
    return len([x for x in glob.glob(os.path.join(BANSHO, oki, '*'))
                if os.path.splitext(x)[1].lower() in SHIRYO_MIME])


def build_jissen_hiroba(jissen, goods):
    fuda = []
    for a in youi_shita(jissen):
        more = JFUDA_MORE.format(body=md_html(a['rest'])) if a['rest'].strip() else ''
        # グッズは、まだ配れないものが多い。リンクにはしないで、状態を字で出す
        items = []
        for g in a['goods_ids']:
            items.append('<span class="gone">%s<i>%s</i></span>'
                         % (esc_html(goods[g]['title']), goods_status(goods[g]) or '準備中'))
        setb = JFUDA_SET.format(items=''.join(items)) if items else ''
        shu = JFUDA_SHU.format(weekly=esc_html(a['weekly'])) if a.get('weekly') else ''
        sh, mado = [], []
        for m, kind, v in a.get('shiryo_list', []):
            if kind == 'naka':
                mado.append(shiryo_mado(m, v, a['title']))
            elif kind == 'sakuin':
                # 索引。押せる見た目にしません（押しても何も起きない、を作らない）
                sh.append('<span class="shiryo-s"><b>%s</b>%s<i>索引</i></span>'
                          % (esc_html(m), esc_html(v)))
            else:
                sh.append('<a class="shiryo-b" href="%s" target="_blank" '
                          'rel="noopener noreferrer">%s<i>外部</i></a>'
                          % (esc_html(v), esc_html(m)))
        shb = ''.join(mado) + (JFUDA_SHIRYO.format(items=''.join(sh)) if sh else '')
        # 板書の写真があれば、板書のページへ渡します（写真はあちらにだけ入っています）
        ban = (JFUDA_BANSHO.format(slug=a['slug'], n=bansho_kazu(a['bansho']))
               if a.get('bansho') else '')
        gidai = (a['kind'] == 'gidai')
        meta = '・'.join(x for x in (esc_html(a['scene']), esc_html(a['grade']),
                                     esc_html(a['time'])) if x)
        fuda.append(JFUDA.format(
            slug=a['slug'], nid=a['naiyo'], naiyo=esc_html(naiyo_ja(a['naiyo'])),
            kcls=' fuda--gidai' if gidai else '',
            kindtag='<span class="fuda-kind">議題</span>' if gidai else '',
            meta=meta, title=esc_html(a['title']), lead=inline_md(a['lead']),
            more=more, setb=setb + shb + ban, weekly=shu,
            by=esc_html(sensei_ja(a['by']))))
    # 2026-09-21：札をぜんぶ縦に並べると、ここだけでスマホ5画面ありました。
    #   上から JISSEN_UE_N 枚だけ出して、のこりはこのページの中のふたへ。
    #   4つの内容から #j-◯◯ で飛んできたときは、akeru() がふたを先に開きます。
    if not fuda:
        # 用意したものが1つも無いとき。空の棚を押せる形で出しません
        return ('    <p class="karappo">道具は、いま用意しているところです。'
                '学級会グッズ・映像資料・よく出る困りごとに効く手だてを、'
                '1つずつここに置いていきます。<br>'
                '<b>先生方から届いた実践は「みんなの実践」にあります。</b></p>')
    ue, ato = fuda[:JISSEN_UE_N], fuda[JISSEN_UE_N:]
    honbun = '    <div class="tefuda">\n' + '\n'.join(ue) + '\n    </div>'
    if not ato:
        return honbun
    naka = '      <div class="tefuda">\n' + '\n'.join(ato) + '\n      </div>'
    return tsunagu(honbun, naka, len(ato))


# ══ 板書（2026-09-21 新設。「溜める」と決めたので、置き場を分けました）══
#   写真は **このページにだけ** 入ります。実践の札からは、リンク1本で渡ります。
#   ここに溜まるいっぽうなので、build の最後に「いま何MB・あと何枚」を出します。
# 板書は「大きく出す」が既定です（2026-09-22）。
#   実測：届いた1枚めは 1400×418 の横長でした。札の幅（405px）で頭打ちになり、
#   **405×124** でしか出ていませんでした。窓には585pxの高さが空いていたのにです。
#   黒板は横長なので、効くのは高さではなく **幅** でした。だから札の外まで広げます。
#   それでもスマホでは字が読めないので、1枚ずつ［大きく見る］を付けます。
#   ★開く先は、同じページの中にある同じ画像です。外へは1バイトも出ません。
# 「みんなの実践」の1件。
#   2026-09-22：前は写真だけを出して、中身は「この実践を読む →」で
#   道具箱の節へ飛ばしていました。棚を分けたので、飛ぶ先がもうありません。
#   **1件ぶんを、ここで丸ごと出します。**
BFUDA = """      <article class="bfuda" id="b-{slug}" data-naiyo="{nid}" data-toki="{toki}" data-nen="{nen}"{nushi} data-t="{dai}" data-grade="{grade}" data-scene="{scene}" data-oshi="{oshi_nama}" data-hon="{hon_nama}" data-ken="{ken}" data-shi="{shi}" data-chiho="{chiho}">
        <p class="bfuda-me"><span class="bfuda-tag t--{nid}">{naiyo}</span>{kindtag}{chiiki}{meta}</p>
        <h3 class="bfuda-h">{title}</h3>
{oshi}        <p class="bfuda-lead">{lead}</p>
{more}{mado}{shiryo}        <p class="bfuda-ashi"><span class="bfuda-by">実践者：{by}</span>\
<span class="bfuda-te">{zen}\
<button class="bansho-b bansho-b--kami" type="button" data-kami="{slug}" hidden>{ICON_KAMI}<span>印刷</span></button>\
<button class="bansho-b bansho-b--ga" type="button" data-ga data-url="{ima}">{ICON_GA}<span>画像保存</span></button></span></p>
      </article>"""

# ── 札の足のボタンに付けるしるし（2026-09-23 依頼）────────────
#   「アイコンにするともっとスタイリッシュになるよね」
#   ★字は消しません。先生がはじめて見て、絵だけで分かるとは限りません。
#     しるしは **字の上**に置きます（3つ横ならびでも、字が読めます）。
#   ★線は本文と同じ墨（currentColor）。緑のボタンの上でも読めます。
def icon(d, w=22):
    return ('<svg class="b-i" viewBox="0 0 24 24" width="%d" height="%d" '
            'fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round" '
            'aria-hidden="true" focusable="false">%s</svg>' % (w, w, d))


ICON_ZEN  = icon('<circle cx="10.5" cy="10.5" r="6.5"/>'      # 虫めがね
                 '<path d="M15.3 15.3 21 21"/>'
                 '<path d="M10.5 7.8v5.4M7.8 10.5h5.4"/>')
ICON_KAMI = icon('<path d="M7 9V3h10v6"/>'                    # プリンター
                 '<rect x="3" y="9" width="18" height="8" rx="2"/>'
                 '<path d="M7 14h10v7H7z"/>')
ICON_GA   = icon('<rect x="3" y="3" width="18" height="12" rx="2"/>'   # 写真＋↓
                 '<path d="m7 12 3-3 2.5 2.5"/><circle cx="15" cy="8" r="1.3"/>'
                 '<path d="M12 17v4m0 0-2.5-2.5M12 21l2.5-2.5"/>')

# 札の足に置く［大きく見る］。どの窓を開くかを data-zen で渡します。
ZEN_B = ('<button class="bansho-b bansho-b--zen" type="button" '
         'data-zen="{doko}">' + ICON_ZEN + '<span>{na}</span></button>')

BFUDA_MADO = """        <div class="bfuda-mado bfuda-mado--hiro">
{gazou}
        </div>
"""

# 中身は、ふたに入れずに**そのまま**出します（2026-09-22）。
#   「わざわざ『この実践を読む』を押したくない」という話から。
#   押す場所を1つも作らない、が答えです。届くものは短いので、
#   開いた時点で ぜんぶ読めます（写真も、書いてもらったことも）。
#   ★長い1件が来たら、ここだけ考え直します。いまは0.5画面ぶんです。
BFUDA_MORE = """        <div class="bfuda-naka">
{body}
        </div>
"""

# 写真1枚ぶん。
#   2026-09-23（依頼）：図の下にあった［大きく見る］の行をやめました。
#   その行があると、写真は **窓の高さ** をその行に取られます。写真は
#   「できる限り大きく」が先なので、ボタンは **札の足**（提供…の行）へ
#   移しました。何枚めかの「1 / 2」は、2枚以上のときだけ 図の左上に
#   小さく重ねます（1枚しか無いときは、出す意味がありません）。
GAZOU = """              <figure class="shot"><img src="{uri}" alt="{alt}" width="{w}" height="{h}" loading="lazy" decoding="async">{kazu}</figure>"""
GAZOU_KAZU = '<span class="shot-kazu">{i} / {n}</span>'


def bansho_aru(jissen):
    """「みんなの実践」に並べるもの＝**届いたもの全部**、新しい順に。
       2026-09-22：前は「板書の写真があるものだけ」でした。それだと
       PDFだけ・議題だけで送ってくださったものが、どこにも出ませんでした。"""
    return [a for a in jissen if a.get('okuri')]


def youi_shita(jissen):
    """「すぐ使える道具」に並べるもの＝こちらで用意したもの。"""
    return [a for a in jissen if not a.get('okuri')]


def build_bansho(jissen):
    """板書のページの中身。写真の実体は、ここにだけ入ります。"""
    aru = bansho_aru(jissen)
    if not aru:
        # 0件のときに、空の棚を押せる形で出さない（正直に書く）
        return ('    <p class="karappo">まだ1件もありません。'
                '送っていただいた実践を、1件ずつここに溜めていきます。<br>'
                '黒板や資料だけが写っているもの（子どもの顔・名前が写っていないもの）を'
                'お願いしています。</p>')
    fuda = []
    for a in aru:
        # 写真が無い件（PDFだけ・議題だけ）も並べます。窓は出しません。
        mai = shiryo_yomu(a['bansho'], BANSHO, 'bansho.html') if a.get('bansho') else []
        g = [GAZOU.format(uri=uri, alt=esc_html('%s の写真 %d枚め' % (a['title'], i + 1)),
                          w=w, h=h,
                          kazu=(GAZOU_KAZU.format(i=i + 1, n=len(mai))
                                if len(mai) > 1 else ''))
             for i, (uri, w, h) in enumerate(mai)]
        mado = BFUDA_MADO.format(gazou='\n'.join(g)) if g else ''
        # 送ってもらった資料（PDFを画像にしたもの）も、ここで開きます
        sh = ''.join(shiryo_mado(m, v, a['title'], page='bansho.html', zen=False)
                     for m, kind, v in a.get('shiryo_list', []) if kind == 'naka')
        # ［大きく見る］。窓のぶんだけ出します（窓が無い件には出しません）。
        #   窓が2つ（写真とPDF）ある件では、どちらを開くのかが分かるように
        #   名前を分けます。いまは そんな件はありませんが、来ても迷いません。
        futatsu = bool(mado) and bool(sh)
        zen = ''
        if mado:
            zen += ZEN_B.format(doko='hiro', na='写真を大きく' if futatsu else '大きく見る')
        if sh:
            zen += ZEN_B.format(doko='shiryo', na='資料を大きく' if futatsu else '大きく見る')
        more = BFUDA_MORE.format(body=md_html(a['rest'])) if a['rest'].strip() else ''
        meta = '・'.join(x for x in (esc_html(a['scene']), esc_html(a['grade']),
                                     ja_md(a['d'])) if x)
        # ── この実践を画像で保存（2026-09-22 夜。依頼で差しかえ）────────
        #   前は「LINEで聞く」でした。押すとLINEが開いて、題とURLが本文に
        #   入った状態で送り先を選ぶ、というものです。
        #   やめた理由 … 送れるのは**字だけ**でした。板書の写真も、書いて
        #   いただいた中身も、受けとった人は押さないと読めません。
        #   かわりに **1枚の画像**にします。開かなくても、その1枚で実践が
        #   ぜんぶ分かります。あとはその画像を、好きな所へ送れます。
        #   ★画像は、押した人のブラウザの中で作ります。何も出ていきません。
        #   ★画像の中に、この実践のURLを必ず入れます。見た人がここへ来られます。
        ima = SITE_URL + 'bansho.html#b-' + a['slug']
        fuda.append(BFUDA.format(
            slug=a['slug'], nid=a['naiyo'], naiyo=esc_html(naiyo_ja(a['naiyo'])),
            toki=a['todoita'].strftime('%Y%m%d%H%M'),
            nen=' '.join(nen_bunkai(a['grade'])),
            nushi=(' data-nushi="%s"' % a['nushi']) if a.get('nushi') else '',
            # ── なおすとき、フォームに戻すための「もとの字」（2026-09-22 夜）──
            #   画面に出ている字から拾い直すと、太字などの印が消えます。
            #   届いたままの字をここに持たせて、そのまま欄へ戻します。
            dai=esc_html(a['title']), grade=esc_html(a['grade']),
            scene=esc_html(a['scene']), oshi_nama=esc_html(a.get('oshi') or ''),
            hon_nama=esc_html(a['summary'].strip()),
            # 「推しポイント」と、字でも名のります（2026-09-23 依頼）。
            #   緑の縦線だけでは、何の1行なのかが伝わりませんでした。
            oshi=('        <p class="bfuda-oshi">'
                  '<span class="bfuda-oshi-l">推しポイント</span>%s</p>\n'
                  % inline_md(a['oshi'])
                  if a.get('oshi') else ''),
            kindtag=('<span class="fuda-kind">議題</span>'
                     if a['kind'] == 'gidai' else ''),
            # 地域（2026-09-22 依頼）。書かれたときだけ出します。
            #   ここは字なので、上の「さがす」欄で「徳島」と打てば当たります
            #   （さがすは、札の字ぜんぶを見ています）。
            chiiki=('<span class="bfuda-chi">%s</span>' % esc_html(a['chiiki'])
                    if a.get('chiiki') else ''),
            ken=esc_html(a.get('ken') or ''), shi=esc_html(a.get('shi') or ''),
            chiho=esc_html(a.get('chiho') or ''),
            meta=meta, title=esc_html(a['title']), lead=inline_md(a['lead']),
            mado=mado, shiryo=sh, zen=zen, more=more, by=esc_html(sensei_ja(a['by'])),
            ICON_KAMI=ICON_KAMI, ICON_GA=ICON_GA,
            ima=esc_html(ima)))
    return (JIBUN_TANA + '\n' + sagasu_obi(aru)
            + '\n    <div class="bantana" id="bantana">\n'
            + '\n'.join(fuda) + '\n    </div>')


def build_kanri_list(jissen):
    """管理画面の一覧。ここに入るのは、すでに公開ページに出ている字だけ。
       編集の権限はこのHTMLではなく、Apps ScriptのKANRI_KEYが決める。"""
    out = []
    for a in bansho_aru(jissen):
        # by は公開ページ用の1行だが、管理画面では名前と所属を
        # 別々になおす。既存データは「名前（所属）」から一度だけ分ける。
        by = (a.get('by') or '').strip()
        na, sh, ko = '', '', False
        if by and by != '送ってくださった先生':
            k = re.match(r'^(.*?)（([^()]*)）$', by)
            if k:
                na, sh = k.group(1).strip(), k.group(2).strip()
            else:
                na = by
            ko = True
        scene_key = {
            '学級活動(1)': 'gakkyu1', '学級活動(2)': 'gakkyu2',
            '学級活動(3)': 'gakkyu3', '学校行事': 'gyoji',
            '児童会活動': 'jidokai', 'クラブ活動': 'club',
        }.get(a['scene'], '')
        d = {
            'v': a['slug'], 't': a['title'], 'o': a.get('oshi') or '',
            'm': a['summary'].strip(), 'g': a['grade'], 's': a['scene'],
            'n': scene_key, 'na': na, 'sh': sh, 'ko': ko, 'by': a['by'],
            # 地域（2026-09-22）。ken は都道府県、shk は自治体。
            #   sh は「所属」で先に使っているので、名前を分けています。
            'ken': a.get('ken') or '', 'shk': a.get('shi') or '',
        }
        sagasu = ' '.join((a['title'], a['summary'], a['grade'], a['scene'], a['by'],
                           a.get('chiiki') or ''))
        meta = '・'.join(x for x in (a.get('chiiki') or '', a['scene'], a['grade'],
                                     ja_md(a['d']), '実践者：' + sensei_ja(a['by'])) if x)
        out.append(
            '      <article class="kanri-card" data-v="%s" data-date="%s" data-sagasu="%s">\n'
            '        <div><h3>%s</h3><p data-kanri-meta>%s</p>'
            # 管理人だけのメモ（2026-09-22）。公開ページには出ません。
            #   中身は受け口の覚え書きにあるので、ここは入れ物だけ置きます。
            '<p class="kanri-memo-p" data-memo-p hidden></p></div>\n'
            '        <div class="kanri-card-te">'
            '<button type="button" class="kanri-memo-b" data-memo data-title="%s">メモ</button>'
            '<button type="button" class="jibun-naosu" data-naosu="%s">なおす</button>'
            '<button type="button" class="kanri-kesu" data-kesu data-title="%s">消す</button>'
            '</div>\n'
            '      </article>'
            % (esc_html(a['slug']), esc_html(ja_md(a['d'])), esc_html(sagasu),
               esc_html(a['title']), esc_html(meta),
               esc_html(a['title']),
               esc_html(json.dumps(d, ensure_ascii=False, separators=(',', ':'))),
               esc_html(a['title'])))
    return '\n'.join(out) if out else '      <p class="karappo">届いた実践はまだありません。</p>'


# ══ 管理画面の「かたより」（2026-09-22 依頼）════════════════
#   届いた実践を、学習指導要領の6つ × 学年 のますめに置きます。
#
#   ★これは成績表ではありません。**空いているますが、そのまま発見**です。
#     「学級活動(2)が1件も来ない」「クラブ活動が誰からも出てこない」は、
#     この界隈で何が語られていないかを示しています。
#
#   ★数えるのは **届いたぶんだけ**です。サイトが自分で書いた見本を混ぜると、
#     「誰が語っていないか」が見えなくなります。
#
#   ★scene は「学級活動(1)ア」「学級活動(1)・計画委員会」のように
#     後ろが伸びることがあるので、**頭の一致**で6つに寄せます。

KATAYORI_NAIYO = ('学級活動(1)', '学級活動(2)', '学級活動(3)',
                  '学校行事', '児童会活動', 'クラブ活動')
KATAYORI_NEN = ('1年', '2年', '3年', '4年', '5年', '6年', '中学校', '全学年')


def _katayori_naiyo(scene):
    """scene を6つのどれかに寄せる。当たらなければ None。"""
    s = (scene or '').strip()
    for na in KATAYORI_NAIYO:
        if s.startswith(na):
            return na
    return None


def build_katayori(jissen):
    todoita = bansho_aru(jissen)
    hoka = len(jissen) - len(todoita)

    masu = {na: {nen: 0 for nen in KATAYORI_NEN + ('なし',)}
            for na in KATAYORI_NAIYO}
    yoso = 0          # 6つに寄せられなかったもの
    for a in todoita:
        na = _katayori_naiyo(a.get('scene'))
        if not na:
            yoso += 1
            continue
        g = a.get('grade') or ''
        atta = [nen for nen in KATAYORI_NEN if nen in g]
        # 「1年」は「11年」には出てきません。ここは素直な含みで足ります。
        for nen in (atta or ['なし']):
            masu[na][nen] += 1

    kei = {na: sum(masu[na].values()) for na in KATAYORI_NAIYO}
    kara = [na for na in KATAYORI_NAIYO if kei[na] == 0]

    out = ['      <div class="kata-hyo"><table>',
           '        <thead><tr><th>内容</th>'
           + ''.join('<th>%s</th>' % esc_html(n) for n in KATAYORI_NEN)
           + '<th>なし</th><th>計</th></tr></thead>',
           '        <tbody>']
    for na in KATAYORI_NAIYO:
        tds = ''.join(
            '<td>%s</td>' % (masu[na][n] if masu[na][n]
                             else '<span class="zero">·</span>')
            for n in KATAYORI_NEN + ('なし',))
        out.append('          <tr%s><th>%s</th>%s<td><b>%d</b></td></tr>'
                   % (' class="kata-kara"' if kei[na] == 0 else '',
                      esc_html(na), tds, kei[na]))
    out.append('        </tbody></table></div>')

    if kara:
        out.append('      <p class="kata-yomi kata-yomi--kara">'
                   '<b>まだ1件も届いていない内容：%s</b><br>'
                   'ここが、いまの空白です。</p>'
                   % esc_html('・'.join(kara)))
    else:
        out.append('      <p class="kata-yomi">6つとも、1件以上 届いています。</p>')

    shita = ['届いた実践 %d件を数えました。' % len(todoita)]
    if hoka:
        shita.append('サイトが自分で書いているぶん（%d件）は数えていません。' % hoka)
    if yoso:
        shita.append('6つのどれにも寄らなかったものが %d件あります。' % yoso)
    shita.append('学年は いくつでも押せるので、'
                 '1件が何年かのますに重なって入ります（計は のべの数です）。')
    out.append('      <p class="kata-yomi">%s</p>' % esc_html('　'.join(shita)))
    return '\n'.join(out)


# ══ 管理画面の「実践のほか」（2026-09-22 依頼）════════════
#   困りごとと 研究日程は、送られたら そのまま公開ページに出ます。
#   ところが 2026-09-22 まで、下ろす道は**知らせメールのリンク1本だけ**
#   でした。メールを見失うと、もう触れません。ここに一覧を出します。
#
#   ★消す仕組みは、実践と同じものを使い回します。
#     .kanri-card に data-v（slug）が付いていれば、kanri.html の
#     いまの［消す］がそのまま動きます。新しい道は作りません。
#   ★「出していないもの」も並べます。NGワードや書き方で止まった1件は、
#     いままでビルドの記録にしか出ず、誰の目にも触れませんでした。
#     こちらは消せません（公開に出ていないので、消すものがありません）。

KANRI_HOKA_T = """      <article class="kanri-card" data-v="{v}" data-sagasu="{sagasu}">
        <div><h3>{dai}</h3><p data-kanri-meta>{meta}</p></div>
        <div class="kanri-card-te"><button type="button" class="kanri-kesu" \
data-kesu data-title="{dai}" data-nani="{nani}">消す</button></div>
      </article>"""


def build_kanri_hoka(komari, ken, tobashita):
    """困りごと・送られた研究日程・出していないもの の3つ。"""
    out = []

    out.append('      <h3 class="kanri-hoka-h">困りごと'
               '<span>%d件</span></h3>' % len(komari))
    if komari:
        for a in komari:
            meta = '・'.join(x for x in (ja_md(a['d']), a.get('grade') or '') if x)
            out.append(KANRI_HOKA_T.format(
                v=esc_html(a['slug']), dai=esc_html(a['mijikai']),
                meta=esc_html(meta), nani='困りごと',
                sagasu=esc_html(' '.join((a['mijikai'], a['hon'], a.get('grade') or '')))))
    else:
        out.append('      <p class="karappo">届いた困りごとはまだありません。</p>')

    # こよみは1件の .md から「当日」と「申込〆切」を別々の行に開きます。
    #   ここは **ファイル1つ＝1枚** に畳みます（消すのはファイルなので、
    #   同じ slug が2枚ならんでいると、どちらを押しても同じものが消えます）。
    okuri = []
    mita = {}
    for a in ken:
        if not a.get('okuri'):
            continue
        k = a['slug']
        if k not in mita:
            mita[k] = dict(a, hi=[])
            okuri.append(mita[k])
        mita[k]['hi'].append('%s（%s）' % (ja_md(a['d']), a['shurui']))
    out.append('      <h3 class="kanri-hoka-h">サイトから送られた研究日程'
               '<span>%d件</span></h3>' % len(okuri))
    if okuri:
        for a in okuri:
            meta = '・'.join(x for x in ('／'.join(a['hi']), a.get('basho') or '',
                                         a.get('org') or '') if x)
            out.append(KANRI_HOKA_T.format(
                v=esc_html(a['slug']), dai=esc_html(a['ja']),
                meta=esc_html(meta), nani='研究日程',
                sagasu=esc_html(' '.join((a['ja'], a.get('naka') or '',
                                          a.get('basho') or '')))))
    else:
        out.append('      <p class="karappo">サイトから送られた日程は、まだありません。'
                   '<br>（こちらで手で書いたぶんは、ここには出ません）</p>')

    out.append('      <h3 class="kanri-hoka-h">届いたけれど、出していないもの'
               '<span>%d件</span></h3>' % len(tobashita))
    if tobashita:
        out.append('      <ul class="kanri-tobashi">')
        for t in tobashita:
            out.append('        <li>%s</li>' % esc_html(t))
        out.append('      </ul>')
        out.append('      <p class="kanri-hoka-yo">これは公開ページに出ていません。'
                   'だから、ここからは消せません。<br>'
                   '中身を直して出すなら、GitHub の src/komari・src/nittei で '
                   'その .md をなおしてください。</p>')
    else:
        out.append('      <p class="karappo">止まったものはありません。</p>')

    return '\n'.join(out)


# ══ storage.js を、いまのビルドにも入れる（2026-09-23 依頼）════
#   9月21日にページを7枚へ組み直したとき、storage.js は古い body.html の
#   経路にしか繋がっておらず、**1バイトも入っていませんでした**。
#   だから ⭐ストックも、読む人のメモも、動いていませんでした。
#   ここで繋ぎ直します。保存を触るのは、これまでどおり storage.js だけです。
STORAGE_ME = '/*BUILD:STORAGE*/'


def storage_ireru(body, doko):
    if STORAGE_ME not in body:
        raise Tomeru('%s に %s がありません（⭐ストックの保存が入りません）'
                     % (doko, STORAGE_ME))
    return body.replace(
        STORAGE_ME,
        '/* ══ storage.js を取りこみ（保存はここだけ。'
        '差しかえるときはこのブロックごと） ══ */\n' + rd('src/storage.js'))


NURU_ME = '/*BUILD:NURU*/'


def nuru_js(doko):
    """塗る面（src/nuru.js）。**送る画面と管理画面の両方**に、同じものを
       入れます。隠す道具が2つに分かれると、いつか片方だけ直って、
       もう片方から漏れます。"""
    return rd('src/nuru.js')


def nuru_ireru(body, doko):
    if NURU_ME not in body:
        raise Tomeru('%s に目じるし %s がありません（塗る面が入りません）'
                     % (doko, NURU_ME))
    return body.replace(NURU_ME, nuru_js(doko))


def build_kanri_page(jissen, komari, ken, tobashita):
    """帯には出さない管理専用ページ。入り口と更新時の2回、受け口で鍵を確かめる。"""
    body = rd('src/kanri.html')
    body = body.replace('          <!--BUILD:KEN-->', build_ken_options())
    body = body.replace('      <!--BUILD:KANRI_LIST-->', build_kanri_list(jissen))
    body = body.replace('      <!--BUILD:KANRI_HOKA-->',
                        build_kanri_hoka(komari, ken, tobashita))
    body = body.replace('      <!--BUILD:KATAYORI-->', build_katayori(jissen))
    body = body.replace('{{OKURU_URL}}', OKURU_URL)
    body = nuru_ireru(body, 'src/kanri.html')
    if re.findall(r'<!--BUILD:[^>]*-->|\{\{[A-Z_]+\}\}', body):
        raise Tomeru('管理画面に差しこまれていない目じるしが残っています')
    head = rd('src/head-hiroba.html')
    head = head.replace('<!--BUILD:ROBOTS-->', robots_tag('kanri.html'))
    head = head.replace('<title>TOKKATSU広場</title>', '<title>実践の管理｜TOKKATSU広場</title>')
    head = re.sub(r'<meta property="og:[^>]+>\n?', '', head)
    return '\n'.join([
        '<!DOCTYPE html>', '<html lang="ja" dir="ltr">', '<head>', head,
        '<style>', rd(CSS_H), '</style>', '</head>', '<body>', body, '</body>', '</html>',
    ])


# ══ 自分が送ったもの（2026-09-22 夜 依頼）════════════════════
#   ログインが無いので、こちらは「誰が誰か」を1つも持っていません。
#   だから **送った人のブラウザに聞きます**。
#   送るときに作った合いことばが、その端末の中に残っています。
#   その合いことばのハッシュと、札に付いている data-nushi を突き合わせて、
#   合ったものだけを ここに並べます。
#   ★この棚は、空のときは出しません（JavaScriptが外します）。
#   ★見えるのは、その端末の人だけです。ほかの人の画面には出ません。
JIBUN_TANA = """    <section class="jibun" id="jibun" hidden aria-labelledby="jibun-h">
      <h3 class="jibun-h" id="jibun-h">あなたが送ったもの</h3>
      <p class="jibun-yo">この端末から送ったものだけが出ています。ほかの人には見えません。</p>
      <ul class="jibun-l" id="jibun-l"></ul>
    </section>"""


# ══ 絞りこみ・並べかえ・さがす（2026-09-22 夜 依頼）════════════
#   届いたものが増えるほど、上から順に見るのが しんどくなります。
#   ★押すところは、サイトのほかの札（学年・内容）と同じ形にそろえます。
#   ★どれが効いているかは、色だけでなく **ベタ塗り（形）** でも分かります。
#   ★字を1つも書かなくても使えます（押すだけで絞れる）。
#   ★JavaScript が動かない人には、この帯を出しません（→ 下の hidden）。
#     押しても何も起きない押しボタンを、画面に置かないためです。
def chizu_michi(ten, hako=None):
    """点を、なめらかな閉じた線（SVGのd）に直す。

       かどを丸めるのに Catmull-Rom を ベジエに直しています。
       点をそのまま線でつなぐと、海岸線がカクカクして
       「四角を並べた地図」に見えてしまうためです。
    """
    p = [chizu_ten(lo, la) for lo, la in ten]
    if hako:
        # 別枠（沖縄）のときは、その枠の中に収めなおします
        x0, y0, w, h = hako
        xs = [q[0] for q in p]; ys = [q[1] for q in p]
        hx, hy = max(xs) - min(xs), max(ys) - min(ys)
        r = min((w - 34) / max(hx, .001), (h - 34) / max(hy, .001))
        ox = x0 + (w - hx * r) / 2 - min(xs) * r
        oy = y0 + (h - hy * r) / 2 - min(ys) * r
        p = [(q[0] * r + ox, q[1] * r + oy) for q in p]
    n = len(p)
    d = ['M%.1f %.1f' % p[0]]
    for i in range(n):
        p0, p1, p2, p3 = p[(i - 1) % n], p[i], p[(i + 1) % n], p[(i + 2) % n]
        d.append('C%.1f %.1f %.1f %.1f %.1f %.1f' % (
            p1[0] + (p2[0] - p0[0]) / 6.0, p1[1] + (p2[1] - p0[1]) / 6.0,
            p2[0] - (p3[0] - p1[0]) / 6.0, p2[1] - (p3[1] - p1[1]) / 6.0,
            p2[0], p2[1]))
    return ' '.join(d) + 'Z'


def chizu_mijikaku(ken):
    """札の中の字。「県」「府」を落として短くします。北海道はそのまま。"""
    return ken if ken == '北海道' else ken[:-1]


# ★ id は外から渡します。同じ id が2つあると、リンクが別の場所へ飛ぶので
#   ビルドが止まります（実践の地図と、研究会の地図の2つを置くため）。
CHIZU_T = """      <div class="sagasu-gyo sagasu-gyo--chizu">
        <span class="sagasu-l" id="{mid}-l">地図から</span>
        <p class="chizu-yomi">{yomi}
          <span class="chizu-nashi-chu">{nashi}</span></p>
        <div class="chizu" id="{mid}" role="group" aria-labelledby="{mid}-l">
{e}
{fuda}        </div>
      </div>
"""

CHIZU_YOMI = ('押すと、その県のものだけになります。もう一度押すと もどります。<br>\n'
              '          <b>札が立っているのが、いま届いている県です。</b>札の無い県は\n'
              '          「そこに実践が無い」のではなく、<b>まだ送られていないだけ</b>です。')


def build_chizu(aru, mid='sagasu-k', yomi=None, nashi=None):
    """日本の地図（2026-09-22 依頼）。押すと、その県のものだけになります。

       mid  … 地図の id。2つ置くので、外から渡します（id が重なると止まります）
       yomi … 上に出す説明。渡さなければ 実践むけの字
       nashi… 「のこり◯県」の1行。渡さなければ 実践むけの字

       ★絵は、経度・緯度から組み立てます。画像は1枚も使いません。
         外の地図サービスも使いません（開いただけで通信が飛ぶため。原則2）。
       ★押すのは、絵の上に重ねた **HTMLのボタン**です。
         絵そのものを押させると、香川県が指より小さくなって押せません。
         ボタンなら、キーボードでも読み上げでも たどれます。
       ★件数は札の中に **数で** 出します。色の濃さだけで伝えると、
         色の見え方がちがう人に届きません。
       ★1件も地域が書かれていないときは、地図ごと出しません。
         札が1枚も立っていない地図は、何も言っていないのと同じです。
    """
    kazu = {}
    for a in aru:
        k = a.get('ken')
        if k:
            kazu[k] = kazu.get(k, 0) + 1
    if not kazu:
        return ''
    ooi = max(kazu.values())

    # ── 絵（海・島・沖縄の別枠）────────────────────────
    e = ['          <svg class="chizu-e" viewBox="0 0 %g %g" aria-hidden="true" '
         'focusable="false" preserveAspectRatio="xMidYMid meet">'
         % (CHIZU_W, CHIZU_H),
         '            <rect class="chizu-umi" x="0" y="0" width="%g" height="%g" rx="16"/>'
         % (CHIZU_W, CHIZU_H)]
    for na, ten in CHIZU_SHIMA.items():
        # ★<path> の中に <title> を入れないこと。build.py は path を
        #   「閉じない札」として数えているので、閉じ札があると
        #   「節の中の入れ子が合っていません」で止まります（実測で踏みました）。
        #   絵そのものは aria-hidden なので、名前は要りません。
        e.append('            <path class="chizu-shima" data-shima="%s" d="%s"/>'
                 % (esc_html(na), chizu_michi(ten)))
    ox, oy, ow, oh = CHIZU_OKI_WAKU
    e.append('            <rect class="chizu-waku" x="%g" y="%g" width="%g" height="%g" rx="12"/>'
             % (ox, oy, ow, oh))
    e.append('            <path class="chizu-shima" d="%s"/>' % chizu_michi(CHIZU_OKI, CHIZU_OKI_WAKU))
    e.append('            <text class="chizu-waku-ji" x="%g" y="%g">沖縄</text>'
             % (ox + 9, oy + 18))
    e.append('          </svg>')

    # ── 札（押せるのは、届いている県だけ）──────────────
    #   札を県の真上に置くと、小さい県（四国・香川あたり）が
    #   札の下に 完全に隠れます（実測で踏みました）。
    #   だから **印は県の上、札は少し外へ逃がして、細い線でつなぎます**。
    #   逃がす向きは「日本のまん中から見て、外がわ」。だいたい海へ出ます。
    MANNAKA = (200.0, 300.0)      # 地図の中の、だいたいの まん中
    NIGASU = 52.0                 # 札を逃がす長さ

    def ichi(ken):
        if ken == '沖縄県':
            return ox + ow / 2, oy + oh * 0.62
        return chizu_ten(*KEN_ICHI[ken])

    tate = []
    for ken in sorted(kazu, key=lambda k: (ichi(k)[1], ichi(k)[0])):
        x, y = ichi(ken)
        dx, dy = x - MANNAKA[0], y - MANNAKA[1]
        nagasa = (dx * dx + dy * dy) ** 0.5 or 1.0
        lx, ly = x + dx / nagasa * NIGASU, y + dy / nagasa * NIGASU
        # 枠から はみ出さないように、内がわへ戻します
        lx = min(max(lx, 46.0), CHIZU_W - 46.0)
        ly = min(max(ly, 18.0), CHIZU_H - 18.0)
        # 前に置いた札と近すぎたら、下へ逃がします
        for _ in range(40):
            if all(abs(lx - px) > 74 or abs(ly - py) > 26 for px, py, _ in tate):
                break
            ly += 14
        tate.append((lx, ly, (ken, x, y)))

    hiku, fuda = [], []
    for lx, ly, (ken, x, y) in tate:
        n = kazu[ken]
        koi = (1 + min(3, int(3.0 * (n - 1) / max(1, ooi - 1)))) if ooi > 1 else 4
        hiku.append('            <line class="chizu-sen" x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f"/>'
                    % (x, y, lx, ly))
        hiku.append('            <circle class="chizu-ten" cx="%.1f" cy="%.1f" r="5"/>' % (x, y))
        fuda.append(
            '          <button type="button" class="chizu-f" data-ken="%s" data-koi="%d" '
            'aria-pressed="false" style="--x:%.3f%%;--y:%.3f%%" '
            'aria-label="%s %d件。押すと、この県のものだけになります">'
            '<span class="chizu-na">%s</span><span class="chizu-n">%d</span></button>\n'
            % (esc_html(ken), koi, lx / CHIZU_W * 100, ly / CHIZU_H * 100,
               esc_html(ken), n, esc_html(chizu_mijikaku(ken)), n))
    e[-1:-1] = hiku      # 引き出し線と印は、島の上・札の下に入れます

    nokori = 47 - len(kazu)
    if nashi is None:
        nashi = ('いまは %d県から %d件。のこり %d県には、まだ札が立っていません。'
                 % (len(kazu), sum(kazu.values()), nokori)) if nokori else \
                'とうとう47都道府県、ぜんぶそろいました。'
    else:
        nashi = nashi % {'ken': len(kazu), 'kazu': sum(kazu.values()), 'nokori': nokori}
    return CHIZU_T.format(e='\n'.join(e), fuda=''.join(fuda), mid=mid,
                          yomi=(yomi or CHIZU_YOMI), nashi=esc_html(nashi))


# 2026-09-23 依頼：**左に地図、右にさがす**の2段組みにします。
#   地図が上にあると、スマホで内容・学年の札まで1画面ぶん遠くなります。
#   ★書く順は「さがす → 地図」です。スマホではこの順に上から並びます
#     （字で絞るほうが速いので、そちらを先に出します）。
#     広い画面だけ、CSSが地図を左の列へ動かします。
#   ★地域が1件も書かれていないときは地図が空なので、
#     そのときは2段組みにしません（build_sagasu_obi が分けます）。
SAGASU_OBI = """    <div class="sagasu{futatsu}" id="sagasu" hidden>
      <div class="sagasu-migi">
      <div class="sagasu-gyo">
        <label class="sagasu-l" for="sagasu-ji">さがす</label>
        <input class="sagasu-i" type="search" id="sagasu-ji" autocomplete="off"
               placeholder="題・中身・学年・実践者から（例：たてわり）">
      </div>
      <div class="sagasu-gyo">
        <span class="sagasu-l" id="sagasu-n-l">内容</span>
        <div class="okuru-nen" role="group" aria-labelledby="sagasu-n-l" id="sagasu-n">
          <button type="button" class="okuru-nen-b" data-n="" aria-pressed="true">ぜんぶ</button>
{naiyo}        </div>
      </div>
      <div class="sagasu-gyo" id="sagasu-g-gyo">
        <span class="sagasu-l" id="sagasu-g-l">学年</span>
        <div class="okuru-nen" role="group" aria-labelledby="sagasu-g-l" id="sagasu-g">
          <button type="button" class="okuru-nen-b" data-g="" aria-pressed="true">ぜんぶ</button>
{nen}        </div>
      </div>
      <div class="sagasu-gyo">
        <span class="sagasu-l" id="sagasu-j-l">並び</span>
        <div class="okuru-nen" role="group" aria-labelledby="sagasu-j-l" id="sagasu-j">
          <button type="button" class="okuru-nen-b" data-j="atarashii" aria-pressed="true">新しい順</button>
          <button type="button" class="okuru-nen-b" data-j="furui" aria-pressed="false">古い順</button>
        </div>
      </div>
      <p class="sagasu-kazu" id="sagasu-kazu" role="status" aria-live="polite"></p>
      </div>
      <div class="sagasu-hidari">
{chizu}      </div>
    </div>"""


NEN_FUDA = [('1', '1年'), ('2', '2年'), ('3', '3年'), ('4', '4年'),
            ('5', '5年'), ('6', '6年'), ('chu', '中学校')]


def nen_bunkai(grade):
    """学年の字を、1年ずつの印にほどく。

       送られてくる字は1つに決まっていません。フォームからは「5年・6年」、
       古いものは「5〜6年」、こちらで用意した道具は「全学年」です。
       字のまま比べると、5年をさがしている人に「5〜6年」が当たりません。
       だから **1年ずつにほどいてから** 比べます。
           全学年      → 1 2 3 4 5 6
           5〜6年      → 5 6
           5年・6年    → 5 6
           中学校      → chu
       どれにも当たらなければ、空（＝学年の札では絞りこめない1件）。"""
    g = (grade or '').strip()
    if not g:
        return []
    out = set()
    if '全学年' in g:
        out |= set('123456')
    for a, b in re.findall(r'([1-6１-６])\s*[〜～~\-]\s*([1-6１-６])', g):
        a, b = int(han(a)), int(han(b))
        for i in range(min(a, b), max(a, b) + 1):
            out.add(str(i))
    for a in re.findall(r'([1-6１-６])\s*年', g):
        out.add(han(a))
    if '中学' in g:
        out.add('chu')
    return [k for k, _ in NEN_FUDA if k in out]


def han(c):
    """１ → 1。全角で書かれていても、同じ学年として数えます。"""
    return chr(ord(c) - 0xFEE0) if '１' <= c <= '６' else c


def build_ken_options():
    """実践を送るフォームの「都道府県」の中身（2026-09-22 依頼）。

       47を手で2か所に書くと、いつか片方だけ直ります。
       出どころは CHIHO の1か所だけにして、ここから吐きます。
       地方ごとに <optgroup> で束ねるので、スマホのプルダウンでも
       北から南に並んで、自分の県をさがしやすくなります。
       ★管理画面（src/kanri.html）の「なおす」にも、同じものを入れます。
    """
    gyo = []
    for ch, kens in CHIHO:
        gyo.append('          <optgroup label="%s">' % esc_html(ch))
        for k in kens:
            gyo.append('            <option value="%s">%s</option>' % (esc_html(k), esc_html(k)))
        gyo.append('          </optgroup>')
    return '\n'.join(gyo)


def sagasu_obi(aru):
    """内容の札は、**いま届いているものにある内容だけ**出します。
       1件も無い内容の札を出すと、押したとたんに0件になるためです。"""
    aru_n = [n for n in aru]
    gyo = []
    for nid, ja in naiyo_ichiran():
        kazu = sum(1 for a in aru_n if a['naiyo'] == nid)
        if not kazu:
            continue
        gyo.append('          <button type="button" class="okuru-nen-b" data-n="%s" '
                   'aria-pressed="false">%s<span class="sagasu-b-kazu">%d</span></button>\n'
                   % (nid, esc_html(ja), kazu))
    nen = []
    for k, ja in NEN_FUDA:
        kazu = sum(1 for a in aru_n if k in nen_bunkai(a['grade']))
        if not kazu:
            continue
        nen.append('          <button type="button" class="okuru-nen-b" data-g="%s" '
                   'aria-pressed="false">%s<span class="sagasu-b-kazu">%d</span></button>\n'
                   % (k, esc_html(ja), kazu))
    chizu = build_chizu(aru)
    return SAGASU_OBI.format(naiyo=''.join(gyo), nen=''.join(nen), chizu=chizu,
                             futatsu=' sagasu--futatsu' if chizu else '')


def build_bansho_iriguchi(jissen):
    """「学ぶ」の実践の節に置く、板書のページへの入口。
       0件のときはリンクにしません（押しても何も無い、を作らないため）。"""
    n = len(bansho_aru(jissen))
    if not n:
        return ('    <p class="bansho-iri bansho-iri--mada">'
                '<b>みんなの実践</b>まだ1件もありません。届いたぶんから、そちらに溜めていきます。</p>')
    mai = sum(bansho_kazu(a['bansho']) for a in bansho_aru(jissen))
    return ('    <p class="bansho-iri"><a class="bansho-b bansho-b--ookii" href="#bansho">'
            'みんなの実践を見る（%d件・%d枚）<i>→</i></a></p>' % (n, mai))


def build_komari_miru(komari):
    """困りごとを送る欄の、すぐ下に置く「見るところ」（2026-09-22）。
       0件のときはリンクにしません（押しても何も無い、を作らないため）。"""
    if not komari:
        return ('    <p class="bansho-iri bansho-iri--mada">'
                '<b>届いている困りごと</b>まだ1件もありません。いちばん乗りをどうぞ。</p>')
    tsuita = sum(1 for a in komari if a['saki'])
    return ('    <p class="bansho-iri"><a class="bansho-b bansho-b--ookii" href="#komari">'
            '届いている困りごとを見る（%d件・うち%d件に答え）<i>→</i></a></p>'
            % (len(komari), tsuita))


def build_okuru_miru(jissen):
    """送るところの、すぐ下に置く「見るところ」（2026-09-22 依頼）。
       送る人は、まず人のを見たい。離れていると往復できません。
       0件のときはリンクにしません（押しても何も無い、を作らないため）。"""
    n = len(bansho_aru(jissen))
    if not n:
        return ('    <p class="bansho-iri bansho-iri--mada">'
                '<b>送られた実践</b>まだ1件もありません。いちばん乗りをどうぞ。</p>')
    mai = sum(bansho_kazu(a['bansho']) for a in bansho_aru(jissen))
    return ('    <p class="bansho-iri"><a class="bansho-b bansho-b--ookii" href="#bansho">'
            '送られた実践を見る（%d件・%d枚）<i>→</i></a></p>' % (n, mai))


NEWS_H_N = 5      # ニュースを、上から何件だけ出しておくか（のこりはふたの中）


def build_hyo_news(kiji):
    def gyo(a):
        # 行そのものは一次情報（外部）へ。そこは飛ばすのが正しいので「外部」と書きます
        return ('      <a href="%s" target="_blank" rel="noopener noreferrer">'
                '<span class="t">%s<span class="sub">%s</span></span>'
                '<span class="d">%s ・外部</span></a>'
                % (a['url'], esc_html(a.get('home') or a['title']),
                   esc_html(a['source']), ja_md(a['d'])))
    # いつまでのニュースが入っているか（2026-09-23 依頼）。
    #   ★出すのは「いちばん新しい記事の日」です。**組んだ日ではありません。**
    #     組んだ日を出すと、ほかの直しでビルドしただけで日が進み、
    #     中身が2か月古くても「今日更新」と出てしまいます。
    #   ★古いままなら、古いと分かるのが正しい出し方です。
    atarashii = ('      <p class="news-hi">いちばん新しいニュースは '
                 '<b>%s</b>。ぜんぶで %d件 あります。</p>\n'
                 % (esc_html(ja_md(kiji[0]['d'])), len(kiji))) if kiji else ''
    ue = (atarashii + '    <div class="hyo">\n'
          + '\n'.join(gyo(a) for a in kiji[:NEWS_H_N]) + '\n    </div>')
    nokori = kiji[NEWS_H_N:]
    naka = ('      <div class="hyo">\n'
            + '\n'.join(gyo(a) for a in nokori) + '\n      </div>') if nokori else ''
    return tsunagu(ue, naka, len(nokori))


# ── 節のまわりに立つ飾り（絵を1回だけ入れて、置きたい所で <use> する）──
KAZARI_RE = re.compile(r'<i class="kazari([^"]*)" data-([kb])="([a-z0-9\-]+)"([^>]*)></i>')


# ══ 節目のお祝い（2026-09-22）════════════════════════════════
#   溜まった実践が **ちょうど** 下の数になったときだけ、ホームの
#   「あなたの実践を、ここに」に お祝いが1つ出ます。
#   次の1件が届くと、ひとりでに消えます（だから見られると嬉しい）。
#
#   ★これは「閲覧数」ではありません。閲覧数を数えるには、開いた人の
#     端末から外へ1回送る必要があり、原則2（何も送信しない）に触れます。
#     ここで数えているのは、サイトの中にもう有るもの＝届いた件数です。
#     だから、読む人からは1バイトも出ません。
#
#   ★数を足すときは、下のタプルに入れるだけです。順番は問いません。
FUSHIME = (1, 5, 10, 20, 30, 50, 75, 100, 150, 200, 300, 500, 1000)


def build_fushime(jissen, buhin):
    """届いた実践が ちょうど節目の数のときだけ、お祝いを返す。ほかは空。"""
    n = len(bansho_aru(jissen))
    if n not in FUSHIME:
        return ''
    if 'bankokki' not in buhin:
        raise Tomeru('節目のお祝いが src/ill/buhin/bankokki.svg を呼んでいますが、'
                     'その絵がありません')
    w, h, _ = buhin['bankokki']
    dai = ('はじめの1件が、届きました。' if n == 1
           else '実践が、%d件になりました。' % n)
    return ('    <p class="fushime">\n'
            '      <span class="fushime-hata" aria-hidden="true">'
            '<svg viewBox="0 0 %g %g" focusable="false">'
            '<use href="#ill-b-bankokki"/></svg></span>\n'
            '      <b class="fushime-dai">%s</b>\n'
            '      <span class="fushime-yo">送ってくださった先生方、'
            'ありがとうございます。</span>\n'
            '    </p>' % (w, h, esc_html(dai)))


def build_kazari(body, buhin, kyara):
    tsukatta = set()

    def hen(m):
        cls, tane, name, nokori = m.groups()
        hako, atama, doko = ((kyara, 'ill-k-', 'src/ill/kyara') if tane == 'k'
                             else (buhin, 'ill-b-', 'src/ill/buhin'))
        if name not in hako:
            raise Tomeru('src/hiroba.html の飾りが %s/%s.svg を呼んでいますが、'
                         'その名前の絵がありません。いま置けるのは： %s'
                         % (doko, name, '、'.join(sorted(hako))))
        w, h, _ = hako[name]
        tsukatta.add((tane, name))
        return ('<i class="kazari%s"%s aria-hidden="true">'
                '<svg viewBox="0 0 %g %g" focusable="false"><use href="#%s%s"/></svg></i>'
                % (cls, nokori, w, h, atama, name))

    body = KAZARI_RE.sub(hen, body)
    nokori = re.findall(r'data-[kb]="[^"]*"', body)
    if nokori:
        raise Tomeru('飾りの書き方がちがいます（%s）。'
                     '<i class="kazari" data-k="名前" style="--y:…;--w:…px"></i> の形で書いてください'
                     % '、'.join(sorted(set(nokori))))
    return body, tsukatta


def kazari_defs(tsukatta, buhin, kyara, mark):
    """使った絵だけを、1回ずつ defs に入れる（同じ絵を何度置いても重さは増えません）。
       種は3つ … k＝キャラクター、b＝広場の部品、m＝札のしるし。"""
    g = []
    hakos = {'k': (kyara, 'ill-k-'), 'b': (buhin, 'ill-b-'), 'm': (mark, 'ill-m-')}
    for tane, name in sorted(tsukatta):
        hako, atama = hakos[tane]
        if name not in hako:
            raise Tomeru('#%s%s を呼んでいますが、その名前の絵がありません' % (atama, name))
        # data-vb … 画像保存のとき、この絵を1枚のSVGに組み直すために使います
        #   （<use> で出すときは外がわの viewBox で決まるので、絵そのものは
        #     大きさを持っていません。ここに書いておかないと 0×0 になります）
        g.append('<g id="%s%s" data-vb="0 0 %g %g">%s</g>'
                 % (atama, name, hako[name][0], hako[name][1], hako[name][2]))
    return ''.join(g)


# ── 4人ならび（ABOUT節。名前をここで読者に渡す）──
NARABI_T = """      <li class="hitori h--{n}">
        <span class="e"><svg viewBox="0 0 {w} {h}" aria-hidden="true" focusable="false"><use href="#ill-k-{n}"/></svg></span>
        <b>{na}</b><span class="yaku">{naiyo}</span>
        <span class="saki">{saki}</span>
      </li>"""


def build_kyara_narabi(kyara):
    return ('    <ul class="kyara">\n'
            + '\n'.join(NARABI_T.format(n=n, na=na, naiyo=naiyo,
                                        saki=KYARA_SAKI.get(n, ''),
                                        w=kyara[n][0], h=kyara[n][1])
                        for n, na, naiyo, _ in KYARA_MEN)
            + '\n    </ul>')


# ── このサイトは、なに（ホームのいちばん上）─────────────
#   LINEオープンチャット「みんなの特活ひろば（仮）」の案内に合わせた4行。
#   ポスターの「ちょっと聞きたい／知りたい／伝えたい」を、
#   4人に1つずつ持たせて、このサイトの行き先につなげています。
#   （id, 「ちょっと◯◯」, このサイトでできること, 行き先の節のid）
#   ★行き先は **節の id だけ** を書きます（page.html#id と書かないこと）。
#     節がどのページに移っても、tsunagi_naosu() が張りなおしてくれます。
#     2026-09-21 夜、「伝えたい」が atsumaru.html#okuru を指したまま
#     送るところがホームへ移り、行き先が消えかけました。
IGI_MEN = (
    ('gakkatsu', 'ちょっと聞きたい', 'いま困っていることを。',   'kiku'),
    ('gyoji',    'ちょっと知りたい', '研究日程とニュース。',     'ima'),
    ('club',     'ちょっと試したい', '週案に貼る1行つき。',     'jissen'),
    ('jidokai',  'ちょっと伝えたい', '板書も資料も、ここから。', 'okuru'),
)

IGI_T = """      <li class="igi-h h--{n}">
        <a class="igi-a" href="#{saki}">
          <span class="e"><svg viewBox="0 0 {w} {h}" aria-hidden="true" focusable="false"><use href="#ill-k-{asset}"/></svg></span>
          <b>{chotto}</b><span class="t">{dekiru}</span>
          <span class="igi-ya" aria-hidden="true">→</span>
        </a>
      </li>"""

IGI_T_NASHI = """      <li class="igi-h h--{n}">
        <span class="e"><svg viewBox="0 0 {w} {h}" aria-hidden="true" focusable="false"><use href="#ill-k-{asset}"/></svg></span>
        <b>{chotto}</b><span class="t">{dekiru}</span>
      </li>"""


def build_igi(kyara):
    """ホームのいちばん上。このサイトが何のためにあるかを、4人で短く渡します。"""
    men = []
    poses = {'gakkatsu': 'listen', 'gyoji': 'calendar', 'jidokai': 'share', 'club': 'try'}
    for n, chotto, dekiru, saki in IGI_MEN:
        if n not in kyara:
            raise Tomeru('意義の節が %s.svg を呼んでいますが、その絵がありません' % n)
        asset = n + '-' + poses[n]
        men.append((IGI_T if saki else IGI_T_NASHI).format(
            n=n, chotto=esc_html(chotto), dekiru=esc_html(dekiru),
            asset=asset, saki=saki, w=kyara[asset][0], h=kyara[asset][1]))
    return ('<section class="sec" id="igi">\n'
            '  <div class="uchi">\n'
            '    <h2 class="midashi"><span class="en">WHY</span>'
            '<span class="ja">このサイトは、なに</span></h2>\n'
            # 1文＝1行。<span> を1つずつ立てて、行の折れ目を文の切れ目に
            # そろえます（2026-09-22）。<br> だと、画面が狭いときに文の
            # 途中でも折れて「みんなの特／活ひろば」のように割れます。
            '    <div class="igi-intro"><p class="igi-bun">'
            '<span>日本の特別活動の<b>情報交流</b>を高めるためのサイトです。</span>'
            '<span>LINEオープンチャット<b>「みんなの特活ひろば（仮）」</b>と'
            '連携しています。</span>'
            '<span>あちらで話し、ここで<b>確かめて、持ち帰る</b>。</span>'
            '<span>そのためにお使いください。</span>'
            '</p><div class="igi-friends">'
            '<svg viewBox="0 0 345 143" aria-hidden="true" focusable="false">'
            '<use href="#ill-k-group-shoulders"/></svg>'
            # 4人の名前（2026-09-23 依頼）。絵の下に小さく置きます。
            #   ★並びは KYARA_MEN の順＝絵の左から右の順です
            #     （服の色が 緑・赤・青・黄 で、group-shoulders.svg と同じ並び）。
            #     KYARA_MEN を並べかえると、ここも一緒に動きます。
            #   ★絵のほうだけ aria-hidden にしました。名前は字なので、
            #     読み上げにも残します。
            '<p class="igi-na">'
            + ''.join('<span>%s</span>' % esc_html(na)
                      for _, na, _, _ in KYARA_MEN)
            + '</p></div></div>\n'
            '    <ul class="igi-l">\n' + '\n'.join(men) + '\n    </ul>\n'
            # ★ここは切り分けたあとに作るので、{{◯◯}} は置きかわりません。
            #   LINKS から直に入れます。
            '    <p class="igi-b"><a class="btn" href="' + LINKS['LINE_OC'] + '" '
            'target="_blank" rel="noopener noreferrer">'
            'みんなの特活ひろば（仮）へ</a></p>\n'
            '  </div>\n'
            '</section>')


# ══ ホーム（2026-09-21に新設）════════════════════════════
#   全部の項目を、短く・面白そうに1枚にまとめる入口。
#   数は、その場で数えたものだけを出します（手で書いた数は置きません。
#   足したのに数が古い、が起きないため）。
#   （節のid, 絵のたね, 絵の名前, 短い1行）
#   ★並び順は「行き先のページごと」にまとめてあります。
#     色も行き先ごとなので、同じ色がとなり合って見えます。
#     ばらばらに並べると、帯を2段にしたとき色が飛び飛びになります。
HOME_FUDA = (
    # ★並びは「明日すぐ使う順」。ページごとのまとまりより、使う順を先にします。
    #   板書を送る → 研究日程 → 学ぶ・実践 → ニュース・研究会 → 特活とは・4つの内容
    #   （2026-09-21。いちばん下の2つは「読みもの」なので、いちばん後ろ）
    #
    # 2026-09-23：札に出す絵を **人 → モノ** に入れかえました。
    #   8枚ぜんぶが人だったころは、絵を見ても何の札か分からず、
    #   けっきょく字を読むしかありませんでした（「ここが全部人になってしまった」）。
    #   いまは 研究日程＝カレンダー、日本の研究会＝日本の地図 のように、
    #   **その場所にあるモノ** を1つだけ出します。
    #   3つめの欄は、行き先の節の見出しに立つ人です（→ SETSU_KYARA）。
    #   （節のid, しるしの名前, 行き先で待つ人, 短い1行）
    # index（このページ自身）。板書を送るところが、いちばん上です
    ('okuru',  'okuru',  'jidokai-upload', '写真もPDFも、送るとそのまま出ます。'),
    # 送る の すぐ次が 見る。この2つで1組です（2026-09-22）
    ('bansho', 'bansho', 'jidokai-share', '先生方から届いた実践が、そのまま並びます。'),
    ('ima',    'nittei', 'gyoji-calendar', 'つぎの研究会と、申込の締切。'),
    # komari（困っている → 学ぶ、の順に並べます。2026-09-22）
    ('komari', 'komari', 'gakkatsu-listen', '送られた困りごとが、そのまま並びます。'),
    # manabu（すぐ使える道具は、この「学ぶ」と同じページにあります）
    ('manabu', 'hajime', 'club-tools', '①から⑤の学習過程と、一次資料と、道具。'),
    # atsumaru
    ('news',   'news',   'gyoji-news', '一次情報だけ。要約は、こちらの言葉で。'),
    ('kai',    'kai',    'jidokai-speak', '1つずつ開いて、いま見られるものだけ。'),
    # shiru（2026-09-22：特活とは と 4つの内容 は同じページなので、1つにまとめました。
    #        4つの内容は、この札から入った先にそのまま置いてあります）
    ('about',  'about',  'gakkatsu-board', '教科書がない時間の、見るところ。4つの内容も、ここに。'),
)

# 節の見出しに立つ人。ホームの札から入ってきた人を、行き先で迎えます。
#   ★出どころは HOME_FUDA の3つめの欄ひとつだけです。ここで書き写しません
#     （札の人と見出しの人がちがう、が起きないため）。
SETSU_KYARA = {sid: kao for sid, _, kao, _ in HOME_FUDA}

# 見出しの **反対がわ**（右）に立つ もう1人（2026-09-23 依頼）。
#   見出しは3列（空き｜見出し｜空き）でできていて、右の空きがずっと
#   から っぽでした。そこにもう1人入れます。**左右の列は同じ幅（1fr）**
#   なので、2人になっても見出しの太字はまん中のままです。
#   ★スマホでも出ます。まわりに立つ飾り（.kazari）は本文の欄の外に
#     置くので、せまい画面では消えます。ここは列の中なので消えません。
#   ★左と右で ちがう子にしています（同じ子が2人ならぶと、絵が1枚に見えます）。
#     困りごとだけは、同じ学活くんの「聞く → 考える」でそろえています。
SETSU_KYARA_MIGI = {
    'okuru':  'gakkatsu-welcome',   # 送りに来た人を迎える
    'bansho': 'club-cheer',         # 届いた実践に拍手
    'ima':    'jidokai-guide',      # 日にちを案内する
    'komari': 'gakkatsu-think',     # 聞いて（左）、考える（右）
    'manabu': 'gakkatsu-guide',     # 学習過程を指す
    'news':   'club-welcome',       # ニュースへ手まねき
    'kai':    'gyoji-welcome',      # 各地の会へ手まねき
    'about':  'club-try',           # やってみよう
}

HOME_T = """      <a class="hfuda p--{page}" href="{saki}">
        <span class="hfuda-e" aria-hidden="true"><svg viewBox="0 0 {w} {h}" focusable="false"><use href="#ill-m-{na}"/></svg></span>
        <b class="hfuda-h">{midashi}</b>
        <span class="hfuda-yo">{yo}</span>
        <span class="hfuda-kazu" data-en="{kazu_en}" data-ar="{kazu_ar}">{kazu}</span>
      </a>"""


def mitsu(ja, en, ar):
    """3つのことばを、1つにまとめて持ちまわるための入れもの。"""
    return (ja, en, ar)


def home_kazu(sid, sec, kiji, jissen, ken, komari):
    """札に出す数。その場で数えたものだけを出します。
       戻りは（日本語, English, العربية）の3つ。
       ★数は毎日変わるので、KOTOBA の表には置けません（置くと、1件届くたびに
         ビルドが止まります）。ここで3つのことばを一緒に作ります。"""
    def kazoe(pat):
        return len(re.findall(pat, sec.get(sid, '')))
    if sid == 'ima':
        return mitsu('%d件' % len(ken), '%d meetings' % len(ken), '%d لقاء' % len(ken))
    if sid == 'news':
        return mitsu('%d件' % len(kiji), '%d items' % len(kiji), '%d خبر' % len(kiji))
    if sid == 'about':
        n = kazoe(r'class="manabu-box"')
        return mitsu('話が%dつ' % n, '%d topics' % n, '%d موضوعات' % n)
    if sid == 'manabu':
        dan = kazoe(r'data-learn-detail=')
        shi = kazoe(r'<li><a href="https?://[^"]*"[^>]*><span><b>')
        return mitsu('%d段階と資料%d件' % (dan, shi),
                     '%d steps, %d sources' % (dan, shi),
                     '%d مراحل و%d مرجعًا' % (dan, shi))
    # 困りごとの数。2026-09-22 まで「4つの内容」の札に出していましたが、
    # 帯を1つにまとめたので、困りごとの札の数になりました。
    if sid in ('komari', 'yotsu'):
        n = len(komari)
        return mitsu('悩み%d件' % n, '%d questions' % n, '%d سؤال' % n)
    if sid == 'jissen':
        return mitsu('%d件' % len(jissen), '%d items' % len(jissen),
                     '%d عنصر' % len(jissen))
    if sid == 'kai':
        return mitsu('%d会' % len(KAI), '%d societies' % len(KAI),
                     '%d جمعية' % len(KAI))
    if sid == 'okuru':
        # 送るところの札には「いくつ届いたか」を出します。
        # （手順の数を出していましたが、手順の箇条書きをやめたので 0 になりました）
        n = len(bansho_aru(jissen))
        return mitsu('%d件とどいた' % n, '%d received' % n, 'وصل %d' % n)
    if sid == 'bansho':
        # みんなの実践。届いた件数と、その中の写真の枚数（2026-09-22）
        aru = bansho_aru(jissen)
        n = aru and len(aru) or 0
        mai = sum(bansho_kazu(a['bansho']) for a in aru)
        return mitsu('%d件・%d枚' % (n, mai), '%d posts, %d photos' % (n, mai),
                     '%d مشاركة و%d صورة' % (n, mai))
    raise Tomeru('ホームの札 %s に、数の出し方がありません' % sid)


def kazu_hiku(sid, sec, kiji, jissen, ken, komari):
    """札の数を、3つのことばぶん、型に入れられる形で返す。"""
    ja, en, ar = home_kazu(sid, sec, kiji, jissen, ken, komari)
    return {'kazu': esc_html(ja), 'kazu_en': esc_html(en), 'kazu_ar': esc_html(ar)}


def build_home(doko, sec, mark, kiji, jissen, ken, komari):
    """ホームの8枚。使った絵の名前も返します（defs に入れるため）。"""
    fuda, tsukatta = [], set()
    for sid, na, _, yo in HOME_FUDA:
        if na not in mark:
            raise Tomeru('ホームの札 %s が src/ill/mark/%s.svg を呼んでいますが、'
                         'その絵がありません' % (sid, na))
        if sid not in doko:
            raise Tomeru('ホームの札 %s に当たる節が、どのページにもありません' % sid)
        w, h, _ = mark[na]
        tsukatta.add(('m', na))
        fuda.append(HOME_T.format(
            page=doko[sid].replace('.html', ''),
            saki='%s#%s' % (doko[sid], sid), na=na, w=w, h=h,
            midashi=esc_html(SETSU_NA[sid]), yo=esc_html(yo),
            **kazu_hiku(sid, sec, kiji, jissen, ken, komari)))
    honbun = ('<section class="sec sec--ki" id="ichiran">\n'
              '  <div class="uchi">\n'
              '    <h2 class="midashi"><span class="en">CONTENTS</span>'
              '<span class="ja">ぜんぶで、8つ</span></h2>\n'
              '    <p class="yomi">押すと、そのページがひらきます。'
              '見た目も帯もそのままなので、いつでもここへ戻れます。</p>\n'
              '    <div class="hban">\n' + '\n'.join(fuda) + '\n    </div>\n'
              '  </div>\n'
              '</section>')
    return honbun, tsukatta


# ══ ホームの「中身を、ざっと」（2026-09-21に追加）════════════
#   札を押すまで中身が分からない、という話から足しました。
#   ★ ここに書く中身は、ぜんぶ節そのものから抜いています。
#     手で写さないこと（節を直したのに概要が古い、が起きます）。

GFUDA = """        <div class="gfuda p--{page}">
          <div class="atama" aria-hidden="true" inert>
            <div class="atama-in">
{atama}
            </div>
          </div>
          <a class="gfuda-a" href="{saki}">
            <span class="gfuda-ue"><b class="gfuda-h">{midashi}</b><span class="gfuda-kazu" data-en="{kazu_en}" data-ar="{kazu_ar}">{kazu}</span><span class="gfuda-go">開く</span></span>
            <span class="gfuda-yo">{yo}</span>
          </a>
        </div>"""

# 概要に出す、節のあたま何個ぶんか。窓の高さでも切るので、多くしても伸びません。
#   2026-09-22：よこスライドにして窓を高くし、中を .atama-in で縮めたので、
#   3個だと窓の下が空いてしまうようになりました。7個に増やします。
ATAMA_N = 7
_IMG_RE = re.compile(r'<img\b[^>]*>')
_ID_RE = re.compile(r'\sid="[^"]*"')
_A_RE = re.compile(r'(<a\b[^>]*?)\shref="[^"]*"')
_VOID = {'br', 'img', 'input', 'hr', 'meta', 'link', 'use', 'path', 'circle',
         'rect', 'source', 'col', 'area', 'ellipse', 'line', 'polygon', 'polyline'}


def uchi_kodomo(sec_html):
    """節の <div class="uchi"> の、じかの子どもを順に切り出す。"""
    m = re.search(r'<div class="uchi">(.*)\n  </div>\n</section>', sec_html, re.S)
    if not m:
        raise Tomeru('節から <div class="uchi"> を切り出せませんでした')
    naka = re.sub(r'<!--.*?-->', '', m.group(1), flags=re.S)
    out, fukasa, hajime = [], 0, None
    for t in re.finditer(r'<(/?)([a-zA-Z][\w-]*)\b[^>]*?(/?)>', naka):
        tojiru, na, jiko = t.group(1), t.group(2).lower(), t.group(3)
        if tojiru:
            fukasa -= 1
            if fukasa == 0 and hajime is not None:
                out.append(naka[hajime:t.end()])
                hajime = None
        elif jiko or na in _VOID:
            if fukasa == 0:
                out.append(t.group(0))
        else:
            if fukasa == 0:
                hajime = t.start()
            fukasa += 1
    if fukasa or not out:
        raise Tomeru('節の中の入れ子が合っていません（概要が作れません）')
    return out


# 窓の頭で飛ばすもの。見出しと、その下の説明文です。
#   2026-09-22：実機で数えたら、**6枚のうち5枚が見出しと説明文だけ**で
#   窓を使い切っていました（「中身をざっと と言っているのに中身が見えない」）。
#   札の下には行き先の名前（学ぶ・実践…）がもう出ているので、
#   窓の中でもう一度 見出しを出すのは、場所の無駄でした。
#   だから **見出しと、頭に続く説明文を飛ばして、中身から始めます。**
#   「写した絵ではなく本物」は変えていません。始める場所を下げただけです。
#   「準備中です」の知らせも飛ばします。まだ何も無い、という知らせは
#   中身ではないので、窓の1枚めに来ると札がいちばん弱く見えます
#   （実測：学ぶの札が「準備中です」で始まっていました）。
#   2026-09-22 夜：窓を2段にして1枚が低くなったので、頭の1つめの重みが
#   増えました。実機で見たら、はじめかたの札が「みんなの実践を見る →」という
#   **入口のボタン1つ**で始まっていました。ボタンは行き先であって中身では
#   ないので、これも飛ばします（bansho-iri ＝ 節の頭に置く入口の行）。
#   ★「まだ1件も届いていません」（komari-mada）は飛ばしません。
#     まだ何も無いページでは、それが唯一の中身だからです。飛ばすと
#     ボタン1つだけの札になって、かえって読めなくなりました（実測）。
_TOBASU = re.compile(r'^\s*<(?:h2[^>]*class="[^"]*\bmidashi\b'
                     r'|p[^>]*class="[^"]*\byomi\b'
                     r'|p[^>]*class="[^"]*\bbansho-iri\b'
                     r'|[a-z0-9]+[^>]*class="[^"]*--mada\b)', re.S)


def atama_kezuru(ko):
    """節の子どもから、頭の見出しと説明文を落とす。
       ぜんぶ落ちてしまう節（説明文しか無い節）は、落とさずに返します。
       空の窓を出すくらいなら、説明文でも出ているほうがよいためです。"""
    i = 0
    while i < len(ko) and _TOBASU.match(ko[i]):
        i += 1
    return ko[i:] if i < len(ko) else ko


def build_atama(sec_html):
    """そのページの「中身のはじまり」を、そのままの大きさで短く載せる。
       ★見出しと説明文は飛ばします（→ atama_kezuru）。
       ★写真は入れません（指導案22ページ＝2.5MB あるため）。
       ★id と href は外します（id が二重になるのと、
         窓の中の押せるものに指やTabが入るのを防ぐため）。
       ★data-yt も外します（残すと、開いただけで YouTube に画像を取りに行きます）。"""
    naka = ''.join(atama_kezuru(uchi_kodomo(sec_html))[:ATAMA_N])
    naka = _IMG_RE.sub('', naka)
    naka = _ID_RE.sub('', naka)
    naka = _A_RE.sub(r'\1', naka)
    naka = re.sub(r'\sdata-yt="[^"]*"', '', naka)
    naka = naka.replace('<summary', '<summary tabindex="-1"')
    naka = naka.replace('<button ', '<button tabindex="-1" ')
    return naka


# ── 行き先の節に、案内役を立たせる（2026-09-23 依頼）──────────
#   札はモノ（封筒・カレンダー・地図…）。押して着いた先の見出しに、
#   その節の人が立っています。「ぱっと見て何の場所か」は札のモノで、
#   「だれが案内するか」は着いてから。絵は1枚も増やしていません。
MIDASHI_KAO_T = ('<span class="midashi-kao%s" aria-hidden="true">'
                 '<svg viewBox="0 0 %g %g" focusable="false">'
                 '<use href="#ill-k-%s"/></svg></span>')


def midashi_kao(sec, kyara):
    """8つの節の見出しの左右に、その節を案内する人を2人ずつ置く。
       見出しは3列（空き｜見出し｜空き）。人は左右の空きに入るので、
       **太字はまん中のまま**です（2026-09-23 依頼）。"""
    for sid, hidari in sorted(SETSU_KYARA.items()):
        if sid not in sec:
            raise Tomeru('見出しに人を立たせようとした節 %s が、'
                         'src/hiroba.html にありません' % sid)
        if sid not in SETSU_KYARA_MIGI:
            raise Tomeru('節 %s の、見出しの右に立つ人が決まっていません'
                         '（build.py の SETSU_KYARA_MIGI に1行足してください）' % sid)
        migi = SETSU_KYARA_MIGI[sid]
        for kao in (hidari, migi):
            if kao not in kyara:
                raise Tomeru('節 %s の案内役が %s.svg を呼んでいますが、'
                             'その絵がありません' % (sid, kao))
        m = re.search(r'<h2 class="midashi">', sec[sid])
        if not m:
            raise Tomeru('節 %s に <h2 class="midashi"> がありません'
                         '（案内役を置く場所が決まりません）' % sid)
        futari = (MIDASHI_KAO_T % ('', kyara[hidari][0], kyara[hidari][1], hidari)
                  + MIDASHI_KAO_T % (' midashi-kao--migi',
                                     kyara[migi][0], kyara[migi][1], migi))
        sec[sid] = (sec[sid][:m.start()] + '<h2 class="midashi midashi--k">'
                    + futari + sec[sid][m.end():])
    return sec


def build_gaiyo(sec, doko, kiji, jissen, ken, komari):
    """ホームの「中身を、ざっと」。
       2026-09-21：箇条書き→本物の縮小→読める箇条書き、と回ったあと、
       「各ページの最初の画面のみ そのまま載せる感じ。短いバージョンで」に落ちつきました。
       だから、節のあたまを載せ、窓の高さで切ります。
       写した絵でも、縮めた絵でもないので、節を直せばここも変わります。

       2026-09-22：ここを **よこスライド** にしました（2列×3段 → 1列よこ）。
       縦に3段あると、それだけで画面2枚ぶんありました。よこにすると、
       1枚の札に使える高さが増えるので、同じ場所で中身が倍ほど見えます。
       字は .atama-in で少し小さくしています（→ style-hiroba.css）。
       札の下には、名前のほかに「数」と「ひとこと」も出します。
       ★数は、その場で数えたものだけ（8つの札と同じ home_kazu を使います）。"""
    fuda = []
    for sid, _, _, yo in HOME_FUDA:
        if sid in ('ima', 'okuru'):   # この2つは、この上に本物が出ているので要りません
            continue
        fuda.append(GFUDA.format(
            page=doko[sid].replace('.html', ''),
            saki='%s#%s' % (doko[sid], sid),
            midashi=esc_html(SETSU_NA[sid]),
            yo=esc_html(yo),
            atama=build_atama(sec[sid]),
            **kazu_hiku(sid, sec, kiji, jissen, ken, komari)))
    return ('<section class="sec" id="gaiyo">\n'
            '  <div class="uchi">\n'
            '    <h2 class="midashi"><span class="en">SUMMARY</span>'
            '<span class="ja">中身を、ざっと</span></h2>\n'
            '    <p class="yomi">それぞれのページの、中身のはじまりです。'
            '写した絵ではなく本物なので、中身が変わればここも変わります。</p>\n'
            + yoko_ban(fuda, 'それぞれのページの中身を、ざっと',
                       mae='前の札を見る', tsugi='次の札を見る', ji=4, cls='gban') + '\n'
            '  </div>\n'
            '</section>')


# ══ 組み上がった1枚を、ページごとに切り分ける ══════════════

def wakeru(body):
    """src/hiroba.html から組んだ body を、部品ごとに切り出す。"""
    def hiku(pat, na):
        m = re.search(pat, body, re.S)
        if not m:
            raise Tomeru('組んだページから「%s」を切り出せませんでした。'
                         'src/hiroba.html の形が変わっていないか見てください' % na)
        return m.group(0)
    hero = hiku(r'<header class="hero".*?</header>', '頭の絵')
    foot = hiku(r'<footer class="foot".*?</footer>', '足もと')
    shikake = hiku(r'<script>.*?</script>', '仕掛け')
    sec = {}
    for m in re.finditer(r'<section class="[^"]*" id="([a-z]+)">.*?\n</section>', body, re.S):
        sec[m.group(1)] = m.group(0)
    motome = set(s for _, _, _, ss in PAGES for s in ss)
    nai = motome - set(sec)
    if nai:
        raise Tomeru('PAGES が %s という節を入れようとしていますが、'
                     'src/hiroba.html にその節がありません' % '、'.join(sorted(nai)))
    amari = set(sec) - motome
    if amari:
        raise Tomeru('src/hiroba.html の節 %s が、PAGES のどのページにも入っていません。'
                     'どこかのページに入れるか、節ごと消してください' % '、'.join(sorted(amari)))
    return hero, sec, foot, shikake


def build_obi(ima_file, doko):
    """帯。どのページでも同じ位置に、同じ8つ。
       2026-09-21：いちど4つ（ページ名）にしましたが、ホームの札8つと
       数がちがって分かりにくい、という話になったので8つに戻しました。
       行き先はページをまたぎます。いまのページにある項目には印をつけます。"""
    gyo = []
    for sid, _, _, _ in HOME_FUDA:
        saki = doko[sid]
        ima = (saki == ima_file)
        gyo.append('      <li><a class="obi-s p--%s%s" href="%s"%s>%s</a></li>'
                   % (saki.replace('.html', ''), ' obi-ima' if ima else '',
                      '#%s' % sid if ima else '%s#%s' % (saki, sid),
                      ' aria-current="page"' if ima else '',
                      esc_html(SETSU_NA[sid])))
    return ('<nav class="obi" aria-label="TOKKATSU広場の中の、8つの行き先">\n'
            '  <div class="obi-uchi">\n'
            '    <a class="obi-na" href="%s">TOKKATSU広場</a>\n'
            '    <ul class="obi-l">\n' % HOME
            + '\n'.join(gyo) + '\n'
            '    </ul>\n'
            '  </div>\n'
            '</nav>')


# 2026-09-23 依頼：字の大きさのつまみを、ほかのページの上部右にも置きます。
#   ここに置くのは **空の入れ物だけ**です。中身は JavaScript が入れます
#   （動かない端末に、押しても何も起きないボタンを置かないため）。
#   ★ホームは src/hiroba.html の .ue-migi（LINEの案内といっしょ）。
#     名前をそろえてあるので、JavaScript の側は1つの書き方で済みます。
KO_T = """<header class="ko{uchi}" id="ue">
  <div class="uchi">
    <div class="ko-ue">
      <p class="ko-modoru"><a href="{home}">TOKKATSU広場</a>{oya}</p>
      <div class="ue-migi"></div>
    </div>
    <h1 class="ko-h">{na}</h1>
    <p class="ko-yo">{yo}</p>
  </div>
{e}</header>"""

# 頭の絵。広い窓とスマホ用の窓を、同じ絵から <use> で切り出します。
#   絵そのものは <defs> の #ill-atama に1つだけ入ります（build_tane）。
#   2回そのまま書くと、ページが絵2枚ぶん重くなります。
KO_E_T = ('  <div class="ko-e ko-e--hiro"><svg viewBox="0 0 {w} {h}" role="img" '
          'aria-label="{yo}のイラスト"><use href="#ill-atama"/></svg></div>\n'
          '  <div class="ko-e ko-e--semai"><svg viewBox="{mado}" role="img" '
          'aria-label="{yo}のイラスト"><use href="#ill-atama"/></svg></div>\n')

# 帯に出ないページの、親への戻り道。帯で「いまどこ」が出ないぶんを、ここで補います。
KO_OYA = """<a class="ko-oya" href="{saki}#{sid}">{na}</a>"""


def ko_atama(f, yo):
    """ページの頭。親があるページには、親への戻り道も出します。
       2026-09-22：名前の下に、そのページの中身を描いた遠目の絵を1枚足しました。"""
    oya = ''
    if f in OYA:
        saki, sid, na = OYA[f]
        oya = KO_OYA.format(saki=saki, sid=sid, na=esc_html(na))
    if f not in KO_E:
        raise Tomeru('%s の頭に置く絵が KO_E にありません。'
                     'ページを足したら、絵も1枚足してください' % f)
    e = KO_E_T.format(w=KO_E_W, h=KO_E_H, mado=KO_E[f][2], yo=esc_html(KO_E[f][1]))
    return KO_T.format(home=HOME, oya=oya, na=esc_html(page_na(f)), yo=esc_html(yo),
                       e=e, uchi=' ko--uchi' if KO_E[f][3] else '')


def page_na(f):
    """画面に出すページの名前。2026-09-21：「知る・学ぶ・集まる」という
       4つの言い方は、帯の8つと数が合わず分かりにくいので画面から消しました。
       かわりに、そのページに入っている節の名前をそのまま出します。"""
    for x, _, _, setsu in PAGES:
        if x == f:
            return '　'.join(SETSU_NA[t] for t in setsu) or 'TOKKATSU広場'
    raise Tomeru('%s は PAGES にありません' % f)


# ══ ことばの意味（用語辞典・2026-09-23 依頼）═══════════════
#   src/kotoba.md が本体です。1語＝## から次の ## まで。
#     ## 見出しの語
#     説明の行（1〜3行）
#     > もとにしたもの
#
#   ★言い方は本サイトによるもので、引用ではありません。
#     「もとにしたもの」は、**どの文書に書かれていることか**を示すためです。
#     ページ数は書きません（版でずれるため）。
#   ★さがす欄は、このページの中だけで動きます。何も送りません。

KOTOBA_MD = os.path.join(SRC, 'kotoba.md')
KOTOBA_SETSU_MAX = 3        # 説明は3行まで（長い説明は、読まれません）


def load_kotoba():
    if not os.path.exists(KOTOBA_MD):
        raise Tomeru('src/kotoba.md がありません（ことばの意味が作れません）')
    hon = rd('kotoba.md') if False else io.open(KOTOBA_MD, encoding='utf-8').read()
    out = []
    for kata in re.split(r'^## ', hon, flags=re.M)[1:]:
        gyo = [x.strip() for x in kata.strip().split('\n')]
        go = gyo[0].strip()
        setsu = [x for x in gyo[1:] if x and not x.startswith('>')]
        moto = [x[1:].strip() for x in gyo[1:] if x.startswith('>')]
        if not go:
            raise Tomeru('src/kotoba.md に、見出しの無い語があります')
        if not setsu:
            raise Tomeru('src/kotoba.md「%s」に説明がありません' % go)
        if len(setsu) > KOTOBA_SETSU_MAX:
            raise Tomeru('src/kotoba.md「%s」の説明が%d行あります（%d行まで）'
                         % (go, len(setsu), KOTOBA_SETSU_MAX))
        if not moto:
            raise Tomeru('src/kotoba.md「%s」に「> もとにしたもの」がありません'
                         % go)
        out.append({'go': go, 'setsu': setsu, 'moto': moto[0]})
    if not out:
        raise Tomeru('src/kotoba.md から1語も読めませんでした')
    na = [a['go'] for a in out]
    futatsu = sorted({x for x in na if na.count(x) > 1})
    if futatsu:
        raise Tomeru('src/kotoba.md に同じ語が2回あります： %s' % '、'.join(futatsu))
    return out


KOTOBA_T = """      <article class="kotoba" data-sagasu="{sagasu}">
        <h3 class="kotoba-go">{go}</h3>
{setsu}        <p class="kotoba-moto">{moto}</p>
      </article>"""


def build_kotoba(kotoba):
    fuda = []
    for a in kotoba:
        setsu = ''.join('        <p class="kotoba-setsu">%s</p>\n' % inline_md(x)
                        for x in a['setsu'])
        fuda.append(KOTOBA_T.format(
            go=esc_html(a['go']), setsu=setsu, moto=esc_html(a['moto']),
            sagasu=esc_html(' '.join([a['go']] + a['setsu']))))
    return ('    <div class="kotoba-sagasu" id="kotoba-sagasu" hidden>\n'
            '      <label class="sagasu-l" for="kotoba-ji">ことばをさがす</label>\n'
            '      <input class="sagasu-i" type="search" id="kotoba-ji" '
            'autocomplete="off" placeholder="例：提案理由、合意形成、係">\n'
            '      <p class="sagasu-kazu" id="kotoba-kazu" role="status" '
            'aria-live="polite"></p>\n'
            '    </div>\n'
            '    <div class="kotoba-ran" id="kotoba-ran">\n'
            + '\n'.join(fuda) + '\n    </div>')


# ══ 検索に出すページ・出さないページ（2026-09-23 依頼）════════
#   2026-09-23 まで、7枚ぜんぶに noindex が付いていました（8月に
#   「URLを配らないかぎり人は来ない」と決めたときのままです）。
#   全国の先生に見つけてもらうため、**6枚とも検索に出します**。
#   「みんなの実践と困りごとを出さなきゃ意味がない」（本人・2026-09-23）。
#
#   ★出さないのは **管理画面だけ** です（乗っ取りが怖いため）。
#     こちらは noindex に加えて robots.txt でも見に来させません。
#
#   ★送られたものが そのまま並ぶ2枚には、**字は出す／絵は出さない**を
#     付けます（KAKUSU_E）。
#       noimageindex          … 画像検索に載せない
#       max-image-preview:none … 検索結果に写真の小窓を出さない
#     実践は題名や中身で見つかるのに、子どもの顔が画像検索に並ぶ道は
#     できません。★これは検索する側への**お願い**で、鍵ではありません。
#       ・従うかどうかは、その検索サービス次第です（Googleは従います）
#       ・URLを知っている人は、これまでどおり写真を見られます
#     そこは変わっていません。変えたのは「検索から辿り着けるかどうか」です。
DASANAI = ('kanri.html',)                      # そもそも検索に出さない
KAKUSU_E = ('bansho.html', 'komari.html')      # 字は出す／絵は出さない


def robots_tag(f):
    if f in DASANAI:
        return '<meta name="robots" content="noindex, nofollow">'
    if f in KAKUSU_E:
        return ('<meta name="robots" '
                'content="index, follow, noimageindex, max-image-preview:none">')
    return '<meta name="robots" content="index, follow">' 


def head_de(f, na):
    """頭は1つの型を使い回し、題と自分のURLだけをページごとに差しかえます。"""
    head = rd('src/head-hiroba.html')
    head = head.replace('<!--BUILD:ROBOTS-->', robots_tag(f))
    dai = 'TOKKATSU広場' if f == HOME else '%s｜TOKKATSU広場' % page_na(f)
    head = head.replace('<title>TOKKATSU広場</title>', '<title>%s</title>' % esc_html(dai))
    if f != HOME:
        head = head.replace('content="%s"' % SITE_URL, 'content="%s%s"' % (SITE_URL, f))
        head = head.replace('content="TOKKATSU広場｜特別活動で、輝く。"',
                            'content="%s｜TOKKATSU広場"' % esc_html(page_na(f)), 1)
    return head


def tsukau_e(html):
    """そのページが実際に呼んでいる絵の名前だけを拾う。"""
    return set(m.groups() for m in re.finditer(r'href="#ill-([kbm])-([a-z0-9-]+)"', html))


def build_tane(html, e_naka, buhin, kyara, mark, atama_naka=None):
    """ページが呼んでいる絵だけを、そのページの defs に入れる。
       呼んでいない絵は入りません（ページごとに軽くなります）。"""
    g = []
    # ホームは絵の本物をそのまま出しています（動かすため）。
    # そこに同じ id をもう1つ作ると、リンクが迷子になるので入れません。
    if 'href="#ill-hiroba"' in html and '<g id="ill-hiroba">' not in html:
        g.append('<g id="ill-hiroba">%s</g>' % e_naka)
    if 'href="#ill-atama"' in html and atama_naka:
        g.append('<g id="ill-atama">%s</g>' % atama_naka)
    # 絵の中にも地紋の <defs> があるので、いちばん外がわ（末尾）にだけ足します
    g.append(kazari_defs(tsukau_e(html), buhin, kyara, mark))
    tane = ('<svg class="tane" aria-hidden="true" focusable="false" width="0" height="0" '
            'style="position:absolute"><defs>%s</defs></svg>' % ''.join(g))
    # 呼んでいるのに入っていない絵が1つでもあれば、止める
    aru = (set(re.findall(r'<g id="(ill-[^"]+)"', tane))
           | set(re.findall(r'<g id="(ill-[^"]+)"', html)))
    yobu = set(re.findall(r'href="#(ill-[^"]+)"', html))
    nai = yobu - aru
    if nai:
        raise Tomeru('ページが #%s を呼んでいますが、そのページの絵の入れ物に入っていません'
                     % '、#'.join(sorted(nai)))
    return tane


# ══════════════════════════════════════════════════════════
# 2-5. ことばの切りかえ（日本語 / English / العربية）
#      2026-09-23 依頼「アラビア語・英語変換ボタンを追加。
#      一番下管理者のところに設置して」
# ══════════════════════════════════════════════════════════
#   ★原則2（何も送信しない）があるので、外の翻訳サービスは使いません。
#     訳は **ぜんぶこの表に書いて、ページの中に入れて配ります**。
#     開いた人の端末から、1バイトも外へ出ません。
#
#   ★訳すのは「このサイトが書いた言葉」だけです。
#     先生方から届いた実践・困りごと・ニュースの題は日本語のままです
#     （訳すには外へ送るしかなく、原則2に触れるため）。
#     そのことは、切りかえたときに画面で断ります（KOTOBA_CHU）。
#
#   ★出どころは、この表1つだけ。
#     下の KOTOBA_TEKI に当たる場所の字が表に無ければ、ビルドが止まります。
#     新しい見出しや説明文を足したら、ここにも1行足してください。
KOTOBA = {
    # ── 節の見出し ──
    'このサイトは、なに': ('What this site is', 'ما هذا الموقع'),
    'ぜんぶで、8つ': ('Eight places in all', 'ثمانية أقسام'),
    'あなたの実践を、ここに': ('Your practice belongs here', 'شارك ممارستك هنا'),
    '中身を、ざっと': ('A quick look inside', 'نظرة سريعة على المحتوى'),
    '特別活動って、なに': ('What is Tokkatsu?', 'ما هي الأنشطة الخاصة (توكاتسو)؟'),
    '4つの内容': ('The four areas', 'المجالات الأربعة'),
    'ことばの意味': ('What the words mean', 'معاني المصطلحات'),
    '学ぶ': ('How to start', 'كيف تبدأ'),
    'すぐ使える道具': ('Tools you can use tomorrow', 'أدوات جاهزة للاستخدام'),
    '最新のニュース': ('Latest news', 'آخر الأخبار'),
    '届いている困りごと': ('Questions that have arrived', 'الأسئلة الواردة'),

    # ── 帯・札の名前（8つ） ──
    '実践を送る': ('Send a practice', 'أرسل ممارسة'),
    'みんなの実践': ('Everyone’s practices', 'ممارسات الجميع'),
    '研究日程': ('Calendar', 'التقويم'),
    '困りごと': ('Questions', 'الأسئلة'),
    'はじめかた': ('How to start', 'كيف تبدأ'),
    'ニュース': ('News', 'الأخبار'),
    '日本の研究会': ('Societies in Japan', 'الجمعيات في اليابان'),
    '特活とは': ('About Tokkatsu', 'عن توكاتسو'),

    # ── 札のひとこと ──
    '写真もPDFも、送るとそのまま出ます。':
        ('Photos and PDFs go straight onto the site.',
         'الصور وملفات PDF تُنشر مباشرة على الموقع.'),
    '先生方から届いた実践が、そのまま並びます。':
        ('Practices sent in by teachers, shown just as they arrived.',
         'ممارسات أرسلها المعلمون، معروضة كما وصلت.'),
    'つぎの研究会と、申込の締切。':
        ('The next meetings, and the registration deadlines.',
         'اللقاءات القادمة ومواعيد التسجيل.'),
    '送られた困りごとが、そのまま並びます。':
        ('Questions sent in, shown just as they arrived.',
         'أسئلة وردت من المعلمين، معروضة كما وصلت.'),
    '①から⑤の学習過程と、一次資料と、道具。':
        ('The five steps of a class meeting, the source documents, and the tools.',
         'مراحل مجلس الفصل الخمس، والمراجع الأصلية، والأدوات.'),
    '一次情報だけ。要約は、こちらの言葉で。':
        ('Primary sources only. The summaries are in our own words.',
         'مصادر أولية فقط. الملخّصات بكلماتنا نحن.'),
    '1つずつ開いて、いま見られるものだけ。':
        ('Open them one by one — only what is online right now.',
         'افتحها واحدة تلو الأخرى — ما هو متاح الآن فقط.'),
    '教科書がない時間の、見るところ。4つの内容も、ここに。':
        ('Where to look for the lesson that has no textbook. The four areas are here too.',
         'دليلك إلى الحصة التي بلا كتاب مدرسي. والمجالات الأربعة هنا أيضًا.'),
    '開く': ('Open', 'افتح'),

    # ── ヒーロー（いちばん上） ──
    '人間関係形成・社会参画・自己実現':
        ('Building relationships · Taking part in society · Becoming yourself',
         'بناء العلاقات · المشاركة في المجتمع · تحقيق الذات'),
    'みんなの実践を見る': ('See everyone’s practices', 'شاهد ممارسات الجميع'),
    'みんなの特活ひろば（LINE）':
        ('Minna no Tokkatsu Hiroba (LINE)', 'ساحة توكاتسو للجميع (LINE)'),

    # ── このサイトは、なに（4行） ──
    '<span>日本の特別活動の<b>情報交流</b>を高めるためのサイトです。</span>'
    '<span>LINEオープンチャット<b>「みんなの特活ひろば（仮）」</b>と連携しています。</span>'
    '<span>あちらで話し、ここで<b>確かめて、持ち帰る</b>。</span>'
    '<span>そのためにお使いください。</span>':
        ('<span>A site for <b>sharing information</b> about Tokkatsu in Japan.</span>'
         '<span>It works together with the LINE open chat '
         '<b>“Minna no Tokkatsu Hiroba”</b>.</span>'
         '<span>Talk over there; <b>check it and take it home</b> over here.</span>'
         '<span>That is what this site is for.</span>',
         '<span>موقع <b>لتبادل المعلومات</b> حول الأنشطة الخاصة (توكاتسو) في اليابان.</span>'
         '<span>يعمل بالتعاون مع محادثة LINE المفتوحة '
         '<b>«ساحة توكاتسو للجميع»</b>.</span>'
         '<span>هناك تتحدّثون، وهنا <b>تتأكّدون وتأخذون ما ينفعكم</b>.</span>'
         '<span>هذا هو الغرض من الموقع.</span>'),

    # ── 4人の札 ──
    'ちょっと聞きたい': ('A quick question', 'سؤال سريع'),
    'いま困っていることを。': ('Whatever you are stuck on right now.',
                              'ما يصعب عليك الآن.'),
    'ちょっと知りたい': ('Something to know', 'ما يستحق المعرفة'),
    '研究日程とニュース。': ('Meetings and news.', 'اللقاءات والأخبار.'),
    'ちょっと試したい': ('Something to try', 'ما يستحق التجربة'),
    '週案に貼る1行つき。': ('With one line you can paste into your weekly plan.',
                            'مع سطر جاهز لخطتك الأسبوعية.'),
    'ちょっと伝えたい': ('Something to pass on', 'ما يستحق المشاركة'),
    '板書も資料も、ここから。': ('Blackboards and handouts — send them from here.',
                                'السبورات والمواد — أرسلها من هنا.'),

    # ── ページの名前とひとこと（子ページの頭） ──
    'ホーム': ('Home', 'الرئيسية'),
    '特活とは 4つの内容 ことばの意味':
        ('About Tokkatsu · The four areas · What the words mean',
         'عن توكاتسو · المجالات الأربعة · معاني المصطلحات'),
    '特別活動って、なに。4つの内容は、どれ。ことばの意味も。':
        ('What Tokkatsu is, what the four areas are, and what the words mean.',
         'ما هي الأنشطة الخاصة، وما المجالات الأربعة، وماذا تعني المصطلحات.'),
    'はじめかた すぐ使える道具':
        ('How to start · Tools you can use tomorrow',
         'كيف تبدأ · أدوات جاهزة للاستخدام'),
    '学級会の学習過程と、一次資料と、持ち帰れる道具。':
        ('The steps of a class meeting, the source documents, and tools to take home.',
         'مراحل مجلس الفصل، والمراجع الأصلية، وأدوات تأخذها معك.'),
    '研究日程 ニュース 日本の研究会':
        ('Calendar · News · Societies in Japan',
         'التقويم · الأخبار · الجمعيات في اليابان'),
    '研究日程、ニュース、各地の研究会。':
        ('Meetings, news, and societies across the country.',
         'اللقاءات والأخبار والجمعيات في أنحاء البلاد.'),
    '送ってもらった実践が、そのまま並びます。':
        ('Practices that teachers sent in, shown just as they arrived.',
         'ممارسات أرسلها المعلمون، معروضة كما وصلت.'),
    'ちょっと聞きたい 困りごと':
        ('A quick question · Questions', 'سؤال سريع · الأسئلة'),
    'いま困っていることを書く。届いたものを読む。':
        ('Write what you are stuck on. Read what others have sent.',
         'اكتب ما يصعب عليك، واقرأ ما أرسله غيرك.'),

    # ── 節の説明（.yomi） ──
    '押すと、そのページがひらきます。見た目も帯もそのままなので、いつでもここへ戻れます。':
        ('Tap a card and that page opens. The look and the top bar stay the same, '
         'so you can always come back here.',
         'اضغط على أي بطاقة لتُفتح صفحتها. المظهر وشريط التنقل لا يتغيّران، '
         'فيمكنك العودة إلى هنا في أي وقت.'),
    '板書の写真1枚でも、指導案のPDFでも。':
        ('One photo of a blackboard, or a lesson-plan PDF — either is welcome.',
         'صورة واحدة للسبورة، أو ملف PDF لخطة الدرس — كلاهما مرحّب به.'),
    '<b>困っていること</b>は <a href="komari.html#komari">ちょっと聞きたい</a> へ。'
    '書くと、そのまま並びます。<br> ただし<strong>答えが早いのは '
    '<b>LINEオープンチャット「みんなの特活ひろば」</b></strong>のほうです。<br> '
    'LINEなら<strong>505人</strong>が読んでいて、その日のうちに誰かが答えてくれます。':
        ('<b>Something you are stuck on</b> goes to '
         '<a href="komari.html#komari">A quick question</a>. '
         'What you write appears straight away.<br> But <strong>answers come faster in the '
         '<b>LINE open chat “Minna no Tokkatsu Hiroba”</b></strong>.<br> '
         'There, <strong>505 teachers</strong> are reading, and someone usually '
         'replies the same day.',
         '<b>ما يصعب عليك</b> اكتبه في '
         '<a href="komari.html#komari">سؤال سريع</a>. '
         'يظهر ما تكتبه مباشرة.<br> لكنّ <strong>الردّ أسرع في '
         '<b>محادثة LINE المفتوحة «ساحة توكاتسو للجميع»</b></strong>.<br> '
         'هناك يقرأ <strong>505</strong> معلمين، وغالبًا يردّ أحدهم في اليوم نفسه.'),
    'それぞれのページの、中身のはじまりです。写した絵ではなく本物なので、中身が変わればここも変わります。':
        ('The opening of each page. This is the real content, not a copy of it, '
         'so when a page changes this changes too.',
         'بداية كل صفحة. هذا هو المحتوى نفسه لا نسخة عنه، '
         'فإذا تغيّرت الصفحة تغيّر ما تراه هنا.'),
    'あなたの困りごとも <a>ちょっと聞きたい</a> から送れます。<br> '
    '<strong>答えが早いのはLINEのほう</strong>です。505人が読んでいます。':
        ('You can send your own question from <a>A quick question</a>.<br> '
         '<strong>Answers come faster on LINE</strong> — 505 teachers are reading there.',
         'يمكنك إرسال سؤالك من <a>سؤال سريع</a>.<br> '
         '<strong>الردّ أسرع في LINE</strong> — يقرأ هناك 505 معلمين.'),
    '国語や算数とちがって、教科書がありません。<br> 決めるのも、やるのも、ふり返るのも、子どもです。<br> '
    '先生の仕事は、教えることではなく、子どもが決められるようにすること。':
        ('Unlike Japanese or mathematics, there is no textbook.<br> '
         'The children decide, the children act, the children look back.<br> '
         'The teacher’s work is not to teach, but to make it possible for children to decide.',
         'على عكس اللغة أو الرياضيات، لا يوجد كتاب مدرسي.<br> '
         'الأطفال هم من يقرّرون، ومن ينفّذون، ومن يراجعون.<br> '
         'عمل المعلم ليس أن يُلقّن، بل أن يجعل القرار ممكنًا للأطفال.'),
    'ここは、その手だてが溜まる場です。<br> 話す場は <a class="line-l" '
    'href="https://line.me/ti/g2/9xsmT5pjwv8jTB-EtUfHn2OoA3Iq0H2ZZqq1gA?utm_source=invitation'
    '&utm_medium=link_copy&utm_campaign=default" target="_blank" rel="noopener noreferrer">'
    'LINEオープンチャット「みんなの特活ひろば」<i>外部</i></a>。<br> '
    '<strong>あなたの実践も、<a href="index.html#okuru">送れば そのまま</a> ここに載ります。</strong>':
        ('This is where those ways of doing it collect.<br> The place to talk is the '
         '<a class="line-l" '
         'href="https://line.me/ti/g2/9xsmT5pjwv8jTB-EtUfHn2OoA3Iq0H2ZZqq1gA?utm_source=invitation'
         '&utm_medium=link_copy&utm_campaign=default" target="_blank" rel="noopener noreferrer">'
         'LINE open chat “Minna no Tokkatsu Hiroba”<i>external</i></a>.<br> '
         '<strong>Your practice too — <a href="index.html#okuru">send it and it appears</a> '
         'right here.</strong>',
         'هنا تتجمّع هذه الطرائق.<br> ومكان الحديث هو '
         '<a class="line-l" '
         'href="https://line.me/ti/g2/9xsmT5pjwv8jTB-EtUfHn2OoA3Iq0H2ZZqq1gA?utm_source=invitation'
         '&utm_medium=link_copy&utm_campaign=default" target="_blank" rel="noopener noreferrer">'
         'محادثة LINE المفتوحة «ساحة توكاتسو للجميع»<i>خارجي</i></a>.<br> '
         '<strong>وممارستك أيضًا — <a href="index.html#okuru">أرسلها فتظهر</a> '
         'هنا كما هي.</strong>'),
    '特別活動は、この4つでできています。絵の中のどこにあるかを、切り出してあります。':
        ('Tokkatsu is made of these four. Each one is cut out of the picture '
         'to show where it happens.',
         'تتكوّن الأنشطة الخاصة من هذه المجالات الأربعة، '
         'وكلٌّ منها مقتطع من الرسم ليُظهر أين يحدث.'),
    '送られた困りごとは <a href="komari.html#komari">困りごと</a>、届いた実践は '
    '<a href="bansho.html#bansho">みんなの実践</a> にあります。<br>'
    'どちらも、送るときにこの4つのどれかを選んでもらっています。':
        ('Questions that were sent are in <a href="komari.html#komari">Questions</a>, '
         'and practices that arrived are in '
         '<a href="bansho.html#bansho">Everyone’s practices</a>.<br>'
         'For both, the sender chooses one of these four areas.',
         'الأسئلة المُرسلة في <a href="komari.html#komari">الأسئلة</a>، '
         'والممارسات الواردة في '
         '<a href="bansho.html#bansho">ممارسات الجميع</a>.<br>'
         'وفي الحالتين يختار المُرسِل أحد هذه المجالات الأربعة.'),
    '特別活動の会議や資料で出てくることばを、はじめての先生に向けて短く。<br> '
    '言い方はこのサイトによるものです。引用ではありません。':
        ('Words that come up in Tokkatsu meetings and documents, put briefly '
         'for a teacher meeting them for the first time.<br> '
         'The wording is this site’s own. These are not quotations.',
         'مصطلحات تتكرّر في لقاءات الأنشطة الخاصة ووثائقها، مشروحة باختصار '
         'لمن يلتقي بها لأول مرة.<br> '
         'الصياغة من إعداد هذا الموقع، وليست اقتباسًا.'),
    '困りごとから、いま必要なところへ。<br>'
    '学級会の学習過程と、根拠になる一次資料をこのページの中で確かめられます。':
        ('From what you are stuck on, straight to what you need now.<br>'
         'The steps of a class meeting, and the source documents behind them, '
         'are all on this page.',
         'من المشكلة التي تواجهك إلى ما تحتاجه الآن مباشرة.<br>'
         'مراحل مجلس الفصل والمراجع الأصلية التي تستند إليها، كلّها في هذه الصفحة.'),
    'ここは<strong>こちらで用意したもの</strong>です。学級会グッズ、映像資料、<br> '
    'よく出る困りごとに効く手だて。<strong>持ち帰って、明日そのまま使えるもの</strong>だけを置きます。':
        ('This part is <strong>what we prepared</strong>: class-meeting kit, video material,<br> '
         'and ways of handling the problems that come up most. '
         'Only things you can <strong>take home and use tomorrow</strong>.',
         'هذا القسم <strong>من إعدادنا</strong>: أدوات مجلس الفصل، ومواد مصوّرة،<br> '
         'وطرائق لمعالجة أكثر المشكلات تكرارًا. '
         'لا نضع هنا إلا ما <strong>يمكنك أخذه واستعماله غدًا</strong>.'),
    '先生方から届いた実践は、こちらではなく <strong>「みんなの実践」</strong>にあります。<br> '
    'あちらが本物の持ち寄り、ここが道具箱です。':
        ('Practices sent in by teachers are not here — they are in '
         '<strong>“Everyone’s practices”</strong>.<br> '
         'That is the real potluck; this is the toolbox.',
         'الممارسات التي أرسلها المعلمون ليست هنا، بل في '
         '<strong>«ممارسات الجميع»</strong>.<br> '
         'تلك هي المائدة المشتركة، وهذا هو صندوق الأدوات.'),
    '研究会の当日と、申込の締切。':
        ('The day of each meeting, and the registration deadline.',
         'يوم انعقاد كل لقاء، وآخر موعد للتسجيل.'),
    '特別活動にかかわる一次情報だけ。要約はこちらの言葉です。<br>'
    '題を押したときだけ、出どころ（外部）がひらきます。':
        ('Primary sources on Tokkatsu only. The summaries are in our own words.<br>'
         'The source (an external site) opens only when you tap the title.',
         'مصادر أولية عن الأنشطة الخاصة فقط. الملخّصات بكلماتنا نحن.<br>'
         'ولا يُفتح المصدر (موقع خارجي) إلا عند الضغط على العنوان.'),
    '全国と各地の会が、それぞれ何を置いているか。<br> '
    '押すと、その会のサイトが<strong>新しいタブ</strong>で開きます（外部）。':
        ('What the national and regional societies each make available.<br> '
         'Tapping opens that society’s site in a <strong>new tab</strong> (external).',
         'ما تتيحه كل جمعية وطنية أو محلّية.<br> '
         'الضغط يفتح موقع تلك الجمعية في <strong>تبويب جديد</strong> (موقع خارجي).'),
    '日本各地の実践を<strong>シェア</strong>！<br> お気軽に投稿してください！':
        ('<strong>Share</strong> practices from all over Japan!<br> '
         'Please post — anyone is welcome.',
         '<strong>شارِك</strong> ممارسات من كل أنحاء اليابان!<br> '
         'لا تتردّد في النشر — الباب مفتوح للجميع.'),
    'いま困っていることを、そのまま書いてください。':
        ('Write what you are stuck on, just as it is.',
         'اكتب ما يصعب عليك الآن، كما هو.'),
    '答えが見つかったものから、<a href="manabu.html#manabu">学ぶ</a>の入口で押せる札になっていきます。':
        ('As answers are found, each one becomes a card you can tap at the entrance to '
         '<a href="manabu.html#manabu">How to start</a>.',
         'وكلّما وُجد جواب، صار سؤاله بطاقة يمكن الضغط عليها عند مدخل '
         '<a href="manabu.html#manabu">كيف تبدأ</a>.'),
    '送られてきたものを、そのまま並べています。<br> 答えが見つかったものは、'
    '<a href="manabu.html#manabu">学ぶ</a>の入口で<strong>押せる札</strong>になります。':
        ('Shown just as they were sent.<br> Once an answer is found, it becomes a '
         '<strong>card you can tap</strong> at the entrance to '
         '<a href="manabu.html#manabu">How to start</a>.',
         'معروضة كما وردت تمامًا.<br> وإذا وُجد الجواب، صارت '
         '<strong>بطاقة قابلة للضغط</strong> عند مدخل '
         '<a href="manabu.html#manabu">كيف تبدأ</a>.'),
    'あなたの困りごとも <a href="#kiku">ちょっと聞きたい</a> から送れます。<br> '
    '<strong>答えが早いのはLINEのほう</strong>です。505人が読んでいます。':
        ('You can send your own question from <a href="#kiku">A quick question</a>.<br> '
         '<strong>Answers come faster on LINE</strong> — 505 teachers are reading there.',
         'يمكنك إرسال سؤالك من <a href="#kiku">سؤال سريع</a>.<br> '
         '<strong>الردّ أسرع في LINE</strong> — يقرأ هناك 505 معلمين.'),

    # ── 足もと ──
    '特別活動で、輝く。': ('Shine through Tokkatsu.', 'تألّق مع الأنشطة الخاصة.'),
    '管理者：伊藤 優': ('Site owner: Yu Ito', 'مسؤول الموقع: يو إيتو'),
    '管理画面': ('Admin page', 'لوحة الإدارة'),

    # ── いちばん上の LINE の帯 ──
    '<b>LINE</b>みんなの特活ひろば<i aria-hidden="true">↗</i>':
        ('<b>LINE</b>Minna no Tokkatsu Hiroba<i aria-hidden="true">↗</i>',
         '<b>LINE</b>ساحة توكاتسو للجميع<i aria-hidden="true">↗</i>'),

    # ── 2026-09-23 追加（送るところ・ことばの意味・欄の名前）──
    '特別活動':
        ('Special Activities',
         'الأنشطة الخاصة'),
    'なすことによって学ぶ':
        ('Learning by doing',
         'التعلّم بالممارسة'),
    '人間関係形成':
        ('Building human relationships',
         'بناء العلاقات الإنسانية'),
    '社会参画':
        ('Social participation',
         'المشاركة الاجتماعية'),
    '自己実現':
        ('Self-realisation',
         'تحقيق الذات'),
    '学級活動(1)':
        ('Classroom Activities (1)',
         'أنشطة الفصل (١)'),
    '学級活動(2)':
        ('Classroom Activities (2)',
         'أنشطة الفصل (٢)'),
    '学級活動(3)':
        ('Classroom Activities (3)',
         'أنشطة الفصل (٣)'),
    '児童会活動':
        ('Student Council Activities',
         'أنشطة مجلس التلاميذ'),
    'クラブ活動':
        ('Club Activities',
         'أنشطة النوادي'),
    '学校行事':
        ('School Events',
         'الفعاليات المدرسية'),
    '自発的、自治的な活動':
        ('Self-initiated, self-governing activity',
         'نشاط ينبع من التلاميذ ويديرونه بأنفسهم'),
    '議題':
        ('Gidai — an item the class decides together',
         'موضوع النقاش — ما يقرّره الفصل معًا'),
    '題材':
        ('Zaizai — a topic the teacher sets',
         'الموضوع الذي يحدّده المعلّم'),
    '提案理由':
        ('Reason for the proposal',
         'سبب الاقتراح'),
    '計画委員会':
        ('Planning committee',
         'لجنة التخطيط'),
    '合意形成':
        ('Building consensus',
         'بناء التوافق'),
    '意思決定':
        ('Personal decision-making',
         'القرار الشخصي'),
    '話合い活動':
        ('Discussion activity',
         'نشاط الحوار'),
    '学級会':
        ('Class meeting',
         'اجتماع الفصل'),
    '係活動':
        ('Kakari — jobs the children invent',
         'المهام التي يبتكرها التلاميذ'),
    '当番活動':
        ('Toban — duties that rotate',
         'المهام الدورية الواجبة'),
    'キャリア・パスポート':
        ('Career Passport',
         'جواز المسار المهني'),
    '学習過程':
        ('The learning process',
         'مسار التعلّم'),
    '振り返り':
        ('Reflection',
         'المراجعة بعد التنفيذ'),
    '教科書のない教科です。学級や学校の生活を、子どもたちが自分たちでよりよくしていく活動をまとめて、こう呼びます。':
        ('A subject with no textbook. It is the name for all the activities in which children make their own class and school life better.',
         'مادة بلا كتاب مدرسي. هو الاسم الجامع للأنشطة التي يحسّن بها التلاميذ حياة فصلهم ومدرستهم بأنفسهم.'),
    '学級活動・児童会活動・クラブ活動・学校行事の4つでできています。':
        ('It is made up of four parts: Classroom Activities, Student Council Activities, Club Activities and School Events.',
         'ويتكوّن من أربعة أقسام: أنشطة الفصل، وأنشطة مجلس التلاميذ، وأنشطة النوادي، والفعاليات المدرسية.'),
    '特別活動の考え方の芯です。話を聞いて分かるのではなく、実際にやってみて、うまくいかなくて、また考える。その繰り返しで学びます。':
        ('The core idea of Special Activities. You do not learn it by being told. You try, it does not work, you think again — and learning happens in that loop.',
         'هذا هو جوهر الأنشطة الخاصة. لا يتعلّم الطفل بالاستماع، بل بالمحاولة والإخفاق وإعادة التفكير، ويحدث التعلّم داخل هذه الدورة.'),
    'だから、失敗できる場が要ります。':
        ('So children need a place where failing is allowed.',
         'ولذلك يحتاج التلاميذ إلى مكان يُسمح فيه بالإخفاق.'),
    '特別活動が育てる3つの視点の1つ。年齢や考え方のちがう人と、よりよい関係をつくっていく力です。':
        ('One of the three perspectives Special Activities develop: the ability to build better relationships with people of different ages and different views.',
         'أحد المنظورات الثلاثة التي تنمّيها الأنشطة الخاصة: القدرة على بناء علاقات أفضل مع من يختلفون في السنّ أو في الرأي.'),
    '仲よくすることとは、少しちがいます。合わない人とも一緒にやれることを指します。':
        ('It is not quite the same as getting along. It means being able to work with people you do not click with.',
         'وهو ليس مجرّد الوفاق، بل القدرة على العمل مع من لا تنسجم معه.'),
    '3つの視点の2つめ。自分たちの集団や社会を、自分たちでよりよくしていこうとする態度です。':
        ('The second perspective: the will to make your own group and society better yourselves.',
         'المنظور الثاني: الإرادة في تحسين الجماعة والمجتمع بأيدي أفرادهما.'),
    '「誰かが決めてくれる」から「自分たちで決める」へ、という転換です。':
        ('It is the shift from “somebody decides for us” to “we decide”.',
         'إنه انتقال من «غيرنا يقرّر» إلى «نحن نقرّر».'),
    '3つの視点の3つめ。集団の中で、自分のよさを生かし、これからの生き方を考えていくことです。':
        ('The third perspective: using your own strengths inside a group, and thinking about how you want to live.',
         'المنظور الثالث: توظيف نقاط قوّتك داخل الجماعة، والتفكير في الحياة التي تريدها.'),
    '集団に埋もれることでも、目立つことでもありません。':
        ('It is neither disappearing into the group nor standing out from it.',
         'وهو ليس الذوبان في الجماعة ولا التميّز عنها.'),
    '「学級や学校における生活づくりへの参画」。議題を子どもが出し、子どもが決めます。':
        ('“Taking part in building class and school life.” The children raise the agenda item, and the children decide.',
         '«المشاركة في بناء حياة الفصل والمدرسة». التلاميذ هم من يطرح الموضوع وهم من يقرّر.'),
    '学級会がこれにあたります。目ざすところは合意形成です。':
        ('This is what the class meeting is. What it aims at is consensus.',
         'وهذا ما يُسمّى اجتماع الفصل، وغايته بناء التوافق.'),
    '「日常の生活や学習への適応と自己の成長及び健康安全」。題材は教師が設定します。':
        ('“Adapting to daily life and learning, personal growth, health and safety.” Here the teacher sets the topic.',
         '«التكيّف مع الحياة اليومية والتعلّم، والنموّ الشخصي، والصحّة والسلامة». هنا يحدّد المعلّم الموضوع.'),
    '食事・睡眠・安全など、一人一人が自分のこととして決めます。目ざすところは意思決定です。':
        ('Food, sleep, safety — each child decides for themselves. What it aims at is a personal decision.',
         'الطعام والنوم والسلامة — يقرّر كل تلميذ لنفسه. وغايته القرار الشخصي.'),
    '「一人一人のキャリア形成と自己実現」。こちらも題材は教師が設定します。':
        ('“Each child’s career formation and self-realisation.” Here too the teacher sets the topic.',
         '«بناء المسار المهني لكل تلميذ وتحقيق ذاته». وهنا أيضًا يحدّد المعلّم الموضوع.'),
    '係活動や当番、学ぶことの意義、将来の生き方を扱います。目ざすところは意思決定です。':
        ('It covers classroom jobs and duties, why learning matters, and how to live in future. What it aims at is a personal decision.',
         'ويتناول مهام الفصل والمناوبات، ومعنى التعلّم، وطريقة الحياة في المستقبل. وغايته القرار الشخصي.'),
    '全校の子どもでつくる組織の活動です。代表委員会や委員会活動、児童会集会などがあります。':
        ('An organisation run by the children of the whole school: the representatives’ committee, the standing committees, school-wide assemblies.',
         'تنظيم يديره تلاميذ المدرسة كلّها: مجلس الممثّلين، واللجان الدائمة، والتجمّعات المدرسية.'),
    '学校全体をよりよくするところが、学級活動とのちがいです。':
        ('What makes it different from Classroom Activities is that it improves the whole school.',
         'وما يميّزه عن أنشطة الفصل أنه يحسّن المدرسة بأكملها.'),
    '主として第4学年以上の、同じ興味や関心をもつ子どもが集まって行う活動です。':
        ('Children from Year 4 upwards who share an interest gather and work on it together.',
         'يجتمع التلاميذ من الصف الرابع فما فوق ممّن تجمعهم ميول مشتركة ويعملون عليها معًا.'),
    '異なる学年が一緒になるところに意味があります。':
        ('The point is that different year groups mix.',
         'والمغزى هو اختلاط الصفوف المختلفة.'),
    '儀式的行事・文化的行事・健康安全体育的行事・遠足集団宿泊的行事・勤労生産奉仕的行事の5つです。':
        ('There are five kinds: ceremonies, cultural events, health–safety–PE events, excursions and residential trips, and work–production–service events.',
         'وهي خمسة أنواع: الاحتفالات الرسمية، والفعاليات الثقافية، وفعاليات الصحّة والسلامة والرياضة، والرحلات والمبيت الجماعي، وفعاليات العمل والإنتاج والخدمة.'),
    'やること自体が目的ではなく、集団への所属感や公共の精神を育てるためのものです。':
        ('Holding the event is not the aim. The aim is a sense of belonging and a public spirit.',
         'إقامة الفعالية ليست الغاية؛ الغاية هي الإحساس بالانتماء وروح الصالح العام.'),
    '子どもが自分たちで問題を見つけ、話し合い、決め、実践する活動のことです。':
        ('Activity in which children find the problem, talk it over, decide and carry it out themselves.',
         'نشاط يكتشف فيه التلاميذ المشكلة، ويتحاورون، ويقرّرون، وينفّذون بأنفسهم.'),
    '教師が決めたことを子どもにやらせるのは、これにあたりません。':
        ('Having children carry out what the teacher decided does not count as this.',
         'أمّا تنفيذ التلاميذ لما قرّره المعلّم فلا يُعدّ من هذا الباب.'),
    '学級活動(1)で話し合うことがらです。子どもが出します。':
        ('What the class talks about in Classroom Activities (1). The children raise it.',
         'ما يناقشه الفصل في أنشطة الفصل (١). والتلاميذ هم من يطرحه.'),
    '「みんなで決めたいこと」であることが条件で、一人で決められることや、先生が決めることは議題になりません。':
        ('It has to be something the class wants to decide together. Anything one child can decide alone, or that the teacher decides, is not an agenda item.',
         'ويُشترط أن يكون ممّا يريد الفصل أن يقرّره معًا؛ فما يقرّره تلميذ وحده أو يقرّره المعلّم ليس موضوعًا للنقاش.'),
    '学級活動(2)(3)で扱うことがらです。教師が設定します。':
        ('What is dealt with in Classroom Activities (2) and (3). The teacher sets it.',
         'ما تتناوله أنشطة الفصل (٢) و(٣). والمعلّم هو من يحدّده.'),
    '議題とまぎらわしいのですが、出どころがちがいます。ここを取りちがえると、活動の性格が変わります。':
        ('It is easily confused with an agenda item, but it comes from a different place. Mix the two up and the nature of the activity changes.',
         'يسهل الخلط بينه وبين موضوع النقاش، لكنّ مصدرهما مختلف؛ والخلط بينهما يغيّر طبيعة النشاط.'),
    '「なぜこれをクラス全員で話す必要があるのか」を述べたものです。':
        ('It states why this has to be talked about by the whole class.',
         'يوضّح لماذا يجب أن يناقش الفصل كلّه هذا الأمر.'),
    '話合いで案をくらべるときのものさしになります。ここが弱いと、話合いは好き嫌いの言い合いになります。':
        ('It becomes the measure for comparing ideas. When it is weak, the discussion turns into a swap of likes and dislikes.',
         'وهو المعيار الذي تُقارن به الاقتراحات. وإذا ضعف، تحوّل الحوار إلى تبادل أهواء.'),
    '学級会の前に、議題を選び、進め方を考える子どもたちの集まりです。':
        ('A group of children who, before the class meeting, choose the agenda item and plan how the meeting will run.',
         'مجموعة من التلاميذ يختارون موضوع النقاش قبل الاجتماع ويخطّطون لسير الجلسة.'),
    '司会・記録・提案者などで構成します。ここが育つと、学級会が回りはじめます。':
        ('It is made up of the chair, the note-taker, the proposer and so on. Once this grows, the class meeting starts to run by itself.',
         'وتتكوّن من المُيسِّر والمدوّن وصاحب الاقتراح وغيرهم. ومتى نضجت، بدأ الاجتماع يسير من تلقاء نفسه.'),
    'みんなが納得できる一つの答えを、話合いでつくることです。学級活動(1)が目ざすところです。':
        ('Making, through discussion, one answer everyone can accept. This is what Classroom Activities (1) aim at.',
         'صنع إجابة واحدة يقبلها الجميع، عبر الحوار. وهذا ما تسعى إليه أنشطة الفصل (١).'),
    '多数決で決めることではありません。人数ではなく理由をくらべます。':
        ('It is not deciding by majority vote. You compare reasons, not head counts.',
         'وليس القرار بالأغلبية؛ فالمقارنة بين الأسباب لا بين الأعداد.'),
    '一人一人が、自分のこととして「これをやる」と決めることです。学級活動(2)(3)が目ざすところです。':
        ('Each child deciding, as their own business, “I will do this.” This is what Classroom Activities (2) and (3) aim at.',
         'أن يقرّر كل تلميذ بنفسه ولنفسه: «سأفعل هذا». وهذا ما تسعى إليه أنشطة الفصل (٢) و(٣).'),
    'クラスで1つに決める合意形成とは、目ざすところがちがいます。':
        ('It aims at something different from consensus, where the class settles on one answer.',
         'وغايته تختلف عن بناء التوافق الذي يستقرّ فيه الفصل على إجابة واحدة.'),
    '学級活動(1)の中心になる活動です。「出し合う → くらべ合う → まとめる」の順で進みます。':
        ('The activity at the centre of Classroom Activities (1). It goes: put ideas out → compare them → bring them together.',
         'النشاط المحوري في أنشطة الفصل (١)، ويسير هكذا: نطرح الأفكار ← نقارنها ← نجمعها.'),
    '出し合っている間は、よい悪いを言いません。':
        ('While ideas are being put out, nobody says good or bad.',
         'وأثناء طرح الأفكار لا يُقال جيّد أو رديء.'),
    '学級活動(1)を行う時間の、実際の呼び名です。議題を子どもが出し、子どもが司会をして進めます。':
        ('The everyday name for the lesson in which Classroom Activities (1) happen. The children raise the agenda item and the children chair it.',
         'الاسم المتداول للحصّة التي تجري فيها أنشطة الفصل (١). التلاميذ يطرحون الموضوع ويُيسّرون الجلسة.'),
    '教師は決めません。見取り、必要なときだけ助けます。':
        ('The teacher does not decide. The teacher watches, and steps in only when needed.',
         'لا يقرّر المعلّم؛ بل يراقب ولا يتدخّل إلا عند الحاجة.'),
    '学級の生活を楽しく豊かにするために、子どもが自分たちで考えてつくる仕事です。':
        ('Jobs the children think up themselves to make class life richer and more enjoyable.',
         'مهام يبتكرها التلاميذ بأنفسهم ليجعلوا حياة الفصل أغنى وأمتع.'),
    '当番活動とはちがいます。当番は誰かが必ずやらねばならない仕事、係は無くても困らないが、あると学級が豊かになる仕事です。':
        ('Not the same as rotating duties. A duty is work someone must do; a kakari job is work nobody would miss, but which makes the class richer.',
         'وهي غير المهام الدورية. المناوبة عمل لا بدّ أن يقوم به أحد، أمّا مهمّة «كاكاري» فلا يفتقدها أحد لو غابت، لكنّها تُغني الفصل إن وُجدت.'),
    '給食・掃除・日直など、学級の生活を成り立たせるために必ず必要な仕事です。':
        ('Lunch, cleaning, the day’s monitor — work the class cannot run without.',
         'الغداء والتنظيف ومناوبة اليوم — أعمال لا يقوم الفصل بدونها.'),
    '創意工夫の余地は係活動より小さく、公平に回すことが大事になります。':
        ('There is less room to invent than in kakari jobs, so sharing them fairly is what matters.',
         'ومجال الابتكار فيها أضيق، فالمهمّ أن تُوزَّع بالعدل.'),
    '小学校から高校までの、学びの記録を積み上げていく教材です。学級活動(3)と結びついています。':
        ('A record of learning built up from primary through to upper secondary school. It is tied to Classroom Activities (3).',
         'سجلّ للتعلّم يُبنى من الابتدائية حتى الثانوية، ويرتبط بأنشطة الفصل (٣).'),
    '書かせることが目的ではなく、自分で見返して次を考えるためのものです。':
        ('Filling it in is not the point. It is there to be looked back on, to think about what comes next.',
         'وليست الغاية أن يملأه الطفل، بل أن يعود إليه ليفكّر في الخطوة التالية.'),
    '学級活動(1)の一連の流れです。①問題の発見・確認 ②解決方法等の話合い ③解決方法の決定 ④決めたことの実践 ⑤振り返り、と進み、また①に戻ります。':
        ('The whole cycle of Classroom Activities (1): ① find and confirm the problem ② talk about how to solve it ③ decide ④ carry out what was decided ⑤ reflect — then back to ①.',
         'الدورة الكاملة لأنشطة الفصل (١): ① اكتشاف المشكلة وتأكيدها ② الحوار حول الحلّ ③ اتخاذ القرار ④ تنفيذ ما تقرّر ⑤ المراجعة — ثم العودة إلى ①.'),
    '1時間で終わるものではなく、学級会の前と後を含めた流れです。':
        ('It does not fit into one lesson. It is a flow that includes what comes before and after the class meeting.',
         'ولا تنتهي في حصّة واحدة؛ فهي مسار يشمل ما قبل الاجتماع وما بعده.'),
    'やってみた後で、はじめの自分の考えとくらべることです。':
        ('After trying it, comparing the result with what you thought at the start.',
         'أن تقارن بعد التنفيذ بين النتيجة وما كنت تظنّه في البداية.'),
    '「楽しかった」で終わらせず、次の議題につなげるところまでが振り返りです。':
        ('Reflection is not over at “that was fun”. It runs as far as the next agenda item.',
         'ولا تنتهي المراجعة عند «كان ممتعًا»؛ بل تمتدّ حتى موضوع النقاش التالي.'),
    'さがす':
        ('Search',
         'ابحث'),
    'ことばをさがす':
        ('Search the words',
         'ابحث في المصطلحات'),
    '字の大きさ':
        ('Text size',
         'حجم الخطّ'),
    '必須':
        ('required',
         'مطلوب'),
    '任意':
        ('optional',
         'اختياري'),
    '内容':
        ('Which of the four',
         'أيٌّ من الأربعة'),
    '学年':
        ('Year group',
         'الصف'),
    '地域':
        ('Where',
         'المكان'),
    'お名前':
        ('Your name',
         'اسمك'),
    '所属':
        ('School or affiliation',
         'المدرسة أو الجهة'),
    '実践内容':
        ('What you did',
         'ما الذي قمت به'),
    '推しポイント':
        ('The one thing to notice',
         'أبرز نقطة'),
    '議題名・題材名・行事名':
        ('Agenda item, topic or event name',
         'اسم موضوع النقاش أو الموضوع أو الفعالية'),
    '議題名・題材名・行事名・タイトル':
        ('Agenda item, topic, event name or title',
         'اسم موضوع النقاش أو الموضوع أو الفعالية أو العنوان'),
    '写真・PDFをえらぶ':
        ('Choose photos or a PDF',
         'اختر صورًا أو ملفّ PDF'),
    '市区町村':
        ('Municipality',
         'البلدية'),
    '会の名前':
        ('Name of the meeting',
         'اسم اللقاء'),
    'いつ':
        ('When',
         'متى'),
    '2日目':
        ('Second day',
         'اليوم الثاني'),
    '申込の〆切':
        ('Application deadline',
         'آخر موعد للتسجيل'),
    '何をやる会か':
        ('What happens there',
         'ماذا يجري فيه'),
    '会場':
        ('Venue',
         'المكان'),
    '主催':
        ('Organiser',
         'الجهة المنظِّمة'),
    '申込みについて':
        ('About applying',
         'عن التسجيل'),
    '案内ページ':
        ('Information page',
         'صفحة المعلومات'),
    'いま困っていることを書く':
        ('Write what you are stuck on',
         'اكتب ما يصعب عليك'),
    '知っている研究会を知らせる':
        ('Tell us about a meeting you know of',
         'أخبرنا بلقاء تعرفه'),
    '写真3枚まで／PDF1つまで／その場で撮ってもOK 隠したいところは、このページの上で消せます':
        ('Up to 3 photos, up to 1 PDF. Taking a photo right now is fine. Anything you want hidden can be blacked out on this page.',
         'حتى ٣ صور وملفّ PDF واحد. ولا بأس بالتقاط صورة الآن. وما تريد إخفاءه يمكن طمسه داخل هذه الصفحة.'),
    '写真1枚だけで大丈夫です。ログインもメールも要りません。 内容とお名前だけ、書いてください。名前をサイトに出すかどうかは、下で選べます。':
        ('One photo is enough. No login, no email address. Just write what it was and your name. Whether your name appears on the site is your choice, below.',
         'تكفي صورة واحدة. لا تسجيل دخول ولا بريد إلكتروني. اكتب ما جرى واسمك فقط، ولك أن تختار أدناه إظهار اسمك على الموقع من عدمه.'),
    '隠したいところを、指でなぞってください。 なぞった四角が、黒くぬりつぶされます。 ぬったものが送られます。元の写真は、どこにも出ていきません。':
        ('Trace over anything you want hidden. The rectangle you trace is filled in black. What is sent is the blacked-out version — the original photo never leaves your device.',
         'مرّر إصبعك على ما تريد إخفاءه، فيُملأ المستطيل الذي رسمته بالأسود. والمُرسَل هو النسخة المطموسة؛ أمّا الصورة الأصلية فلا تغادر جهازك أبدًا.'),
    '1つだけ押してください。押したもののカードに集まります。 学級活動(1)(2)(3)は、ぜんぶ「学級活動」のカードへ。':
        ('Press one only. It will be gathered on that card. Classroom Activities (1), (2) and (3) all go to the “Classroom Activities” card.',
         'اضغط واحدًا فقط، فيُجمع على تلك البطاقة. وأنشطة الفصل (١) و(٢) و(٣) تذهب جميعها إلى بطاقة «أنشطة الفصل».'),
    '1つだけ押してください。押したもののカードに集まります。 その内容の実践と、同じところに並びます。':
        ('Press one only. It will be gathered on that card, alongside the practices for the same one of the four.',
         'اضغط واحدًا فقط، فيُجمع على تلك البطاقة إلى جانب الممارسات من النوع نفسه.'),
    '押すと入ります。いくつでも押せます。もう一度押すと外れます。':
        ('Press to add. You can press as many as you like. Press again to remove.',
         'اضغط للإضافة، ولك أن تضغط ما شئت، واضغط ثانية للإزالة.'),
    'いちばん伝えたいことを、ひとことで。題のすぐ下に、大きく出ます。':
        ('The one thing you most want to get across, in a single line. It appears large, just under the title.',
         'أهمّ ما تودّ إيصاله في سطر واحد، ويظهر كبيرًا تحت العنوان مباشرة.'),
    'ひとことでも大丈夫です。長く書く必要はありません。':
        ('A single line is fine. There is no need to write at length.',
         'يكفي سطر واحد، ولا داعي للإطالة.'),
    '学校名や子どもの名前は書かないでください。そのまま出ます。':
        ('Please do not write the school name or children’s names. It goes out exactly as written.',
         'من فضلك لا تكتب اسم المدرسة ولا أسماء الأطفال؛ فما تكتبه يُنشر كما هو.'),
    'サイトに出ます。 書いていただいたぶんが溜まったら、地図からさがせるようにします。 自治体は、書きたいときだけで大丈夫です（区や市でちがう、を言えるように）。':
        ('This appears on the site. Once enough has been written in, we will make it searchable from a map. The municipality is optional — it is there so you can say that things differ from ward to ward.',
         'يظهر هذا على الموقع. ومتى تجمّع ما يكفي، سنجعل البحث ممكنًا من خريطة. أمّا البلدية فاختيارية، وُضعت كي تتمكّن من بيان اختلاف الأمور بين حيّ وآخر.'),
    '2日開催のときだけ。1日で終わる会は、空のままで。':
        ('Only for two-day meetings. Leave it empty if it finishes in one day.',
         'لِلقاءات اليومين فقط. اتركه فارغًا إن انتهى في يوم واحد.'),
    '入れると、こよみに点線の丸で出ます。':
        ('If you fill this in, it shows on the calendar as a dotted circle.',
         'إن ملأته، ظهر في التقويم كدائرة منقّطة.'),
    '学年・内容・始まる時こく・講師など。10字以上。 名前と日付だけ並べるのは、このサイトではやらないと決めています。':
        ('Year group, content, start time, speaker and so on — at least ten characters. Listing nothing but a name and a date is something this site has decided not to do.',
         'الصف والمحتوى ووقت البدء والمحاضر ونحوها، بعشرة محارف على الأقل. أمّا سرد الاسم والتاريخ فحسب فقد قرّر هذا الموقع ألّا يفعله.'),
    '主催の公式ページがあれば。押した人だけが、外へ出ます。':
        ('The organiser’s official page, if there is one. Only whoever presses it leaves the site.',
         'الصفحة الرسمية للجهة المنظِّمة إن وُجدت. ولا يغادر الموقع إلا من يضغطها.'),
    '送るまえに かならず子どもの顔や名前、学校名が写っていないか見てください。押すと、そのまま公開のページに出ます。 写っていても、撮り直さなくて大丈夫です。隠したいところは、このページの上で消せます。':
        ('Before you send, please check for children’s faces, names and the school name. What you send goes straight onto the public page. If something is in the photo you do not have to reshoot it — you can black it out on this page.',
         'قبل الإرسال، تحقّق من وجوه الأطفال وأسمائهم واسم المدرسة. فما تُرسله يظهر مباشرة على الصفحة العامّة. وإن ظهر شيء منها فلا حاجة لإعادة التصوير؛ يمكنك طمسه داخل هذه الصفحة.'),
    '送るまえに かならず学校名・子どもの名前・同僚の名前が入っていないか見てください。押すと、そのまま公開のページに出ます。':
        ('Before you send, please check for the school name and the names of children and colleagues. What you send goes straight onto the public page.',
         'قبل الإرسال، تحقّق من اسم المدرسة وأسماء الأطفال والزملاء. فما تُرسله يظهر مباشرة على الصفحة العامّة.'),
    '送るまえに かならず主催の案内と、日づけを見くらべてください。押すと、そのまま公開のこよみに出ます。':
        ('Before you send, please check the date against the organiser’s own announcement. What you send goes straight onto the public calendar.',
         'قبل الإرسال، قارن التاريخ بإعلان الجهة المنظِّمة نفسها. فما تُرسله يظهر مباشرة في التقويم العامّ.'),
    '押すと、そのまま上のこよみに出ます。数分かかります。 公になっている会だけにしてください。校内の予定は載せられません。':
        ('It goes straight onto the calendar above; that takes a few minutes. Please only send meetings that are already public. In-school schedules cannot go up.',
         'يظهر مباشرة في التقويم أعلاه خلال دقائق. ومن فضلك أرسل اللقاءات المعلَنة فقط؛ فالجداول الداخلية للمدرسة لا تُنشر.'),

    # ── このサイトを紹介する（2026-09-23）──
    'このサイトを紹介する':
        ('Tell others about this site',
         'عرِّف الآخرين بهذا الموقع'),
    '研修の資料や学級だよりに貼れる、QRコードつきの1枚を作ります。<br> 読みこむと、このサイトのホームがひらきます。':
        ('Makes a single sheet with a QR code, to paste into training materials '
         'or a class newsletter.<br> Scanning it opens this site’s home page.',
         'يُنشئ ورقة واحدة برمز QR، تُلصق في مواد التدريب أو نشرة الفصل.<br> '
         'ومسحُه يفتح الصفحة الرئيسية لهذا الموقع.'),
    '画面のQRに、そのままカメラを向けても開きます。<br> 紙に貼るなら、下から1枚の絵として保存してください。':
        ('You can also point a camera straight at the QR on screen.<br> '
         'To put it on paper, save it below as a single image.',
         'ويمكنك أيضًا توجيه الكاميرا إلى الرمز على الشاشة مباشرة.<br> '
         'ولوضعه على الورق، احفظه أدناه كصورة واحدة.'),
    'はじめかた このサイトを紹介する すぐ使える道具':
        ('How to start · Tell others · Tools you can use now',
         'كيف تبدأ · عرِّف الآخرين · أدوات جاهزة'),
}

# 訳を付ける場所。( 正規表現, 何の場所か ) の並び。
#   正規表現は3つ以上の ( ) に分けます … 前の札／中の字／後ろの札。
#   中の字を表で引いて、前の札に data-en / data-ar を足します。
KOTOBA_TEKI = (
    (r'(<span class="ja">)(.*?)(</span>)', '節の見出し'),
    (r'(<p class="yomi[^"]*">)(.*?)(</p>)', '節の説明'),
    (r'(<a class="obi-s[^"]*"[^>]*>)(.*?)(</a>)', '帯'),
    (r'(<b class="hfuda-h">)(.*?)(</b>)', '札の名前'),
    (r'(<span class="hfuda-yo">)(.*?)(</span>)', '札のひとこと'),
    (r'(<b class="gfuda-h">)(.*?)(</b>)', '概要の札の名前'),
    (r'(<span class="gfuda-yo">)(.*?)(</span>)', '概要の札のひとこと'),
    (r'(<span class="gfuda-go">)(.*?)(</span>)', '概要の札のボタン'),
    (r'(<p class="hero-copy">)(.*?)(</p>)', 'ヒーローのコピー', 'ji'),
    (r'(<p class="igi-bun">)(.*?)(</p>)', 'このサイトは、なに'),
    (r'(<b>)([^<]+)(</b><span class="t">)([^<]+)(</span>)', '4人の札'),
    (r'(<h1 class="ko-h">)(.*?)(</h1>)', 'ページの名前'),
    (r'(<p class="ko-yo">)(.*?)(</p>)', 'ページのひとこと'),
    (r'(<a class="ko-oya"[^>]*>)(.*?)(</a>)', '親への戻り道'),
    (r'(<p class="foot-koe">)(.*?)(</p>)', '足もとの1行'),
    (r'(<span class="kanri-na">)(.*?)(</span>)', '管理者'),
    (r'(<a class="btn"[^>]*href="\#okuru"[^>]*>)(実践を送る)(<span)', 'ヒーローのボタン1'),
    (r'(<a class="btn btn--usu"[^>]*>)(みんなの実践を見る)(<span)', 'ヒーローのボタン2'),
    (r'(<a class="kanri-a"[^>]*>)(.*?)(</a>)', '管理画面へ'),
    (r'(<span class="btn-ji">)(.*?)(</span>)', 'ボタンの字'),
    (r'(<a class="line-sumi"[^>]*>)(.*?)(</a>)', 'いちばん上のLINEの帯'),

    # ── 送るところ（2026-09-23 追加）────────────────────────
    #   このサイトの目玉です。ここが日本語のままだと、外の先生は
    #   「見るだけ」になります。
    (r'(<p class="okuru-midashi">)(.*?)(</p>)', '送る・見出し'),
    (r'(<p class="okuru-yomi[^"]*">)(.*?)(</p>)', '送る・説明', 'ji'),
    (r'(<span class="okuru-shashin-ji">)(.*?)(</span>)', '送る・写真をえらぶ'),
    (r'(<span class="okuru-shashin-chu">)(.*?)(</span>)', '送る・写真の注', 'ji'),
    (r'(<label class="okuru-l"[^>]*>)([^<]+)(<span)', '送る・欄の名前'),
    (r'(<span class="okuru-l"[^>]*>)([^<]+)(<span)', '送る・欄の名前2'),
    (r'(<span class="okuru-hissu">)(.*?)(</span>)', '送る・必須'),
    (r'(<span class="okuru-nin">)(.*?)(</span>)', '送る・任意'),
    (r'(<p class="okuru-check-chu">)(.*?)(</p>)', '送る・チェックの注', 'ji'),
    (r'(<p class="okuru-kiwo">)(.*?)(</p>)', '送る・気をつけること', 'ji'),
    (r'(<p class="kakusu-yomi">)(.*?)(</p>)', '隠すところの説明', 'ji'),
    (r'(<p class="hero-slide">)(.*?)(</p>)', 'よこにスライド'),
    (r'(<a class="skip">)(.*?)(</a>)', '本文へ進む'),
    (r'(<span class="moji-l">)(.*?)(</span>)', '字の大きさ'),

    # ── ことばの意味（2026-09-23 追加）──────────────────────
    (r'(<h3 class="kotoba-go">)(.*?)(</h3>)', 'ことば・見出し語'),
    (r'(<p class="kotoba-setsu">)(.*?)(</p>)', 'ことば・説明', 'ji'),
    (r'(<label class="sagasu-l"[^>]*>)(.*?)(</label>)', 'さがす欄の名前'),
    (r'(<p class="shokai-yo">)(.*?)(</p>)', '紹介の説明'),
)


# --kotoba のときだけ、止めずに集めます（ふだんは None ＝ 1個でも欠けたら止まる）
KOTOBA_TARINAI = None


def kotoba_hiku(ji, doko, nai):
    """表から訳を引く。無ければ nai に積む（積んだぶんは、あとでまとめて出します）。"""
    key = re.sub(r'\s+', ' ', ji).strip()
    if key not in KOTOBA:
        nai.append((doko, key))
        return None
    yaku = KOTOBA[key]
    if not yaku[0] or not yaku[1]:
        nai.append((doko, key))
        return None
    return yaku


_TAGU = re.compile(r'<[^>]+>')


def kotoba_ireru(html, f):
    """訳を data-en / data-ar として、その場に足す。
       ページの中の仕掛けは、この2つを入れかえるだけです。外へは何も出ません。

       ★もう data-en を持っている場所（札の数など）は、そのままにします。
         数はその場で数えるものなので、表ではなく home_kazu が訳を作ります。"""
    nai, ima = [], ['', '']

    def fuda(mae, yaku):
        """開き札に data-en / data-ar を足す。"""
        return '%s data-en="%s" data-ar="%s">' % (
            mae[:-1], esc_html(yaku[0]), esc_html(yaku[1]))

    def hen(m):
        g = list(m.groups())
        if 'data-en="' in g[0]:
            return m.group(0)
        if len(g) == 5:                     # 4人の札（<b>…</b><span class="t">…</span>）
            a = kotoba_hiku(g[1], ima[0], nai)
            b = kotoba_hiku(g[3], ima[0], nai)
            if not a or not b:
                return m.group(0)
            return ('<b data-en="%s" data-ar="%s">%s</b>'
                    '<span class="t" data-en="%s" data-ar="%s">%s</span>'
                    % (esc_html(a[0]), esc_html(a[1]), g[1],
                       esc_html(b[0]), esc_html(b[1]), g[3]))
        key = _TAGU.sub('', g[1]) if ima[1] == 'ji' else g[1]
        yaku = kotoba_hiku(key, ima[0], nai)
        if not yaku:
            return m.group(0)
        return '%s%s%s' % (fuda(g[0], yaku), g[1], g[2])

    for teki in KOTOBA_TEKI:
        pat, na = teki[0], teki[1]
        ima[0], ima[1] = na, (teki[2] if len(teki) > 2 else '')
        html = re.sub(pat, hen, html, flags=re.S)
    if nai and KOTOBA_TARINAI is not None:
        # python3 build.py --kotoba … 6枚ぜんぶを1回で集めて、表に貼る形で出します
        KOTOBA_TARINAI.extend(nai)
        return html
    if nai:
        mi = ["    %s: ('', ''),   # %s" % (repr(key), doko)
              for doko, key in sorted(set(nai))]
        raise Tomeru('公開用/%s に、訳の無い言葉が %d 個あります。\n'
                     '     build.py の KOTOBA に、下の行をそのまま足して、'
                     "空の '' を埋めてください（英語, アラビア語）：\n\n%s\n"
                     % (f, len(set(nai)), '\n'.join(mi)))
    return html


def tsunagi_naosu(html, ima_file, doko, tsune):
    """<a href="#◯◯"> の行き先が別のページになったぶんを、書きかえる。
       SVG の <use href="#ill-…"> は触りません（<a> だけを見ます）。"""
    machigai = []

    def hen(m):
        mae, x, ato = m.groups()
        if not x or x in tsune:
            return m.group(0)
        saki = doko.get(x)
        if saki is None:
            machigai.append(x)
            return m.group(0)
        return m.group(0) if saki == ima_file else '%s%s#%s%s' % (mae, saki, x, ato)

    out = re.sub(r'(<a\b[^>]*?\shref=")#([^"]*)(")', hen, html)
    if machigai:
        raise Tomeru('%s の中に、行き先の無いリンク #%s があります。'
                     'その id を持つ節が、どのページにもありません'
                     % (ima_file, '、#'.join(sorted(set(machigai)))))
    return out


def build_shin():
    _GOUKEI.clear()
    buhin, hyo = load_buhin()
    kyara = load_kyara()
    shirushi = load_mark()
    kiji, _ = load_news()
    goods = load_goods()
    jissen, _ = load_jissen(goods)
    body = rd('src/hiroba.html')

    if not kiji:
        raise Tomeru('出せるニュースが1件もありません')
    if not jissen:
        raise Tomeru('出せる実践が1件もありません')

    ken = load_kenkyukai()
    komari, tobashita_k = load_komari()
    # 採用済みの学校全景。4つの活動を切らずに、そのまま見せる。
    #   ★ホームだけは <use> ではなく「本物」を出します（2026-09-23 依頼）。
    #     <use> の中は CSS が届かず、子どもも雲も動かせないためです。
    #     絵は1枚しか入らないので、重さは前と変わりません
    #     （build_tane が、本物がある版には入れ物を作りません）。
    hero_w, hero_h, e_naka = load_approved_svg('school.svg', ugokasu=True)
    hero = ('<svg viewBox="0 0 %g %g" role="img" '
            'aria-label="花の咲く学校で、学級会・運動会・児童会の集会・クラブの共同制作をする子どもたち">'
            '<g id="ill-hiroba">%s</g></svg>' % (hero_w, hero_h, e_naka))

    for mark, html in (('<!--BUILD:HIROBA-->', hero),
                       ('<!--BUILD:COPY-->',   build_copy(TOBIRA_COPY)),
                       ('    <!--BUILD:YOTSU-->',  build_yotsu(kyara, jissen, komari)),
                       ('      <!--BUILD:NAYAMI-->', build_nayami(komari)),
                       ('    <!--BUILD:KYARA-->',  build_kyara_narabi(kyara)),
                       ('    <!--BUILD:JISSEN_H-->', build_jissen_hiroba(jissen, goods)),
                       ('    <!--BUILD:BANSHO_IRI-->', build_bansho_iriguchi(jissen)),
                       ('    <!--BUILD:FUSHIME-->', build_fushime(jissen, buhin)),
                       ('    <!--BUILD:OKURU_MIRU-->', build_okuru_miru(jissen)),
                       ('    <!--BUILD:KOMARI_MIRU-->', build_komari_miru(komari)),
                       ('    <!--BUILD:BANSHO-->',     build_bansho(jissen)),
                       ('    <!--BUILD:KOMARI-->',     build_komari(komari)),
                       ('          <!--BUILD:KEN-->', build_ken_options()),
                       ('    <!--BUILD:KOTOBA-->',   build_kotoba(load_kotoba())),
                       ('    <!--BUILD:KAI-->',      build_kai()),
                       ('    <!--BUILD:NEWS_H-->',   build_hyo_news(kiji)),
                       ('    <!--BUILD:KENKYUKAI-->',
                        build_kenkyukai(ken, kyara, buhin))):
        if mark not in body:
            raise Tomeru('src/hiroba.html に目じるし %s がありません' % mark.strip())
        body = body.replace(mark, html)

    body = storage_ireru(body, 'src/hiroba.html')
    body = nuru_ireru(body, 'src/hiroba.html')
    body, _ = build_kazari(body, buhin, kyara)

    for k, v in LINKS.items():
        body = body.replace('{{%s}}' % k, v)
    # 前は1枚ものだったころの行き先（#jissen など）を、いまのページへ送る表。
    # ページを分けるまえに配ったURLを、生かしたままにするためです。
    if '{{SAKI}}' not in body:
        raise Tomeru('src/hiroba.html の仕掛けに {{SAKI}} がありません'
                     '（古い行き先を、いまのページへ送れなくなります）')
    body = body.replace('{{SAKI}}', '{%s}' % ','.join(
        '"%s":"%s"' % (s, f) for f, _, _, ss in PAGES for s in ss))
    nokori = re.findall(r'\{\{([A-Z_]+)\}\}', body)
    if nokori:
        raise Tomeru('src/hiroba.html に、LINKS に無い目じるしがあります： %s'
                     % '、'.join(sorted(set(nokori))))
    nokori_mark = re.findall(r'<!--BUILD:[^>]*-->', body)
    if nokori_mark:
        raise Tomeru('差しこまれていない目じるしが残っています： %s' % '、'.join(nokori_mark))

    # ── ここから、1枚をページごとに切り分けます ──────────────
    hero, sec, foot, shikake = wakeru(body)
    sec = midashi_kao(sec, kyara)

    # どの id が、どのページに載るか。これで <a href="#◯◯"> を張りなおします
    doko = {}
    for f, _, _, setsu in PAGES:
        for s in setsu:
            for i in re.findall(r'\sid="([^"]+)"', sec[s]):
                doko[i] = f
    # 頭と足もとは、どのページにも同じものが載ります（張りかえません）
    tsune = set(re.findall(r'\sid="([^"]+)"', hero + foot)) | {'ue'}

    home_html, home_e = build_home(doko, sec, shirushi, kiji, jissen, ken, komari)
    for i in re.findall(r'\sid="([^"]+)"', home_html):
        doko[i] = HOME

    gaiyo_html = build_gaiyo(sec, doko, kiji, jissen, ken, komari)
    for i in re.findall(r'\sid="([^"]+)"', gaiyo_html):
        doko[i] = HOME

    igi_html = build_igi(kyara)
    for i in re.findall(r'\sid="([^"]+)"', igi_html):
        doko[i] = HOME

    pages = {}
    for f, na, yo, setsu in PAGES:
        if f == HOME:
            # ホームの並び … このサイトは、なに → 8つの札 → こよみ → 中身をざっと
            atama, saki = hero, 'igi'
            naka_html = '\n\n'.join([igi_html, home_html]
                                    + [sec[s] for s in setsu] + [gaiyo_html])
        else:
            atama = ko_atama(f, yo)
            naka_html, saki = '\n\n'.join(sec[s] for s in setsu), setsu[0]
        p = '\n'.join(['<a class="skip" href="#%s">本文へ進む</a>' % saki,
                       atama, build_obi(f, doko), naka_html, foot, shikake])
        p = tsunagi_naosu(p, f, doko, tsune)
        # ことばの切りかえ（日本語 / English / العربية）。
        # 訳を data-en / data-ar としてその場に足します。外へは何も出ません。
        p = kotoba_ireru(p, f)
        html = '\n'.join([
            '<!DOCTYPE html>', '<html lang="ja" dir="ltr">', '<head>',
            head_de(f, na), '<style>',
            rd(CSS_H) + (''.join(UGOKI_CSS) if f == HOME else ''),
            '</style>', '</head>',
            '<body>',
            build_tane(p, e_naka, buhin, kyara, shirushi,
                       None if f == HOME else ko_e_naka(f, buhin, kyara)),
            p, '</body>', '</html>',
        ]) + '\n'
        ngword_check(html, '公開用/' + f)
        pages[f] = html
    kanri = build_kanri_page(jissen, komari, ken,
                             list(tobashita_k) + list(NITTEI_TOBASHITA))
    ngword_check(kanri, '公開用/kanri.html')
    pages['kanri.html'] = kanri
    return pages, hyo, kiji, jissen, komari, tobashita_k


# ══════════════════════════════════════════════════════════
# 4. とびら版（入口の試作）
# ══════════════════════════════════════════════════════════

def build_copy(s):
    return ''.join('<span style="--i:%d">%s</span>' % (i, esc_html(c))
                   for i, c in enumerate(s))


def build_tobira():
    # 方向A：部品を組んで広場をつくる
    buhin, hyo = load_buhin()
    kiji, tobashita = load_news()
    body = rd('src/tobira.html')

    if '<!--BUILD:HIROBA-->' not in body:
        raise Tomeru('src/tobira.html に目じるし <!--BUILD:HIROBA--> がありません')
    body = body.replace('<!--BUILD:HIROBA-->', hiroba_svg(buhin))
    body = body.replace('<!--BUILD:COPY-->', build_copy(TOBIRA_COPY))

    ima = kiji[0]
    body = body.replace(
        '  <!--BUILD:IMASHU-->',
        '  <p class="tb-ima"><span class="lb">今週</span>'
        '<a href="%s" target="_blank" rel="noopener noreferrer">%s</a>'
        '<span class="ext">外部</span></p>'
        % (esc_html(ima['url']), esc_html(ima.get('home') or ima['title'])))

    for k, v in LINKS.items():
        body = body.replace('{{%s}}' % k, v)
    nokori = re.findall(r'\{\{([A-Z_]+)\}\}', body)
    if nokori:
        raise Tomeru('src/tobira.html に、LINKS に無い目じるしがあります： %s'
                     % '、'.join(sorted(set(nokori))))
    nokori_mark = re.findall(r'<!--BUILD:[^>]*-->', body)
    if nokori_mark:
        raise Tomeru('差しこまれていない目じるしが残っています： %s' % '、'.join(nokori_mark))

    html = '\n'.join([
        '<!DOCTYPE html>', '<html lang="ja" dir="ltr">', '<head>',
        rd('src/head.html'), '<style>', rd(CSS_T), '</style>', '</head>',
        '<body>', body, '</body>', '</html>',
    ]) + '\n'
    ngword_check(html, '公開用/tobira.html')
    return html, hyo, kiji


def _lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def akarusa(hexs):
    h = hexs.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a, b):
    la, lb = akarusa(a), akarusa(b)
    if la < lb:
        la, lb = lb, la
    return (la + 0.05) / (lb + 0.05)


# （文字の色, 地の色, どこの話か）。名前は style-tobira.css の :root から読む
COLOR_PAIRS = [
    ('ink',    'bg',   '本文と問い'),
    ('mute',   'bg',   '添え字'),
    ('accent', 'bg',   'リンク'),
]


def tenken_tobira(html):
    warn = tenken(html)
    warn = [w for w in warn if '要約' not in w]      # とびらにニュースの要約は載せない

    css = rd(CSS_T)

    # ① 空の高さ。超えると1枚目のカードが最初の画面から落ちる
    m = re.search(r'--sora-h\s*:\s*([\d.]+)svh', css)
    if m and float(m.group(1)) > SORA_H_MAX:
        raise Tomeru('--sora-h が %ssvh です。%dsvh を超えると、カードの1枚目が'
                     '最初の画面から落ちます' % (m.group(1), SORA_H_MAX))

    # ② 動きを止める設定に従うか
    if 'prefers-reduced-motion' not in css:
        raise Tomeru('%s に @media (prefers-reduced-motion: reduce) がありません' % CSS_T)

    # ③ コントラスト（CSSに書いてある値そのもので測る＝あとでずれない）
    iro = dict(re.findall(r'--([a-z-]+)\s*:\s*(#[0-9A-Fa-f]{6})', css))
    hyo = []
    for moji, ji, doko in COLOR_PAIRS:
        if moji not in iro or ji not in iro:
            continue
        h = contrast(iro[moji], iro[ji])
        hyo.append((doko, iro[moji], iro[ji], h))
        if h < 4.5:
            raise Tomeru('%s：%s を %s に置くと %.2f:1 で、4.5:1 に届きません（読めません）'
                         % (doko, iro[moji], iro[ji], h))

    # ④ 大きさ
    kb = len(html.encode('utf-8')) / 1024.0
    if kb > TOBIRA_KB_MAX:
        raise Tomeru('tobira.html が %.0fKB あります（上限 %.0fKB）' % (kb, TOBIRA_KB_MAX))

    return warn, hyo


# ══════════════════════════════════════════════════════════
# 5. 入口
# ══════════════════════════════════════════════════════════

def main_tobira(check_only):
    try:
        html, hyo, kiji = build_tobira()
        warn, hyo_iro = tenken_tobira(html)
    except Tomeru as e:
        print('')
        print('  ✕ ビルドを止めました')
        print('     %s' % e)
        print('')
        return 1

    kb = len(html.encode('utf-8')) / 1024.0
    print('')
    print('  広場　　　　… 部品%d種・図形%d個' % (len(hyo), sum(h[3] for h in hyo)))
    print('  コントラスト… 全部 4.5:1 以上')
    for doko, a, b, h in hyo_iro:
        print('     %-22s %s on %s  %.2f:1' % (doko, a, b, h))
    print('  今週　　　　… %s' % (kiji[0].get('home') or kiji[0]['title']))
    print('  出来上がり　… 公開用/tobira.html  %.0fKB' % kb)
    for w in warn:
        print('  ⚠ %s' % w)

    if check_only:
        print('')
        print('  --check なので書いていません。')
        print('')
        return 0
    io.open(OUT_T, 'w', encoding='utf-8', newline='\n').write(html)
    print('')
    print('  書きました。これは入口の試作です（段1）。')
    print('  公開用/tobira.html をそのままブラウザで開けます。')
    print('  （本体 公開用/index.html には手を触れていません）')
    print('')
    return 0


def main_shin(check_only):
    try:
        pages, hyo, kiji, jissen, komari, tobashita_k = build_shin()
        warn = []
        for f in pages:
            warn += [w for w in tenken(pages[f]) if '要約' not in w]
    except Tomeru as e:
        print('')
        print('  ✕ ビルドを止めました')
        print('     %s' % e)
        print('')
        return 1
    print('')
    print('  新版（ホーム＋%dページ＋管理画面）' % (len(PAGES) - 1))
    print('  広場　　　　… 部品%d種・図形%d個。ページごとに、呼んだ絵だけを埋めこみ'
          % (len(hyo), sum(h[3] for h in hyo)))
    print('  4つの内容　… %s'
          % '、'.join('%s（悩み%d・実践%d）'
                     % (ja, sum(1 for a in komari if a['naiyo'] == nid),
                        sum(1 for a in jissen if a['naiyo'] == nid))
                     for nid, ja in naiyo_ichiran()))
    print('  悩み　　　　… %d件（うち %d件に答えが付いています）'
          % (len(komari), sum(1 for a in komari if a['saki'])))
    print('  実践　　　　… %d件（うち議題が%d件。ぜんぶ、中身までこのページに）'
          % (len(jissen), sum(1 for a in jissen if a['kind'] == 'gidai')))
    print('  板書　　　　… %d件・%d枚（写真は bansho.html にだけ入れています）'
          % (len(bansho_aru(jissen)),
             sum(bansho_kazu(a['bansho']) for a in bansho_aru(jissen))))
    print('  困りごと　　… %d件（送られたら、そのまま出ます）' % len(komari))
    for t in tobashita_k:
        print('  とばした　　… %s' % t)
    print('  ニュース　　… %d件（上から%d件。のこりはページの中のふた）'
          % (len(kiji), min(len(kiji), NEWS_H_N)))
    ken_zen = load_kenkyukai()
    print('  こよみ　　　… %d件を %dか月ぶんのますめに（うち %d件は、サイトから送られたぶん）'
          % (len(ken_zen), KOYOMI_TSUKI_MAX,
             sum(1 for a in ken_zen if a.get('okuri'))))
    for t in NITTEI_TOBASHITA:
        print('  とばした日程… %s' % t)
    print('  ほかの研究会… %d会（全国%d・都道府県%d・市%d）'
          % (len(KAI), sum(1 for k in KAI if k[0] == 'zen'),
             sum(1 for k in KAI if k[0] == 'ken'), sum(1 for k in KAI if k[0] == 'shi')))
    print('  出来上がり　…')
    for f, na, _, setsu in PAGES:
        kb = len(pages[f].encode('utf-8')) / 1024.0
        omo = ('%.1fMB' % (kb / 1024.0)) if kb >= 1024 else ('%.0fKB' % kb)
        print('　　%-14s %-8s %s%s'
              % (f, na, omo, ('　' + '・'.join(SETSU_NA[s] for s in setsu)) if setsu else
                 '　8つの札'))
    print('　　%-14s %-8s %.0fKB　受け口で管理キーを確認'
          % ('kanri.html', '実践の管理', len(pages['kanri.html'].encode('utf-8')) / 1024.0))
    # ── 板書の残り（2026-09-21）────────────────────────
    #   溜めると決めたので、**止まる前に教える**ほうを作ります。
    #   検問は16MBで止めますが、止まってから気づくのでは遅い。
    tsukatta = _GOUKEI.get('bansho.html', 0) / 1024.0 / 1024.0
    nokori = SHIRYO_ZEN_MAX - tsukatta
    mai = int(nokori * 1024.0 / BANSHO_NOKORI_KB)
    print('  板書の残り　… %.1fMB / %.0fMB を使いました。'
          'あと %d枚ぶん（1枚 %.0fKB として）' % (tsukatta, SHIRYO_ZEN_MAX, mai,
                                                  BANSHO_NOKORI_KB))
    if tsukatta > SHIRYO_ZEN_MAX * 0.7:
        warn.append('板書のページが %.1fMB になりました（上限 %.0fMB）。'
                    'そろそろ年度で分けるときです。'
                    'PAGES に bansho-2027.html を足して、新しいぶんをそちらへ。'
                    % (tsukatta, SHIRYO_ZEN_MAX))
    for w in warn:
        print('  ⚠ %s' % w)
    if check_only:
        print('\n  --check なので書いていません。\n')
        return 0
    for f in pages:
        io.open(os.path.join(ROOT, '公開用', f), 'w',
                encoding='utf-8', newline='\n').write(pages[f])
    sitemap_kaku(pages)
    pdfjs_utsusu()
    print('')
    print('  書きました。入口は 公開用/index.html（ホーム）です。')
    print('  公開用/ は GitHubに上げません（.gitignore）。上げるのは src/ と build.py。')
    print('  push すると Actions が同じように組み立てて、%d枚とも Pages へ出します。'
          % len(pages))
    print('')
    return 0


# ══ 検索に見つけてもらうための2枚（2026-09-23 依頼）════════
#   noindex を外しただけでは、すぐには拾われません。
#   ★sitemap.xml … 出してよいページだけを並べます（DASANAI は入れません）
#   ★robots.txt  … 出さないページを、そもそも見に来させません
#                   （HTMLの noindex は「読んでから外す」ので、
#                     写真の重いページを読ませずに済むほうが確かです）
#   どちらも .github/workflows/build.yml で _site へ写します。

def sitemap_kaku(pages):
    dasu = [f for f in pages if f not in DASANAI]
    hi = kyou_jst().isoformat()
    url = ''.join(
        '  <url><loc>%s%s</loc><lastmod>%s</lastmod></url>\n'
        % (SITE_URL, '' if f == HOME else f, hi)
        for f in dasu)
    io.open(os.path.join(ROOT, '公開用', 'sitemap.xml'), 'w',
            encoding='utf-8', newline='\n').write(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + url + '</urlset>\n')
    io.open(os.path.join(ROOT, '公開用', 'robots.txt'), 'w',
            encoding='utf-8', newline='\n').write(
        '# 管理画面は、見に来ないでください。\n'
        '# みんなの実践と困りごとは、検索に出します（写真だけは\n'
        '# HTMLの noimageindex で、画像検索に載せないようお願いしています）。\n'
        'User-agent: *\n'
        + ''.join('Disallow: /tokkatsu-hiroba/%s\n' % f for f in DASANAI)
        + '\nSitemap: %ssitemap.xml\n' % SITE_URL)
    print('  検索　　　　… %d枚を sitemap.xml に。%d枚は出しません（%s）。'
          % (len(dasu), len(DASANAI), '・'.join(DASANAI)))
    print('  　　　　　　　 %s は 字だけ出します（写真は画像検索に載せません）'
          % '・'.join(KAKUSU_E))


PDFJS = os.path.join(SRC, 'pdfjs')   # PDFを、送る人のブラウザの中で絵にする道具


def pdfjs_utsusu():
    """src/pdfjs/*.js を 公開用/pdfjs/ に写す。

       ページの中に入れません。**PDFを選んだ人だけ**が取りに行くものなので、
       埋めこむと、読むだけの人まで1.7MB 背負うことになります。
       外のCDNからも読みません。学校のネットワークは外のCDNを止めている
       ことがよくあり、止められるとPDFが送れなくなるためです。"""
    import shutil
    saki = os.path.join(ROOT, '公開用', 'pdfjs')
    if not os.path.isdir(PDFJS):
        raise Tomeru('src/pdfjs/ がありません。PDFを塗るところが動かなくなります')
    os.makedirs(saki, exist_ok=True)
    n = 0
    for f in sorted(glob.glob(os.path.join(PDFJS, '*.js'))):
        shutil.copyfile(f, os.path.join(saki, os.path.basename(f)))
        n += 1
    if n < 2:
        raise Tomeru('src/pdfjs/ に .js が %d個しかありません（本体と裏方の2つが要ります）' % n)
    print('  PDFの道具　… %d個を 公開用/pdfjs/ に写しました（%.1fMB。'
          'ページには入れません）'
          % (n, sum(os.path.getsize(x) for x in glob.glob(os.path.join(saki, '*.js')))
             / 1024.0 / 1024.0))


def main():
    check_only = '--check' in sys.argv
    simple     = '--simple' in sys.argv          # デザインだけ差しかえた簡素版を出す

    # --kotoba … 止めずに、6枚ぜんぶの「訳の無い言葉」を1回で集めます。
    #   ふだんは1個でも欠けたら止まる（＝日本語のまま公開されない）ままです。
    if '--kotoba' in sys.argv:
        global KOTOBA_TARINAI
        KOTOBA_TARINAI = []
        main_shin(check_only=True)
        mi = sorted(set(KOTOBA_TARINAI))
        print('\n  訳の無い言葉 %d個。下をそのまま KOTOBA に貼って、'
              "'' を埋めてください（英語, アラビア語）。\n" % len(mi))
        for doko, key in mi:
            print("    %s: ('', ''),   # %s" % (repr(key), doko))
        return 0

    if '--tobira' in sys.argv:
        return main_tobira(check_only)
    if '--buhin' in sys.argv:
        return main_buhin()
    # 2026-09-21：公開するものは新版になりました。
    # 何も足さずに動かすと、新版を 公開用/index.html に書きます。
    # 旧・本体（タブで切りかえる版）を出したいときだけ --kyu を足します。
    if '--kyu' not in sys.argv:
        return main_shin(check_only)

    css, out_path, out_name = ((CSS_S, OUT_S, '公開用/index-simple.html') if simple
                               else (CSS, OUT_KYU, '公開用/index-kyu.html'))
    try:
        html, kiji, tobashita, jissen, goods = build(css, out_name)
        warn = tenken(html)
    except Tomeru as e:
        print('')
        print('  ✕ ビルドを止めました')
        print('     %s' % e)
        print('')
        return 1

    kb = len(html.encode('utf-8')) / 1024.0
    ima = io.open(out_path, encoding='utf-8').read() if os.path.exists(out_path) else ''
    print('')
    print('  ニュース　　… %d件を書きこみ（ホームは上から%d件）'
          % (len(kiji), min(len(kiji), HOME_N)))
    for t in tobashita:
        print('  とばした　　… %s' % t)
    dekiru = sum(1 for g in goods.values() if goods_status(g))
    print('  実践　　　　… %d件を書きこみ（ホームは上から%d件）'
          % (len(jissen), min(len(jissen), JISSEN_HOME_N)))
    print('  グッズ　　　… %d点（配布できるもの %d点、準備中 %d点）'
          % (len(goods), dekiru, len(goods) - dekiru))
    print('  見た目　　　… %s' % ('簡素版（style-simple.css）' if simple else '旧・本体（style.css）'))
    print('  出来上がり　… %s  %.0fKB （これは公開しません。控えです）' % (out_name, kb))
    print('  いまの版と　… %s' % ('同じ' if ima == html else 'ちがう'))
    for w in warn:
        print('  ⚠ %s' % w)

    if check_only:
        print('')
        print('  --check なので書いていません。')
        print('')
        return 0
    io.open(out_path, 'w', encoding='utf-8', newline='\n').write(html)
    print('')
    if simple:
        print('  書きました。これは見てもらう用の簡素版です（旧・本体のデザイン違い）。')
    else:
        print('  書きました。旧・本体の控えです。公開するのは 公開用/index.html（新版）です。')
    print('')
    return 0


if __name__ == '__main__':
    sys.exit(main())
