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

import io, os, re, sys, glob, datetime, calendar

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(ROOT, 'src')
# 公開するのはこの1つだけ。2026-09-21 から、中身は新版（縦スクロール1枚）です。
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
    ('shiru.html',    '知る',   '特別活動って、なに。4つの内容は、どれ。',
     ('about', 'yotsu')),
    ('manabu.html',   'はじめかた', '学級会の学習過程と、一次資料と、持ち帰れる道具。',
     ('manabu', 'jissen')),
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
    'kai':    '日本の研究会', 'okuru': '実践を送る',
    # 2026-09-22：ここがこのサイトの主役です。
    #   「板書」は狭すぎました（いまは写真もPDFも議題も届きます）。
    #   ファイル名（bansho.html）と front matter の bansho: は、そのままです。
    #   URLは読まれないので変えません。配ったリンクも生きます。
    'bansho': 'みんなの実践', 'komari': '困りごと', 'kiku': 'ちょっと聞きたい',
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
    # 最初の段落が「ひとこと」。残りが本文
    parts = re.split(r'\n\s*\n', fm['summary'].strip(), maxsplit=1)
    fm['lead'] = parts[0].strip()
    fm['rest'] = parts[1] if len(parts) > 1 else ''
    if fm['lead'].startswith('#'):
        raise Tomeru('%s：本文は見出しではなく、ひとことの段落から始めてください' % f)
    return True, None


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
                        by=(KOMARI_BY.format(by=esc_html(a['by'])) if a['by'] else ''),
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


SHIRYO_MADO = """        <details class="hiraku shiryo-hiraku">
          <summary><span class="a">{midashi}を見る（{n}ページ）</span><span class="b">とじる</span></summary>
          <div class="shiryo-naka">
            <p class="shiryo-chu">このページの中に入っています。押しても外にはつながりません。</p>
            <div class="shiryo-mado">
{gazou}
            </div>
          </div>
        </details>
"""


def shiryo_mado(midashi, oki, alt, moto=None, page='manabu.html'):
    """資料1件ぶんの「ページの中で開く窓」。"""
    mai = shiryo_yomu(oki, moto, page)
    g = [GAZOU.format(uri=uri, alt=esc_html('%s %dページめ' % (alt, i + 1)),
                      w=w, h=h, i=i + 1, n=len(mai))
         for i, (uri, w, h) in enumerate(mai)]
    return SHIRYO_MADO.format(midashi=esc_html(midashi), n=len(mai), gazou='\n'.join(g))


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
    kyou = kyou or datetime.date.today()
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
    kyou = kyou or datetime.date.today()
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
    kyou = kyou or datetime.date.today()

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

