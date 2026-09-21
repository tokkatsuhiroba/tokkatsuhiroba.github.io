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
JISSEN_HOME_N = 2                      # ホームに出す実践の数

# 資料をページの中に入れるときの上限。ここを外すと配れない重さになります。
SHIRYO_KB_MAX  = 500.0   # 画像1枚
SHIRYO_MB_MAX  = 8.0     # 資料1件（1フォルダ）
SHIRYO_ZEN_MAX = 16.0    # 1ページに入る資料の合計
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
    ('index.html',    'TOKKATSU広場', '', ('ima',)),
    ('shiru.html',    '知る',   '特別活動って、なに。4つの内容は、どれ。',
     ('about', 'yotsu')),
    ('manabu.html',   '学ぶ',   '学級会の学習過程と、明日そのまま使える実践。',
     ('manabu', 'jissen')),
    ('atsumaru.html', '集まる', 'ニュース、各地の研究会、実践を送る。',
     ('news', 'kai', 'okuru')),
)
HOME = PAGES[0][0]
# 節の名前。ホームの札と、ページの中の見出しで使い回します
SETSU_NA = {
    'ima':    'カレンダー', 'news':   'ニュース',
    'about':  '特活とは',   'manabu': '学ぶ',
    'yotsu':  '4つの内容',  'jissen': '実践',
    'kai':    '日本の研究会', 'okuru': '送る',
}

# 外のフォームなどのURL。差しかえる場所はここ1つだけ。
# src/body.html の {{FORM_IKEN}} のような目じるしが、ビルド時にこれに置きかわる。
LINKS = {
    'FORM_IKEN'  : 'https://forms.gle/Qkmej386gxQavi8z6',   # 困りごと・意見（2026-09-21 専用フォームに差しかえ）
    'FORM_JISSEN': 'https://forms.gle/fnWnivr61t2BA6tR7',   # 実践・板書の提供（同上）
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


def ngword_check(text, where):
    """出してはいけない語が1つでも混ざっていたら止める（src/_ngword.txt）。"""
    if not os.path.exists(NG):
        return
    for line in io.open(NG, encoding='utf-8'):
        w = line.strip()
        if not w or w.startswith('#'):
            continue
        if w in text:
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
    for k in ('date', 'title', 'grade', 'scene', 'time'):
        if not fm.get(k):
            raise Tomeru('%s：%s が空です' % (f, k))
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
        if not re.match(r'^[a-z0-9-]+$', oki):
            raise Tomeru('%s：shiryo の置き場「%s」は、src/shiryo/ のフォルダ名'
                         '（英小文字・数字・-）か、https:// のURLにしてください' % (f, oki))
        if not os.path.isdir(os.path.join(SHIRYO, oki)):
            aru = sorted(os.path.basename(x) for x in glob.glob(os.path.join(SHIRYO, '*'))
                         if os.path.isdir(x))
            raise Tomeru('%s：shiryo の「%s」が src/shiryo/ にありません（あるのは %s）'
                         % (f, oki, '、'.join(aru) or '無し'))
        fm['shiryo_list'].append((midashi, 'naka', oki))

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
    kiji.sort(key=lambda a: (a['d'], a['_file']), reverse=True)
    seen = set()
    for a in kiji:
        if a['slug'] in seen:
            raise Tomeru('実践の id「%s」が2つあります（ファイル名の _ から後ろが同じ）' % a['slug'])
        seen.add(a['slug'])
        for g in a['goods_ids']:
            goods[g]['used'].append(a)
    return kiji, tobashita


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
    raise Tomeru('%s：大きさが読めませんでした（WebP か PNG にしてください）' % f)


# 1ページに入れた資料の合計（ビルドのはじめに0に戻す）
_SHIRYO_GOUKEI = {'b': 0}


def shiryo_yomu(oki):
    """src/shiryo/◯◯/ の画像を、名前の順に読む。戻りは [(data URI, 横, 縦)]。"""
    tokoro = os.path.join(SHIRYO, oki)
    import base64
    mai, goukei = [], 0
    for p in sorted(glob.glob(os.path.join(tokoro, '*'))):
        e = os.path.splitext(p)[1].lower()
        if e not in SHIRYO_MIME:
            continue
        b = io.open(p, 'rb').read()
        kb = len(b) / 1024.0
        if kb > SHIRYO_KB_MAX:
            raise Tomeru('src/shiryo/%s/%s が %.0fKB あります（上限 %.0fKB）。'
                         '横1000pxくらいのWebPにしてください'
                         % (oki, os.path.basename(p), kb, SHIRYO_KB_MAX))
        goukei += len(b)
        w, h = gazou_size(b, 'src/shiryo/%s/%s' % (oki, os.path.basename(p)))
        mai.append(('data:%s;base64,%s' % (SHIRYO_MIME[e], base64.b64encode(b).decode()), w, h))
    if not mai:
        raise Tomeru('src/shiryo/%s/ に画像がありません（.webp か .png）' % oki)
    mb = goukei / 1024.0 / 1024.0
    if mb > SHIRYO_MB_MAX:
        raise Tomeru('src/shiryo/%s/ が合わせて %.1fMB あります（上限 %.0fMB）。'
                     'ページが重くなるので、要るページだけにしてください' % (oki, mb, SHIRYO_MB_MAX))
    _SHIRYO_GOUKEI['b'] += goukei
    zen = _SHIRYO_GOUKEI['b'] / 1024.0 / 1024.0
    if zen > SHIRYO_ZEN_MAX:
        raise Tomeru('1ページに入れた資料が合わせて %.1fMB になりました（上限 %.0fMB）。'
                     '配るには重すぎます' % (zen, SHIRYO_ZEN_MAX))
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


def shiryo_mado(midashi, oki, alt):
    """資料1件ぶんの「ページの中で開く窓」。"""
    mai = shiryo_yomu(oki)
    g = []
    for i, (uri, w, h) in enumerate(mai):
        g.append('              <figure><img src="%s" alt="%s %dページめ" '
                 'width="%d" height="%d" loading="lazy" decoding="async">'
                 '<figcaption>%d / %d</figcaption></figure>'
                 % (uri, esc_html(alt), i + 1, w, h, i + 1, len(mai)))
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
                mado.append(shiryo_mado(m, v, a['title']))
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
    _SHIRYO_GOUKEI['b'] = 0
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
                        'basho': hiku('place_ja'), 'url': hiku('url')})
    out.sort(key=lambda a: a['d'])
    return out


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


