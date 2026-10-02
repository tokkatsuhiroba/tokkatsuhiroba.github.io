#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
スマホの幅で、ページが画面の外へはみ出していないかを機械で見る（2026-10-02 依頼）

    python3 sumaho_haba.py            … 公開用/*.html をぜんぶ見る
    python3 sumaho_haba.py bansho.html … 1枚だけ見る

はみ出しが1つでもあれば、終わりの番号 1 で止まります。
GitHub Actions では build.py の すぐあとに走り、**止まれば公開されません**
（前の、くずれていないページがそのまま残ります）。

なぜ要るのか
    2026-10-02、本文に長いURL（折れめの無い英数字）を書いた実践が1件 届いただけで、スマホの実践集の
    札が **14件ぜんぶ** 幅678pxに広がり、右半分が切れて読めなくなりました。
    ページは overflow-x:clip なので、横にスクロールも出ません。
    **見た目では気づけず、build.py の検問にもかかりません**（検問が見るのは
    字と項目で、並べたときの幅は見ていないため）。
    だから、本物のブラウザで 375px に並べて、幅を測ります。

どう測るか
    ・Chrome をヘッドレス（画面なし）で開き、幅375pxで並べます。
    ・ページの写しの最後に、測る小さなスクリプトを足します。
      **公開するページには1バイトも足しません**（写しは捨てます）。
    ・「画面の右はしより外に出ている要素」を数えます。ただし、
      よこ送りの窓（overflow が visible でない入れ物）の中身は数えません。
      あれは わざと外へ並べて、指で送るものです。窓そのものは数えます。
    ・字が自分の箱からはみ出していないかも見ます（長いURLが札のふちで
      切れるのは、外側の幅だけ見ていると通ってしまうため）。
      たたんだ本文（［さらに表示］）は、ひらいてから測ります。
    ・遅れて読む写真（loading=lazy）も、写しでは すぐ読ませます。
      届いた写真の形で幅がくずれるので、読まないと測れません。

Chrome が見つからないときは、測らずに知らせて 0 で終わります（手もとの
Mac に Chrome が無くても、build はできるように）。Actions には入っています。
"""

import glob, html, json, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, '公開用')
HABA = 375          # いちばん よく見られる iPhone の幅（SE〜13 mini は 375／320 は今は まれ）
TAKASA = 812
# 測らないページ。とびら版は試作で、公開の帯からは つながっていません。
NOZOKU = {'tobira.html', 'index-kyu.html', 'index-simple.html'}

# ヘッドレスの Chrome は、窓を 500px より細くできません。
# だから 375px の枠（iframe）の中にページを開いて、枠の中で測ります。
# 結果は枠の外へ手紙（postMessage）で渡し、外のページに書き出します。
WAKU = '''<!doctype html><meta charset="utf-8">
<iframe src="%s" style="width:%dpx;height:%dpx;border:0"></iframe>
<script>
addEventListener('message', function(ev){
  var pre = document.createElement('pre');
  pre.id = '__haba__';
  pre.textContent = ev.data;
  document.body.appendChild(pre);
});
</script>
'''

HAKARU = r'''
<script>
addEventListener('load', function(){ setTimeout(function(){
  var W = document.documentElement.clientWidth, deta = [];
  // たたんだ本文（［さらに表示］）は、ひらいてから測ります。
  // たたんだままだと、はみ出した字が切られて隠れ、見のがします。
  document.querySelectorAll('.bfuda-naka--tojita').forEach(function(n){
    n.classList.remove('bfuda-naka--tojita');
  });
  document.body.offsetWidth;
  function mado(e){
    // e より上（body の手前まで）に、中身を切る／送る入れ物があるか
    for (var p = e.parentElement; p && p !== document.body; p = p.parentElement){
      var o = getComputedStyle(p).overflowX;
      if (o !== 'visible') return true;
    }
    return false;
  }
  document.querySelectorAll('body *').forEach(function(e){
    if (e.closest('svg') && e.tagName.toLowerCase() !== 'svg') return;
    var r = e.getBoundingClientRect();
    if (!r.width || !r.height) return;
    var s = getComputedStyle(e);
    if (s.visibility === 'hidden' || s.position === 'fixed') return;
    if (r.right <= W + 1 && r.left >= -1) return;
    if (mado(e)) return;
    var a = e.closest('[id]');
    deta.push({tag: e.tagName.toLowerCase() + (e.classList.length ? '.' + [].join.call(e.classList, '.') : ''),
               w: Math.round(r.width), right: Math.round(r.right),
               id: a ? a.id : ''});
  });
  // もう1つ：字が、自分の箱からはみ出していないか。
  //   札の幅は守れても、中の長いURLが札のふちで切れることがあります
  //   （2026-10-02 の実際）。外側の幅だけ見ていると、これは通ってしまいます。
  document.querySelectorAll('body *').forEach(function(e){
    if (e.closest('svg')) return;
    var ji = [].some.call(e.childNodes, function(n){ return n.nodeType === 3 && n.textContent.trim(); });
    if (!ji || e.clientWidth <= 2) return;           // 字が無い／読み上げ用の1px
    var s = getComputedStyle(e);
    if (s.textOverflow === 'ellipsis' || s.visibility === 'hidden') return;
    if (e.scrollWidth > e.clientWidth + 1) {
      var a = e.closest('[id]');
      deta.push({tag: e.tagName.toLowerCase() + (e.classList.length ? '.' + [].join.call(e.classList, '.') : '') + '（字）',
                 w: e.clientWidth, right: e.scrollWidth, id: a ? a.id : '',
                 ji: e.textContent.trim().slice(0, 40)});
    }
  });
  parent.postMessage(JSON.stringify({W: W, deta: deta}), '*');
}, 300); });
</script>
'''


def chrome():
    for c in [os.environ.get('CHROME', ''),
              '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
              shutil.which('google-chrome') or '', shutil.which('google-chrome-stable') or '',
              shutil.which('chromium') or '', shutil.which('chromium-browser') or '']:
        if c and os.path.exists(c):
            return c
    return None


def hakaru(exe, path, tmp):
    s = open(path, encoding='utf-8').read()
    s = s.replace(' loading="lazy"', '')
    i = s.rfind('</body>')
    s = (s[:i] + HAKARU + s[i:]) if i >= 0 else s + HAKARU
    utsushi = os.path.join(tmp, os.path.basename(path))
    open(utsushi, 'w', encoding='utf-8').write(s)
    waku = os.path.join(tmp, '__waku__.html')
    open(waku, 'w', encoding='utf-8').write(WAKU % (os.path.basename(path), HABA, TAKASA))
    r = subprocess.run([exe, '--headless=new', '--disable-gpu', '--no-sandbox',
                        '--hide-scrollbars', '--window-size=800,%d' % (TAKASA + 40),
                        '--virtual-time-budget=8000', '--dump-dom',
                        '--allow-file-access-from-files',
                        'file://' + waku],
                       capture_output=True, text=True, timeout=180)
    m = re.search(r'<pre id="__haba__">(.*?)</pre>', r.stdout, re.S)
    if not m:
        raise RuntimeError('%s：測れませんでした（Chrome の出力に結果がありません）\n%s'
                           % (os.path.basename(path), r.stderr[-800:]))
    return json.loads(html.unescape(m.group(1)))


def main():
    exe = chrome()
    if not exe:
        print('⚠ Chrome が見つからないので、スマホの幅は測りませんでした。')
        return 0
    names = sys.argv[1:] or sorted(os.path.basename(p) for p in glob.glob(os.path.join(OUT, '*.html')))
    names = [n for n in names if n not in NOZOKU]
    dame = 0
    with tempfile.TemporaryDirectory() as tmp:
        # 写しの横に、ページが読む小物（pdfjs など）も置いておきます
        for p in glob.glob(os.path.join(OUT, '*')):
            if not p.endswith('.html'):
                d = os.path.join(tmp, os.path.basename(p))
                (shutil.copytree if os.path.isdir(p) else shutil.copy)(p, d)
        for n in names:
            kekka = hakaru(exe, os.path.join(OUT, n), tmp)
            if kekka['W'] != HABA:
                raise RuntimeError('%s：幅が %dpx で開きました（%dpx のはず）' % (n, kekka['W'], HABA))
            deta = kekka['deta']
            if not deta:
                print('  ○ %-14s はみ出しなし（%dpx）' % (n, HABA))
                continue
            dame += 1
            print('  × %-14s %d か所が画面の外へ出ています（幅%dpx）' % (n, len(deta), HABA))
            # いちばん外側（親）から先に見せます。中身は親につられているだけのことが多いため
            mieta = set()
            for d in deta[:12]:
                key = (d['id'], d['tag'])
                if key in mieta:
                    continue
                mieta.add(key)
                if d.get('ji'):
                    print('      %s  箱%dpx に 字%dpx  （#%s の中）「%s…」' % (d['tag'], d['w'], d['right'], d['id'] or '-', d['ji']))
                else:
                    print('      %s  幅%dpx 右はし%dpx  （#%s の中）' % (d['tag'], d['w'], d['right'], d['id'] or '-'))
    if dame:
        print('\nスマホでくずれるので、公開を止めます。'
              '\n  いちばん上の要素が、たいてい原因です。#〜 は、どの札かの手がかりです。')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