# (範囲, 範囲の字, だれ向け, 会の名前, URL, 様子の1行, 置いてあるもののタグ)
KAI = (
    ('zen', '全国', '小・中・高',
     '全国特別活動研究会',
     'https://zentokkatsu.com/',
     '全国大会と冬季研・夏季ゼミの案内。この一覧そのものの出どころです。',
     ('大会案内', '各地の会の一覧')),
    ('zen', '全国', '小中高・研究者',
     '日本特別活動学会',
     'https://jaseatokkatsu.jimdoweb.com/',
     'オンラインの勉強会「特活カフェ」と研究会の案内。紀要と会報はPDFで読めます。',
     ('研究会案内', '紀要・会報PDF')),
    ('zen', '全国', '小学校',
     '特別活動 希望の会',
     'https://kibounokai.web.wox.cc/',
     '教科調査官と実践者のネットワーク。小学校特別活動の映像資料と大会の案内。',
     ('映像資料', '大会案内')),
    ('zen', '全国', '小学校',
     '全国小学校学校行事研究会',
     'https://zensyo-gyou.com/',
     '学校行事のガイドラインと研究報告。行事を「思い出づくり」から動かしたいときに。',
     ('行事のガイドライン', '研究報告')),
    ('zen', '全国', '小・中',
     '全国道徳特別活動研究会',
     'https://doutokutokkatukatarukai.jimdofree.com/',
     '昭和33年から続く会。全国大会と、月例会「大いに語る会」の案内。道徳といっしょに考えます。',
     ('全国大会', '月例会')),
    ('ken', '都', '小学校',
     '東京都小学校特別活動研究会',
     'http://tosho-tokkatsu.tokyo/',
     '検証授業の予定一覧と研究紀要、会報「都小特活」。ホームの研究日程は、ここから拾っています。',
     ('研究会の日程', '研究紀要')),
    ('ken', '都', '中学校',
     '東京都中学校特別活動研究会',
     'https://www.tochutokkatsu.com/',
     '月例研修会の予定、生徒会長サミット、研究紀要、講師派遣の窓口。',
     ('月例研修会', '生徒会長サミット')),
    ('ken', '都', '高等学校',
     '東京都高等学校特別活動研究会',
     'http://tokkatsu.com/',
     '都高特活。高校の特別活動の研究協議会と、新しく担当になった先生への案内。',
     ('研究協議会',)),
    ('ken', '県', '小・中',
     '埼玉県特別活動研究会',
     'http://saitokkatsu.sub.jp/',
     '研究主題と年間計画、研究集録のバックナンバー、資料のダウンロード。',
     ('資料ダウンロード', '研究集録')),
    ('ken', '県', '小学校',
     '熊本県特別活動研究会',
     'https://estokkatsu.wixsite.com/index',
     '研究資料室に、活動報告書・年間指導計画・実態調査。会報「特活通信」のバックナンバーもあります。',
     ('年間指導計画', '会報')),
    ('ken', '県', '中学校',
     '広島県中学校教育研究会 特別活動部会',
     'https://www.pref.hiroshima.lg.jp/site/kyougikai/tokukatu.html',
     '広島県の研究団体連絡協議会の中のページ。県の研究大会の予定が出ます。',
     ('県の研究大会',)),
    ('shi', '市', '小学校',
     '川崎市立小学校特別活動研究会',
     'https://kawasaki-edu.jp/9/2kenkyukai/index.cfm/12,0,60,html',
     '特活データベース。実践事例集・司会台本・学級会ノート・板書グッズ。刷ってすぐ使えるものが多いです。',
     ('実践事例集', '司会台本・板書グッズ')),
    ('shi', '市', '小学校',
     '横浜市立小学校特別活動研究会',
     'http://yokohamatokkatu.cool.coocan.jp/index.html',
     '研究紀要と現況調査報告書。紀要で使ったワークシートがダウンロードできます。',
     ('ワークシート', '現況調査')),
    ('shi', '市', '小学校',
     '名古屋市特別活動実践研究会',
     'http://www.nagoyatokkatsu.com/',
     'なごやとっかつ。「とっかつ 学びの扉」と「特活だより」。読み物として読めるものが多いです。',
     ('読み物', '特活だより')),
    ('shi', '市', '小学校',
     '札幌市特別活動研究会',
     'http://www.sattokkatu.com/',
     '研究の足跡と実践事例、研究・研修会のお知らせ。北海道（北特活）のコーナーもあります。',
     ('実践事例', '研修会')),
)

KAI_UE_N = 3      # 研究会を、上から何件だけ出しておくか（のこりはページの中のふた）

KAI_T = """      <a class="kai" href="{url}" target="_blank" rel="noopener noreferrer">
        <span class="kai-ue"><span class="kai-han han--{han}">{han_ji}</span><span class="kai-muke">{muke}</span><span class="kai-soto">外部</span></span>
        <b class="kai-na">{na}</b>
        <span class="kai-yo">{yo}</span>
        <span class="kai-shita">{tag}<span class="kai-do">{do}</span></span>
      </a>"""


def build_kai():
    from urllib.parse import urlsplit
    gyo, mita = [], set()
    for han, han_ji, muke, na, url, yo, tags in KAI:
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
        fuda = ''.join('<span class="kai-tag">%s</span>' % esc_html(t) for t in tags)
        gyo.append(KAI_T.format(
            url=esc_html(url), han=han, han_ji=esc_html(han_ji), muke=esc_html(muke),
            na=esc_html(na), yo=esc_html(yo), tag=fuda,
            do=esc_html(urlsplit(url).netloc.replace('www.', ''))))
    # 2026-09-21：15会ぜんぶ並べると、ここだけでスマホ5画面ありました。
    #   上から KAI_UE_N 件だけ出して、のこりはこのページの中のふたへ。
    ue, ato = gyo[:KAI_UE_N], gyo[KAI_UE_N:]
    honbun = '    <div class="kaiban">\n' + '\n'.join(ue) + '\n    </div>'
    if not ato:
        return honbun
    naka = '      <div class="kaiban">\n' + '\n'.join(ato) + '\n      </div>'
    return tsunagu(honbun, naka, len(ato))