KEN_T = """      <{tag} class="gyo{tsugi}" id="ken-{ban}"{href}>
        <span class="hizuke"><b aria-hidden="true">{md}</b><i aria-hidden="true">{youbi}</i>\
<span class="kakure">{ja_date}（{youbi}）</span></span>
        <span class="kao kao--{kao}"><svg viewBox="{win}" aria-hidden="true" focusable="false"><use href="#{ref}"/></svg></span>
        <span class="t">{ja}<span class="sub">{shurui}{basho}{soto}</span></span>
        <span class="nokori"><b>{nokori}</b>日後</span></{tag}>"""


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
    ue = ('      <div class="koyomi-ue">\n'
          '        <p class="koyomi-hint">よこにスライド</p>\n'
          '        <p class="koyomi-okuri">\n'
          '          <button type="button" class="tsuki-b" data-tsuki="-1"'
          ' aria-label="前の月を見る">‹</button>\n'
          '          <button type="button" class="tsuki-b" data-tsuki="1"'
          ' aria-label="次の月を見る">›</button>\n'
          '        </p>\n'
          '      </div>')
    ban = ('      <div class="tsuki-ban" tabindex="0" role="group"'
           ' aria-label="研究会のこよみ。%dか月ぶんを、よこにスライドして見ます">\n'
           % len(out)
           + '\n'.join(out) + '\n      </div>')
    return ('    <div class="koyomi">\n' + ue + '\n' + ban + '\n'
            + hanrei + '\n    </div>')