# ══════════════════════════════════════════════════════════
# 3-4. 新版（縦スクロール1枚）を組み立てる
# ══════════════════════════════════════════════════════════

# 4つの内容。絵のどこを切り出すか（x y 幅 高さ。どれも 5:2）
#
# このサイトの背骨です。広場で出た悩みも、届いた実践も、ぜんぶこの4つに集めます。
#
# 2026-09-21：ここは本体サイトの #manabu へ飛んでいました。
# 飛び先は別のデザインなので、押した人は「別のサイトへ出された」と感じます。
# だから、いまは **どこへも飛ばしません**。カードの中で、その内容の
# 悩み（src/komari の naiyo）と実践（src/jissen の naiyo）が、その場で開きます。
YOTSU = (
    ('n-gakkyu',  'GAKKYU KATSUDO',  '学級活動',   '30 900 1000 400',
     '学級会・係・当番・給食。子どもが自分たちで決める時間です。'),
    ('n-gyoji',   'GAKKO GYOJI',     '学校行事',   '800 820 1000 400',
     '運動会・卒業式・遠足。思い出をつくる時間ではなく、子どもが育つ時間です。'),
    ('n-jidokai', 'JIDOKAI KATSUDO', '児童会活動', '1740 860 1000 400',
     '代表委員会・集会・あいさつ運動。学年をこえて学校をつくります。'),
    ('n-club',    'CLUB KATSUDO',    'クラブ活動', '2420 860 780 312',
     '音楽・図工・科学・運動。好きなことを、学年をこえて。'),
)


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
      <summary><span class="a">のこり{n}件を、このページで開く</span><span class="b">とじる</span></summary>
{naka}
    </details>"""


def tsunagu(ue, nokori_html, n):
    """上に出すぶん ＋（のこりがあれば）ふたの中"""
    if not n:
        return ue
    return ue + '\n' + MOTTO.format(n=n, naka=nokori_html)


# ══ すぐ使える実践（中身まで、この1枚の中で開く） ══════════
#   前は一覧の行で、押すと本体サイトの「まなぶ」タブへ飛んでいました。
#   いまは 準備・流れ・板書・つまずき まで、ここで開きます。
#   JSは1行も使いません（<details> だけ）。だから何も送信しません。
JFUDA = """      <article class="fuda{kcls}" id="j-{slug}">
        <p class="fuda-me"><a class="fuda-tag t--{nid}" href="#naiyo-{nid}">{naiyo}</a>{kindtag}{meta}</p>
        <h3 class="fuda-h">{title}</h3>
        <p class="fuda-lead">{lead}</p>
{more}{setb}{weekly}        <p class="fuda-by">提供：{by}</p>
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
            more=more, setb=setb + shb + ban, weekly=shu, by=esc_html(a['by'])))
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
BFUDA = """      <article class="bfuda" id="b-{slug}">
        <p class="bfuda-me"><span class="bfuda-tag t--{nid}">{naiyo}</span>{kindtag}{meta}</p>
        <h3 class="bfuda-h">{title}</h3>
        <p class="bfuda-lead">{lead}</p>
{mado}{shiryo}{more}        <p class="bfuda-ashi"><span class="bfuda-by">提供：{by}</span><a class="bansho-b bansho-b--line" href="{line}" target="_blank" rel="noopener noreferrer">この実践について、LINEで聞く<i>外部 ↗</i></a></p>
      </article>"""

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

# 写真1枚ぶん。図と、その下の［大きく見る］。
#   ボタンは figure の中に置きます。押されたら、同じ figure の <img> を大きく出します。
GAZOU = """              <figure class="shot"><img src="{uri}" alt="{alt}" width="{w}" height="{h}" loading="lazy" decoding="async">
                <figcaption class="shot-shita"><span class="shot-kazu">{i} / {n}</span><button class="shot-b" type="button" data-zen>大きく見る</button></figcaption>
              </figure>"""


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
                          w=w, h=h, i=i + 1, n=len(mai))
             for i, (uri, w, h) in enumerate(mai)]
        mado = BFUDA_MADO.format(gazou='\n'.join(g)) if g else ''
        # 送ってもらった資料（PDFを画像にしたもの）も、ここで開きます
        sh = ''.join(shiryo_mado(m, v, a['title'], page='bansho.html')
                     for m, kind, v in a.get('shiryo_list', []) if kind == 'naka')
        more = BFUDA_MORE.format(body=md_html(a['rest'])) if a['rest'].strip() else ''
        meta = '・'.join(x for x in (esc_html(a['scene']), esc_html(a['grade']),
                                     ja_md(a['d'])) if x)
        # ── この実践について、LINEで聞く（2026-09-22）─────────────
        #   ★LINEには「決まったオープンチャットを、本文を入れた状態で開く」
        #     入口がありません。できるのは次の2つだけです。
        #       line.me/R/share?text=…  … 本文は入る。送り先は押した人が選ぶ
        #       line.me/ti/g2/…         … あの部屋が直接開く。本文は空
        #   本文が入っているほうが値打ちが大きいので、前者にしました。
        #   押す → LINEが開く → 一覧から「みんなの特活ひろば」を選ぶ → 本文は入っている。
        #   ★ここから何かが出ていくことはありません。送るのは押した人です。
        #   ★話す場はLINE、溜まる場はここ。この1本が、その芯そのものです。
        ima = SITE_URL + 'bansho.html#b-' + a['slug']
        fuda.append(BFUDA.format(
            slug=a['slug'], nid=a['naiyo'], naiyo=esc_html(naiyo_ja(a['naiyo'])),
            kindtag=('<span class="fuda-kind">議題</span>'
                     if a['kind'] == 'gidai' else ''),
            meta=meta, title=esc_html(a['title']), lead=inline_md(a['lead']),
            mado=mado, shiryo=sh, more=more, by=esc_html(a['by']),
            line=esc_html(line_share(a['title'] + '\n' + ima + '\n\n'))))
    return '    <div class="bantana">\n' + '\n'.join(fuda) + '\n    </div>'


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
    ue = ('    <div class="hyo">\n'
          + '\n'.join(gyo(a) for a in kiji[:NEWS_H_N]) + '\n    </div>')
    nokori = kiji[NEWS_H_N:]
    naka = ('      <div class="hyo">\n'
            + '\n'.join(gyo(a) for a in nokori) + '\n      </div>') if nokori else ''
    return tsunagu(ue, naka, len(nokori))


# ── 節のまわりに立つ飾り（絵を1回だけ入れて、置きたい所で <use> する）──
KAZARI_RE = re.compile(r'<i class="kazari([^"]*)" data-([kb])="([a-z0-9\-]+)"([^>]*)></i>')


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