def build_kenkyukai(ken, kyara, buhin, kyou=None):
    kyou = kyou or datetime.date.today()

    def gyo(a, i):
        tag = 'a' if a['url'] else 'div'
        ref, kao, win = ken_kao(a, kyara, buhin)
        d = a['d']
        return KEN_T.format(
            tag=tag, tsugi=(' gyo--tsugi' if i == 0 else ''), ban=i,
            href=(' href="%s" target="_blank" rel="noopener noreferrer"' % a['url']) if a['url'] else '',
            ref=ref, kao=kao, win=win,
            md='%d/%d' % (d.month, d.day),
            youbi=YOUBI[(calendar.weekday(d.year, d.month, d.day) + 1) % 7],
            soto=('・外部（申込のページ）' if a['url'] else ''),
            ja=esc_html(a['ja']), shurui=a['shurui'], ja_date=ja_md(d),
            basho=('・' + esc_html(a['basho'])) if a['basho'] else '',
            nokori=a['nokori'])
    # 2026-09-21：一覧は、近い KEN_UE_N 件だけ出して、のこりはふたの中へ。
    #   （前は「こよみから飛べるように」ぜんぶ出していました。いまは
    #     hiroba.html の akeru() が、飛び先のふたを先に開くので、
    #     ふたの中にあってもこよみから飛べます。）
    ue, ato = ken[:KEN_UE_N], ken[KEN_UE_N:]
    hyo = ('      <div class="hyo hyo--ken">\n'
           + '\n'.join(gyo(a, i) for i, a in enumerate(ue)) + '\n      </div>')
    if ato:
        naka = ('        <div class="hyo hyo--ken">\n'
                + '\n'.join(gyo(a, i + len(ue)) for i, a in enumerate(ato))
                + '\n        </div>')
        hyo = tsunagu(hyo, naka, len(ato))
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
     '検証授業の予定一覧と研究紀要、会報「都小特活」。このページのカレンダーはここから拾っています。',
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
# 悩み（NAYAMI）と実践（src/jissen の naiyo）が、その場で開きます。
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


# ── 広場で出た悩み（4つの内容ごとに集める）──────────────
# 1行＝(4つの内容のどれか, 悩みの言葉, 行き先)
#   行き先 '1'〜'5' … 学級活動(1)の学習過程の段階。押すと「学ぶ」のそこが開きます
#   行き先 ''      … まだ答えを置けていない悩み。隠さずに、そのまま出します
#
# ★ここ1か所に書くと、2か所に出ます。
#   ・「学ぶ」の お悩み別の入口 … 上から NAYAMI_IRIGUCHI 件（段階につながるものだけ）
#   ・「4つの内容」のカードの中 … その内容の悩み、ぜんぶ
#
# ── 出どころ（2026-09-21）──────────────────────────
# LINEオープンチャット「みんなの特活ひろば（仮）」の 8/9〜9/21 のやりとり
# （1750件）を読んで、**実際に出ていた困りごとだけ**を書き出したものです。
#
# 載せるときの約束。ここを外すと、書いた人が特定されます。
#   1. 発言をそのまま引用しない。**悩みの言葉に言いかえる**
#   2. 発言者・学校・地域・日付は**一切載せない**（この表にも持たせない）
#   3. 1人の個別事情が分かる書き方にしない。**同じ困りごとの一般形**にする
#   4. 答えを置けていないものも消さない。**「まだ答えが無い」ことが情報**です
NAYAMI = (
    # ── 学級活動 ───────────────────────────────
    ('gakkyu',  '学級会が話し合いにならない',                   '2'),
    ('gakkyu',  '議題が出てこない',                             '1'),
    ('gakkyu',  '学級会の進め方が分からない',                   '1'),
    ('gakkyu',  '話合いが決まらない・多数決になる',             '3'),
    ('gakkyu',  '係活動が形だけになっている',                   '4'),
    ('gakkyu',  'やりっぱなしで次につながらない',               '5'),
    ('gakkyu',  '学級会をやったことのないクラスで、どう始めるか', '1'),
    ('gakkyu',  '議題が楽しいことばかりで、生活の問題に向かわない', '1'),
    ('gakkyu',  '意見が広がるだけで、深まらない',               '2'),
    ('gakkyu',  '決まらないとき「とりあえずやってみる」でいいのか', '3'),
    ('gakkyu',  '「私」から「私たち」に変わるとは、どういうことか', '3'),
    ('gakkyu',  '係と当番のちがいが分からない',                 '4'),
    ('gakkyu',  '振り返りの視点が、毎回こんがらがる',           '5'),
    ('gakkyu',  '「振り返らせる」になっていないか',             '5'),
    ('gakkyu',  '特別支援学級の子と、どう一緒に学級会をつくるか', ''),
    ('gakkyu',  '学級活動(1)(2)(3)の区別が、あいまいなまま',    ''),
    # ── 学校行事 ───────────────────────────────
    ('gyoji',   '行事が本番だけで終わり、積み上がらない',       ''),
    ('gyoji',   '行事のとき、子どもに何を渡せばいいか',         ''),
    ('gyoji',   '移動教室のバスレクや夜の集いの中身が思いつかない', ''),
    # ── 児童会活動 ─────────────────────────────
    ('jidokai', '児童会を任された',                             ''),
    ('jidokai', '委員会で、めあては決まるのに活動が思いつかない', ''),
    ('jidokai', '代表委員会が、決まった話し合いだけで終わる',   ''),
    # ── クラブ活動 ─────────────────────────────
    ('club',    'クラブが何をする時間か分からない',             ''),
    ('club',    'ほかの学校が、どんなクラブをやっているか知りたい', ''),
)

# 「学ぶ」のお悩み別の入口に出す数（上から数えて、段階につながるものだけ）。
# ぜんぶ出すと入口が長くなって、入口の役をしなくなります。
NAYAMI_IRIGUCHI = 6

MARU = '①②③④⑤'


def kenmon_nayami():
    aru = [n for n, _ in naiyo_ichiran()]
    mita = set()
    for naiyo, kotoba, saki in NAYAMI:
        if naiyo not in aru:
            raise Tomeru('悩み「%s」の内容が %s です（%s のどれか）'
                         % (kotoba, naiyo or '空', '／'.join(aru)))
        if saki and saki not in '12345':
            raise Tomeru('悩み「%s」の行き先が %s です（1〜5 の段階か、空）' % (kotoba, saki))
        if kotoba in mita:
            raise Tomeru('悩み「%s」が2回出ています' % kotoba)
        mita.add(kotoba)


def nayami_gyo(kotoba, saki, ji=' ' * 8):
    """悩み1つぶんの行。行き先があれば押せる札、無ければ破線の札。"""
    if saki:
        return ('%s<li><button type="button" data-learn-step="%s">'
                '<span>%s</span><span class="to">%sへ</span></button></li>'
                % (ji, saki, esc_html(kotoba), MARU[int(saki) - 1]))
    return ('%s<li class="mada"><span>%s</span>'
            '<span class="to to--mada">LINEで聞く</span></li>' % (ji, esc_html(kotoba)))


def build_nayami():
    """「学ぶ」のお悩み別の入口。段階につながる悩みを、表の順に上から数件。"""
    gyo = [nayami_gyo(k, s) for _, k, s in NAYAMI if s][:NAYAMI_IRIGUCHI]
    return '      <ul class="nayami">\n' + '\n'.join(gyo) + '\n      </ul>'


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

YOTSU_AKE = """          <details class="hiraku naiyo-ake">
            <summary><span class="a">{aji}</span><span class="b">とじる</span></summary>
            <div class="naiyo-naka">
{naka}
            </div>
          </details>
"""

YOTSU_KARA = """          <p class="naiyo-saki naiyo-mada">悩みも実践も、まだ集まっていません</p>
          <p class="naiyo-okuru"><a href="#okuru">{ja}の実践を送る</a></p>
"""