def kazari_defs(tsukatta, buhin, kyara):
    """使った絵だけを、1回ずつ defs に入れる（同じ絵を何度置いても重さは増えません）。"""
    g = []
    for tane, name in sorted(tsukatta):
        hako, atama = (kyara, 'ill-k-') if tane == 'k' else (buhin, 'ill-b-')
        g.append('<g id="%s%s">%s</g>' % (atama, name, hako[name][2]))
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
          <span class="e"><svg viewBox="0 0 {w} {h}" aria-hidden="true" focusable="false"><use href="#ill-k-{n}"/></svg></span>
          <b>{chotto}</b><span class="t">{dekiru}</span>
          <span class="igi-ya" aria-hidden="true">→</span>
        </a>
      </li>"""

IGI_T_NASHI = """      <li class="igi-h h--{n}">
        <span class="e"><svg viewBox="0 0 {w} {h}" aria-hidden="true" focusable="false"><use href="#ill-k-{n}"/></svg></span>
        <b>{chotto}</b><span class="t">{dekiru}</span>
      </li>"""


def build_igi(kyara):
    """ホームのいちばん上。このサイトが何のためにあるかを、4人で短く渡します。"""
    men = []
    for n, chotto, dekiru, saki in IGI_MEN:
        if n not in kyara:
            raise Tomeru('意義の節が %s.svg を呼んでいますが、その絵がありません' % n)
        men.append((IGI_T if saki else IGI_T_NASHI).format(
            n=n, chotto=esc_html(chotto), dekiru=esc_html(dekiru),
            saki=saki, w=kyara[n][0], h=kyara[n][1]))
    return ('<section class="sec" id="igi">\n'
            '  <div class="uchi">\n'
            '    <h2 class="midashi"><span class="en">WHY</span>'
            '<span class="ja">このサイトは、なに</span></h2>\n'
            # 1文＝1行。<span> を1つずつ立てて、行の折れ目を文の切れ目に
            # そろえます（2026-09-22）。<br> だと、画面が狭いときに文の
            # 途中でも折れて「みんなの特／活ひろば」のように割れます。
            '    <p class="igi-bun">'
            '<span>日本の特別活動の<b>情報交流</b>を高めるためのサイトです。</span>'
            '<span>LINEオープンチャット<b>「みんなの特活ひろば（仮）」</b>と'
            '連携しています。</span>'
            '<span>あちらで話し、ここで<b>確かめて、持ち帰る</b>。</span>'
            '<span>そのためにお使いください。</span>'
            '</p>\n'
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
    # index（このページ自身）。板書を送るところが、いちばん上です
    ('okuru',  'b', 'ko-te',    '写真もPDFも、送るとそのまま出ます。'),
    # 送る の すぐ次が 見る。この2つで1組です（2026-09-22）
    ('bansho', 'b', 'kokuban',  '先生方から届いた実践が、そのまま並びます。'),
    ('ima',    'k', 'gyoji',    'つぎの研究会と、申込の締切。'),
    # komari（困っている → 学ぶ、の順に並べます。2026-09-22）
    ('komari', 'b', 'sensei',   '送られた困りごとが、そのまま並びます。'),
    # manabu（すぐ使える道具は、この「学ぶ」と同じページにあります）
    ('manabu', 'k', 'club',     '①から⑤の学習過程と、一次資料と、道具。'),
    # atsumaru
    ('news',   'b', 'keijiban', '一次情報だけ。要約は、こちらの言葉で。'),
    ('kai',    'b', 'bankokki', '1つずつ開いて、いま見られるものだけ。'),
    # shiru（2026-09-22：特活とは と 4つの内容 は同じページなので、1つにまとめました。
    #        4つの内容は、この札から入った先にそのまま置いてあります）
    ('about',  'k', 'gakkatsu', '教科書がない時間の、見るところ。4つの内容も、ここに。'),
)

HOME_T = """      <a class="hfuda p--{page}" href="{saki}">
        <span class="hfuda-e" aria-hidden="true"><svg viewBox="0 0 {w} {h}" focusable="false"><use href="#ill-{tane}-{na}"/></svg></span>
        <b class="hfuda-h">{midashi}</b>
        <span class="hfuda-yo">{yo}</span>
        <span class="hfuda-kazu">{kazu}</span>
      </a>"""


def home_kazu(sid, sec, kiji, jissen, ken, komari):
    """札に出す数。その場で数えたものだけを出します。"""
    def kazoe(pat):
        return len(re.findall(pat, sec.get(sid, '')))
    if sid == 'ima':
        return '%d件' % len(ken)
    if sid == 'news':
        return '%d件' % len(kiji)
    if sid == 'about':
        return '話が%dつ' % kazoe(r'class="manabu-box"')
    if sid == 'manabu':
        return '%d段階と資料%d件' % (kazoe(r'data-learn-detail='),
                                  kazoe(r'<li><a href="https?://[^"]*"[^>]*><span><b>'))
    # 困りごとの数。2026-09-22 まで「4つの内容」の札に出していましたが、
    # 帯を1つにまとめたので、困りごとの札の数になりました。
    if sid in ('komari', 'yotsu'):
        return '悩み%d件' % len(komari)
    if sid == 'jissen':
        return '%d件' % len(jissen)
    if sid == 'kai':
        return '%d会' % len(KAI)
    if sid == 'okuru':
        # 送るところの札には「いくつ届いたか」を出します。
        # （手順の数を出していましたが、手順の箇条書きをやめたので 0 になりました）
        return '%d件とどいた' % len(bansho_aru(jissen))
    if sid == 'bansho':
        # みんなの実践。届いた件数と、その中の写真の枚数（2026-09-22）
        aru = bansho_aru(jissen)
        return '%d件・%d枚' % (aru and len(aru) or 0,
                              sum(bansho_kazu(a['bansho']) for a in aru))
    raise Tomeru('ホームの札 %s に、数の出し方がありません' % sid)


def build_home(doko, sec, buhin, kyara, kiji, jissen, ken, komari):
    """ホームの8枚。使った絵の名前も返します（defs に入れるため）。"""
    fuda, tsukatta = [], set()
    for sid, tane, na, yo in HOME_FUDA:
        hako = kyara if tane == 'k' else buhin
        if na not in hako:
            raise Tomeru('ホームの札 %s が %s.svg を呼んでいますが、その絵がありません' % (sid, na))
        if sid not in doko:
            raise Tomeru('ホームの札 %s に当たる節が、どのページにもありません' % sid)
        w, h, _ = hako[na]
        tsukatta.add((tane, na))
        fuda.append(HOME_T.format(
            page=doko[sid].replace('.html', ''),
            saki='%s#%s' % (doko[sid], sid), tane=tane, na=na, w=w, h=h,
            midashi=esc_html(SETSU_NA[sid]), yo=esc_html(yo),
            kazu=esc_html(home_kazu(sid, sec, kiji, jissen, ken, komari))))
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

GFUDA = """      <div class="gfuda p--{page}">
        <div class="atama" aria-hidden="true" inert>
{atama}
        </div>
        <a class="gfuda-a" href="{saki}"><b class="gfuda-h">{midashi}</b><span class="gfuda-go">開く</span></a>
      </div>"""

# 概要に出す、節のあたま何個ぶんか。窓の高さでも切るので、多くしても伸びません
ATAMA_N = 3
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
_TOBASU = re.compile(r'^\s*<(?:h2[^>]*class="[^"]*\bmidashi\b'
                     r'|p[^>]*class="[^"]*\byomi\b'
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


def build_gaiyo(sec, doko):
    """ホームの「中身を、ざっと」。
       2026-09-21：箇条書き→本物の縮小→読める箇条書き、と回ったあと、
       「各ページの最初の画面のみ そのまま載せる感じ。短いバージョンで」に落ちつきました。
       だから、節のあたまを**そのままの大きさで**載せ、窓の高さで切ります。
       写した絵でも、縮めた絵でもないので、節を直せばここも変わります。"""
    fuda = []
    for sid, _, _, _ in HOME_FUDA:
        if sid in ('ima', 'okuru'):   # この2つは、この上に本物が出ているので要りません
            continue
        fuda.append(GFUDA.format(
            page=doko[sid].replace('.html', ''),
            saki='%s#%s' % (doko[sid], sid),
            midashi=esc_html(SETSU_NA[sid]),
            atama=build_atama(sec[sid])))
    return ('<section class="sec" id="gaiyo">\n'
            '  <div class="uchi">\n'
            '    <h2 class="midashi"><span class="en">SUMMARY</span>'
            '<span class="ja">中身を、ざっと</span></h2>\n'
            '    <p class="yomi">それぞれのページの、中身のはじまりです。'
            '写した絵ではなく本物なので、中身が変わればここも変わります。</p>\n'
            '    <div class="gban">\n' + '\n'.join(fuda) + '\n    </div>\n'
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


KO_T = """<header class="ko{uchi}" id="ue">
  <div class="uchi">
    <p class="ko-modoru"><a href="{home}">TOKKATSU広場</a>{oya}</p>
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