def yotsu_atsume(nid, ja, nayami, jissen):
    """カードの中に、その内容の悩みと実践を集める。開くのは、このページの中。"""
    if not nayami and not jissen:
        return YOTSU_KARA.format(ja=esc_html(ja))
    naka, aji = [], []
    if nayami:
        aji.append('悩み%d件' % len(nayami))
        naka.append('              <p class="naiyo-h">広場で出た悩み<i>%d</i></p>' % len(nayami))
        naka.append('              <ul class="nayami nayami--naka">\n'
                    + '\n'.join(nayami_gyo(k, s, ' ' * 16) for _, k, s in nayami)
                    + '\n              </ul>')
    if jissen:
        aji.append('実践%d件' % len(jissen))
        naka.append('              <p class="naiyo-h">この内容の実践<i>%d</i></p>' % len(jissen))
        naka.append('              <ul class="naiyo-jissen">\n'
                    + '\n'.join('                <li><a href="#j-%s"><span>%s</span>'
                                '<span class="d">↓</span></a></li>'
                                % (a['slug'], esc_html(a['title'])) for a in jissen)
                    + '\n              </ul>')
    else:
        naka.append('              <p class="naiyo-nai">この内容の実践は、まだ1件もありません。'
                    'あなたの1件めが、ここに載ります。</p>')
    naka.append('              <p class="naiyo-okuru"><a href="#okuru">%sの実践を送る</a></p>'
                % esc_html(ja))
    return YOTSU_AKE.format(aji='・'.join(aji) + 'をひらく', naka='\n'.join(naka))


def build_yotsu(kyara, jissen):
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
                                [x for x in NAYAMI if x[0] == nid],
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
JFUDA = """      <article class="fuda" id="j-{slug}">
        <p class="fuda-me"><a class="fuda-tag t--{nid}" href="#naiyo-{nid}">{naiyo}</a>{scene}・{grade}・{time}</p>
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


JISSEN_UE_N = 2   # 実践を、上から何枚だけ出しておくか（のこりはページの中のふた）


def build_jissen_hiroba(jissen, goods):
    fuda = []
    for a in jissen:
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
            else:
                sh.append('<a class="shiryo-b" href="%s" target="_blank" '
                          'rel="noopener noreferrer">%s<i>外部</i></a>'
                          % (esc_html(v), esc_html(m)))
        shb = ''.join(mado) + (JFUDA_SHIRYO.format(items=''.join(sh)) if sh else '')
        fuda.append(JFUDA.format(
            slug=a['slug'], nid=a['naiyo'], naiyo=esc_html(naiyo_ja(a['naiyo'])),
            scene=esc_html(a['scene']), grade=esc_html(a['grade']),
            time=esc_html(a['time']), title=esc_html(a['title']), lead=inline_md(a['lead']),
            more=more, setb=setb + shb, weekly=shu, by=esc_html(a['by'])))
    # 2026-09-21：札をぜんぶ縦に並べると、ここだけでスマホ5画面ありました。
    #   上から JISSEN_UE_N 枚だけ出して、のこりはこのページの中のふたへ。
    #   4つの内容から #j-◯◯ で飛んできたときは、akeru() がふたを先に開きます。
    ue, ato = fuda[:JISSEN_UE_N], fuda[JISSEN_UE_N:]
    honbun = '    <div class="tefuda">\n' + '\n'.join(ue) + '\n    </div>'
    if not ato:
        return honbun
    naka = '      <div class="tefuda">\n' + '\n'.join(ato) + '\n      </div>'
    return tsunagu(honbun, naka, len(ato))


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


# ══ ホーム（2026-09-21に新設）════════════════════════════
#   全部の項目を、短く・面白そうに1枚にまとめる入口。
#   数は、その場で数えたものだけを出します（手で書いた数は置きません。
#   足したのに数が古い、が起きないため）。
#   （節のid, 絵のたね, 絵の名前, 短い1行）
HOME_FUDA = (
    ('ima',    'k', 'gyoji',    'つぎの研究会と、申込の締切。'),
    ('news',   'b', 'keijiban', '一次情報だけ。要約は、こちらの言葉で。'),
    ('about',  'k', 'gakkatsu', '教科書がない時間の、見るところ。'),
    ('manabu', 'b', 'kokuban',  '①から⑤が、ひと回りして①に戻る。'),
    ('yotsu',  'k', 'jidokai',  '学活くん・行人・児童会ちゃん・クラブマン。'),
    ('jissen', 'k', 'club',     '週案にそのまま書ける1行が付いています。'),
    ('kai',    'b', 'bankokki', '1つずつ開いて、いま見られるものだけ。'),
    ('okuru',  'b', 'ko-te',    '送ると、ふつうはその日のうちに載ります。'),
)

HOME_T = """      <a class="hfuda hf--{sid}" href="{saki}">
        <span class="hfuda-e" aria-hidden="true"><svg viewBox="0 0 {w} {h}" focusable="false"><use href="#ill-{tane}-{na}"/></svg></span>
        <b class="hfuda-h">{midashi}</b>
        <span class="hfuda-yo">{yo}</span>
        <span class="hfuda-kazu">{kazu}</span>
      </a>"""


def home_kazu(sid, sec, kiji, jissen, ken):
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
    if sid == 'yotsu':
        return '悩み%d件' % len(NAYAMI)
    if sid == 'jissen':
        return '%d件' % len(jissen)
    if sid == 'kai':
        return '%d会' % len(KAI)
    if sid == 'okuru':
        return '%dつの手順' % kazoe(r'<li><span class="n">')
    raise Tomeru('ホームの札 %s に、数の出し方がありません' % sid)


def build_home(doko, sec, buhin, kyara, kiji, jissen, ken):
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
            sid=sid, saki='%s#%s' % (doko[sid], sid), tane=tane, na=na, w=w, h=h,
            midashi=esc_html(SETSU_NA[sid]), yo=esc_html(yo),
            kazu=esc_html(home_kazu(sid, sec, kiji, jissen, ken))))
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

GFUDA = """      <a class="gfuda gf--{sid}" href="{saki}">
        <b class="gfuda-h">{midashi}</b>
        <ul class="gfuda-l">
{gyo}
        </ul>
        <span class="gfuda-go">{iku}</span>
      </a>"""


def _nuku(html, pat, n=4):
    """節の中から、見出しになっている字だけを抜く。"""
    out = []
    for m in re.finditer(pat, html, re.S):
        t = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        t = re.sub(r'\s+', ' ', t)
        if t and t not in out:
            out.append(t)
    if not out:
        raise Tomeru('ホームの概要が、節から中身を1つも抜けませんでした（%s）' % pat)
    return out[:n]


def build_gaiyo(sec, doko, kiji, jissen):
    naka = {
        # 「特活とは」… 4つの箱の見出し
        'about':  _nuku(sec['about'], r'<h3 class="manabu-h">(.*?)</h3>'),
        # 「学ぶ」… 5段階の名前
        'manabu': _nuku(sec['manabu'], r'<summary><span class="no">\d</span>'
                                       r'<span class="sh"><b>(.*?)</b>', 5),
        # 「4つの内容」… 4人の名前と、受けもつ内容
        'yotsu':  ['%s　%s' % (na, naiyo) for _, na, naiyo, _ in KYARA_MEN],
        # 「送る」… 4つの手順
        'okuru':  _nuku(sec['okuru'], r'<li><span class="n">\d</span><b>(.*?)</b>'),
        # ニュースと実践は、いま載っているものそのもの
        'news':   [a.get('home') or a['title'] for a in kiji[:3]],
        'jissen': [a['title'] for a in jissen[:3]],
        # 研究会は、範囲ごとの数
        'kai':    ['全国の会　%d' % sum(1 for k in KAI if k[0] == 'zen'),
                   '都道府県の会　%d' % sum(1 for k in KAI if k[0] == 'ken'),
                   '市の会　%d' % sum(1 for k in KAI if k[0] == 'shi')],
    }
    fuda = []
    for sid, _, _, _ in HOME_FUDA:
        if sid not in naka:       # こよみは、この下に本物が出ているので要りません
            continue
        saki = '%s#%s' % (doko[sid], sid)
        iku = '%s を開く' % dict((f, na) for f, na, _, _ in PAGES)[doko[sid]]
        fuda.append(GFUDA.format(
            sid=sid, saki=saki, midashi=esc_html(SETSU_NA[sid]),
            iku=esc_html(iku),
            gyo='\n'.join('          <li>%s</li>' % esc_html(t) for t in naka[sid])))
    return ('<section class="sec" id="gaiyo">\n'
            '  <div class="uchi">\n'
            '    <h2 class="midashi"><span class="en">SUMMARY</span>'
            '<span class="ja">中身を、ざっと</span></h2>\n'
            '    <p class="yomi">どのページに何があるか、押すまえに見られます。'
            'ここに出ているのは、そのページの中身そのものです。</p>\n'
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
        gyo.append('      <li><a href="%s"%s>%s</a></li>'
                   % ('#%s' % sid if ima else '%s#%s' % (saki, sid),
                      ' class="obi-ima" aria-current="page"' if ima else '',
                      esc_html(SETSU_NA[sid])))
    return ('<nav class="obi" aria-label="TOKKATSU広場の中の、8つの行き先">\n'
            '  <div class="obi-uchi">\n'
            '    <a class="obi-na" href="%s">TOKKATSU広場</a>\n'
            '    <ul class="obi-l">\n' % HOME
            + '\n'.join(gyo) + '\n'
            '    </ul>\n'
            '  </div>\n'
            '</nav>')


KO_T = """<header class="ko" id="ue">
  <div class="uchi">
    <p class="ko-modoru"><a href="{home}">TOKKATSU広場</a></p>
    <h1 class="ko-h">{na}</h1>
    <p class="ko-yo">{yo}</p>
    <p class="ko-naka">{naka}</p>
  </div>