def head_de(f, na):
    """頭は1つの型を使い回し、題と自分のURLだけをページごとに差しかえます。"""
    head = rd('src/head-hiroba.html')
    dai = 'TOKKATSU広場' if f == HOME else '%s｜TOKKATSU広場' % page_na(f)
    head = head.replace('<title>TOKKATSU広場</title>', '<title>%s</title>' % esc_html(dai))
    if f != HOME:
        head = head.replace('content="%s"' % SITE_URL, 'content="%s%s"' % (SITE_URL, f))
        head = head.replace('content="TOKKATSU広場｜特別活動の情報が、溜まる場。"',
                            'content="%s｜TOKKATSU広場"' % esc_html(page_na(f)), 1)
    return head


def tsukau_e(html):
    """そのページが実際に呼んでいる絵の名前だけを拾う。"""
    return set(m.groups() for m in re.finditer(r'href="#ill-([kb])-([a-z0-9-]+)"', html))


def build_tane(html, e_naka, buhin, kyara, atama_naka=None):
    """ページが呼んでいる絵だけを、そのページの defs に入れる。
       呼んでいない絵は入りません（ページごとに軽くなります）。"""
    g = []
    if 'href="#ill-hiroba"' in html:
        g.append('<g id="ill-hiroba">%s</g>' % e_naka)
    if 'href="#ill-atama"' in html and atama_naka:
        g.append('<g id="ill-atama">%s</g>' % atama_naka)
    # 絵の中にも地紋の <defs> があるので、いちばん外がわ（末尾）にだけ足します
    g.append(kazari_defs(tsukau_e(html), buhin, kyara))
    tane = ('<svg class="tane" aria-hidden="true" focusable="false" width="0" height="0" '
            'style="position:absolute"><defs>%s</defs></svg>' % ''.join(g))
    # 呼んでいるのに入っていない絵が1つでもあれば、止める
    aru = set(re.findall(r'<g id="(ill-[^"]+)">', tane))
    yobu = set(re.findall(r'href="#(ill-[^"]+)"', html))
    nai = yobu - aru
    if nai:
        raise Tomeru('ページが #%s を呼んでいますが、そのページの絵の入れ物に入っていません'
                     % '、#'.join(sorted(nai)))
    return tane


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
    # 絵は1ページに1回だけ埋めこみ、4つの内容は <use> で別の場所を切り出す
    e_naka = hiroba_naka(buhin)

    # ── 空を流れる雲（2026-09-22）──────────────────────────
    #   絵そのものは <defs> ＋ <use> なので、中に動きを付けても出ません
    #   （実測ずみ）。そこで「絵の上に重ねた入れ物」を動かします。
    #   1つずつ 高さ・大きさ・速さ・出る間 を変えます。そろうと列車に見えます。
    #   （上からの位置, はば, 1周の秒数, 出るまでの秒数, うすさ）
    kw, kh, _ = buhin['kumo']
    hero_kumo = ''.join(
        '<i class="hkumo" aria-hidden="true" '
        'style="--y:%s;--w:%dpx;--t:%ds;--d:-%ds;--o:%s">'
        '<svg viewBox="0 0 %g %g" focusable="false"><use href="#ill-b-kumo"/></svg></i>'
        % (y, w, t, d, o, kw, kh)
        for y, w, t, d, o in (('16%', 108, 74, 0,  '.62'),
                              ('34%', 150, 96, 34, '.5'),
                              ('7%',   80, 62, 58, '.42')))

    # ── 校庭を走る子（2026-09-22）──────────────────────────
    #   これも雲と同じで「絵の上に重ねた入れ物」。絵の中の子は動かせません。
    #   ★絵の中の子と同じ大きさに見えるよう、はばを px で決め打ちにします。
    #     広い窓（3200）でもスマホの窓（1450）でも、画面上の子は同じくらいの
    #     大きさになるので（実測、どちらも約0.25倍）、1つの値で足ります。
    #   （下からの位置, はば, 横切る秒数, 出るまでの秒数）
    hw, hh, _ = buhin['ko-hashiru']
    hero_ko = ''.join(
        '<i class="hko" aria-hidden="true" style="--b:%s;--w:%dpx;--t:%ds;--d:-%ds;--h:%ss">'
        '<svg viewBox="0 0 %g %g" focusable="false"><use href="#ill-b-ko-hashiru"/></svg></i>'
        % (b, w, t, d, h, hw, hh)
        for b, w, t, d, h in (('6%',  17, 21, 0,  '.30'),
                              ('2%',  21, 17, 9,  '.26')))

    hero = (hero_kumo + hero_ko
            + '<svg viewBox="0 0 %d %d" role="img" aria-label="校庭で学級活動・学校行事・'
            '児童会活動・クラブ活動をしている学校の広場のイラスト">'
            '<use href="#ill-hiroba"/></svg>' % (HIROBA_W, HIROBA_H))

    # スマホ用の切り出し（2026-09-21 直し）。
    #   前は 620 500 1400 700。空を1ドットも入れず、校舎の屋根と
    #   右の時計台を切っていました（「空と学校が切れている」）。
    #   いまは 空と雲・校舎まるごと・右の時計台まるごと・下の子どもたち、
    #   が1枚に入る窓です（1450:1060 ＝ たて長め）。
    hero_s = (hero_kumo + hero_ko
              + '<svg viewBox="760 140 1450 1060" role="img" aria-label="校庭で学校行事を'
              'している学校のイラスト"><use href="#ill-hiroba"/></svg>')

    for mark, html in (('<!--BUILD:HIROBA-->', hero),
                       ('<!--BUILD:HIROBA_S-->', hero_s),
                       ('<!--BUILD:COPY-->',   build_copy(TOBIRA_COPY)),
                       ('    <!--BUILD:YOTSU-->',  build_yotsu(kyara, jissen, komari)),
                       ('      <!--BUILD:NAYAMI-->', build_nayami(komari)),
                       ('    <!--BUILD:KYARA-->',  build_kyara_narabi(kyara)),
                       ('    <!--BUILD:JISSEN_H-->', build_jissen_hiroba(jissen, goods)),
                       ('    <!--BUILD:BANSHO_IRI-->', build_bansho_iriguchi(jissen)),
                       ('    <!--BUILD:OKURU_MIRU-->', build_okuru_miru(jissen)),
                       ('    <!--BUILD:KOMARI_MIRU-->', build_komari_miru(komari)),
                       ('    <!--BUILD:BANSHO-->',     build_bansho(jissen)),
                       ('    <!--BUILD:KOMARI-->',     build_komari(komari)),
                       ('    <!--BUILD:KAI-->',      build_kai()),
                       ('    <!--BUILD:NEWS_H-->',   build_hyo_news(kiji)),
                       ('    <!--BUILD:KENKYUKAI-->',
                        build_kenkyukai(ken, kyara, buhin))):
        if mark not in body:
            raise Tomeru('src/hiroba.html に目じるし %s がありません' % mark.strip())
        body = body.replace(mark, html)

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

    # どの id が、どのページに載るか。これで <a href="#◯◯"> を張りなおします
    doko = {}
    for f, _, _, setsu in PAGES:
        for s in setsu:
            for i in re.findall(r'\sid="([^"]+)"', sec[s]):
                doko[i] = f
    # 頭と足もとは、どのページにも同じものが載ります（張りかえません）
    tsune = set(re.findall(r'\sid="([^"]+)"', hero + foot)) | {'ue'}

    home_html, home_e = build_home(doko, sec, buhin, kyara, kiji, jissen, ken, komari)
    for i in re.findall(r'\sid="([^"]+)"', home_html):
        doko[i] = HOME

    gaiyo_html = build_gaiyo(sec, doko)
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
        html = '\n'.join([
            '<!DOCTYPE html>', '<html lang="ja" dir="ltr">', '<head>',
            head_de(f, na), '<style>', rd(CSS_H), '</style>', '</head>',
            '<body>',
            build_tane(p, e_naka, buhin, kyara,
                       None if f == HOME else ko_e_naka(f, buhin, kyara)),
            p, '</body>', '</html>',
        ]) + '\n'
        ngword_check(html, '公開用/' + f)
        pages[f] = html
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
    print('  新版（ホーム＋%dページ）' % (len(PAGES) - 1))
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
    pdfjs_utsusu()
    print('')
    print('  書きました。入口は 公開用/index.html（ホーム）です。')
    print('  公開用/ は GitHubに上げません（.gitignore）。上げるのは src/ と build.py。')
    print('  push すると Actions が同じように組み立てて、%d枚とも Pages へ出します。'
          % len(PAGES))
    print('')
    return 0


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