</header>"""


def head_de(f, na):
    """頭は1つの型を使い回し、題と自分のURLだけをページごとに差しかえます。"""
    head = rd('src/head-hiroba.html')
    dai = 'TOKKATSU広場' if f == HOME else '%s｜TOKKATSU広場' % na
    head = head.replace('<title>TOKKATSU広場</title>', '<title>%s</title>' % esc_html(dai))
    if f != HOME:
        head = head.replace('content="%s"' % SITE_URL, 'content="%s%s"' % (SITE_URL, f))
        head = head.replace('content="TOKKATSU広場｜特別活動の情報が、溜まる場。"',
                            'content="%s｜TOKKATSU広場"' % esc_html(na), 1)
    return head


def tsukau_e(html):
    """そのページが実際に呼んでいる絵の名前だけを拾う。"""
    return set(m.groups() for m in re.finditer(r'href="#ill-([kb])-([a-z0-9-]+)"', html))


def build_tane(html, e_naka, buhin, kyara):
    """ページが呼んでいる絵だけを、そのページの defs に入れる。
       呼んでいない絵は入りません（ページごとに軽くなります）。"""
    g = []
    if 'href="#ill-hiroba"' in html:
        g.append('<g id="ill-hiroba">%s</g>' % e_naka)
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
    _SHIRYO_GOUKEI['b'] = 0
    buhin, hyo = load_buhin()
    kyara = load_kyara()
    kiji, _ = load_news()
    goods = load_goods()
    jissen, _ = load_jissen(goods)
    kenmon_nayami()
    body = rd('src/hiroba.html')

    if not kiji:
        raise Tomeru('出せるニュースが1件もありません')
    if not jissen:
        raise Tomeru('出せる実践が1件もありません')

    ken = load_kenkyukai()
    # 絵は1ページに1回だけ埋めこみ、4つの内容は <use> で別の場所を切り出す
    e_naka = hiroba_naka(buhin)
    hero = ('<svg viewBox="0 0 %d %d" role="img" aria-label="校庭で学級活動・学校行事・'
            '児童会活動・クラブ活動をしている学校の広場のイラスト">'
            '<use href="#ill-hiroba"/></svg>' % (HIROBA_W, HIROBA_H))

    # スマホ用は、校舎と学校行事のあたりを寄って切り出す（2:1）
    hero_s = ('<svg viewBox="620 500 1400 700" role="img" aria-label="校庭で学校行事を'
              'している学校のイラスト"><use href="#ill-hiroba"/></svg>')

    for mark, html in (('<!--BUILD:HIROBA-->', hero),
                       ('<!--BUILD:HIROBA_S-->', hero_s),
                       ('<!--BUILD:COPY-->',   build_copy(TOBIRA_COPY)),
                       ('    <!--BUILD:YOTSU-->',  build_yotsu(kyara, jissen)),
                       ('      <!--BUILD:NAYAMI-->', build_nayami()),
                       ('    <!--BUILD:KYARA-->',  build_kyara_narabi(kyara)),
                       ('    <!--BUILD:JISSEN_H-->', build_jissen_hiroba(jissen, goods)),
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

    home_html, home_e = build_home(doko, sec, buhin, kyara, kiji, jissen, ken)
    for i in re.findall(r'\sid="([^"]+)"', home_html):
        doko[i] = HOME

    gaiyo_html = build_gaiyo(sec, doko, kiji, jissen)
    for i in re.findall(r'\sid="([^"]+)"', gaiyo_html):
        doko[i] = HOME

    pages = {}
    for f, na, yo, setsu in PAGES:
        if f == HOME:
            # ホームの並び … 8つの札 → こよみ → 中身をざっと
            atama, saki = hero, 'ichiran'
            naka_html = '\n\n'.join([home_html]
                                    + [sec[s] for s in setsu] + [gaiyo_html])
        else:
            atama = KO_T.format(home=HOME, na=esc_html(na), yo=esc_html(yo),
                                naka='　'.join(SETSU_NA[s] for s in setsu))
            naka_html, saki = '\n\n'.join(sec[s] for s in setsu), setsu[0]
        p = '\n'.join(['<a class="skip" href="#%s">本文へ進む</a>' % saki,
                       atama, build_obi(f, doko), naka_html, foot, shikake])
        p = tsunagi_naosu(p, f, doko, tsune)
        html = '\n'.join([
            '<!DOCTYPE html>', '<html lang="ja" dir="ltr">', '<head>',
            head_de(f, na), '<style>', rd(CSS_H), '</style>', '</head>',
            '<body>', build_tane(p, e_naka, buhin, kyara), p, '</body>', '</html>',
        ]) + '\n'
        ngword_check(html, '公開用/' + f)
        pages[f] = html
    return pages, hyo, kiji, jissen


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
        pages, hyo, kiji, jissen = build_shin()
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
                     % (ja, sum(1 for x in NAYAMI if x[0] == nid),
                        sum(1 for a in jissen if a['naiyo'] == nid))
                     for nid, ja in naiyo_ichiran()))
    print('  悩み　　　　… %d件（うち %d件が学習過程につながっています）'
          % (len(NAYAMI), sum(1 for x in NAYAMI if x[2])))
    print('  実践　　　　… %d件（ぜんぶ、中身までこのページに）' % len(jissen))
    print('  ニュース　　… %d件（上から%d件。のこりはページの中のふた）'
          % (len(kiji), min(len(kiji), NEWS_H_N)))
    print('  こよみ　　　… %d件を %dか月ぶんのますめに'
          % (len(load_kenkyukai()), KOYOMI_TSUKI_MAX))
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
    for w in warn:
        print('  ⚠ %s' % w)
    if check_only:
        print('\n  --check なので書いていません。\n')
        return 0
    for f in pages:
        io.open(os.path.join(ROOT, '公開用', f), 'w',
                encoding='utf-8', newline='\n').write(pages[f])
    print('')
    print('  書きました。入口は 公開用/index.html（ホーム）です。')
    print('  公開用/ は GitHubに上げません（.gitignore）。上げるのは src/ と build.py。')
    print('  push すると Actions が同じように組み立てて、%d枚とも Pages へ出します。'
          % len(PAGES))
    print('')
    return 0


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
