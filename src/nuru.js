/* ══════════════════════════════════════════════════════════
   塗る面（黒でぬる）　2026-09-22 夜
   ──────────────────────────────────────────────────────────
   送る前（実践を送る）と、**載ったあと**（実践の管理）の両方で、
   これ1つを使います。隠す道具を2つ持つと、いつか片方だけ直って、
   もう片方から漏れます。

   ★四角は 0〜1 の割合で持ちます。だから、見ている大きさ（拡大中でも）と
     送る大きさ（1400px でも 800px でも）で、同じ所が塗れます。
   ★塗るのは「縮めたあと」です。先に塗ってから縮めると、質を落とす段で
     にじんで、ふちから中身が透けます（→ kaku）。
   ★モザイクにはしません。粗さが足りないと元の字が読めることがあり、
     隠したつもりが隠れていない、がいちばん困るためです。

   ── 拡大（依頼）────────────────────────────────────────
   名札のような小さいものは、ぜんたいを見たままでは狙えません。
   拡大は **CSSの幅だけ** を変えます。四角は割合で持っているので、
   なぞる所の計算（nuri_ten）は 1行も変わりません。
   ・マウス／トラックパッド … ［＋］［－］で拡大、はみ出したぶんは
     入れ物をふつうにスクロールして動かします
   ・指 … 1本で塗る／**2本でつまんで拡大・動かす**
     （canvas は touch-action:none なので、2本ぶんはこちらで動かします）
   ══════════════════════════════════════════════════════════ */
window.NURU = (function(){
  'use strict';

  var SAI = .012;       /* これより小さい四角は、押しまちがいとみなします */
  var BAI_MIN = 1, BAI_MAX = 6;
  var BAI_DAN = 1.5;    /* ［＋］1回ぶん */

  /* 四角を黒でぬる。割合（0〜1）→ その canvas の画の数。 */
  function nuru(ctx, c, shikaku){
    if(!shikaku || !shikaku.length) return;
    ctx.fillStyle = '#000';
    shikaku.forEach(function(k){
      ctx.fillRect(Math.floor(k.x * c.width),  Math.floor(k.y * c.height),
                   Math.ceil(k.w * c.width),   Math.ceil(k.h * c.height));
    });
  }

  /* 縮めて、塗って、JPEGの data URI にして返します。 */
  function kaku(im, hen, omosa, shikaku){
    var w = im.width, h = im.height, r = Math.min(1, hen / Math.max(w, h));
    var c = document.createElement('canvas');
    c.width = Math.round(w * r); c.height = Math.round(h * r);
    var ctx = c.getContext('2d');
    ctx.drawImage(im, 0, 0, c.width, c.height);
    nuru(ctx, c, shikaku);
    return c.toDataURL('image/jpeg', omosa);
  }

  /* data URI の base64 から、おおよその KB */
  function nanKB(uri){ return (uri.length - uri.indexOf(',') - 1) * 3 / 4 / 1024; }

  /* 上限に収まるまで、質を落とし、それでもだめなら小さくします。
     収まらなければ null。**送る側は、null を黙って通してはいけません。** */
  function osameru(im, dan, kbMax, shikaku){
    for(var i = 0; i < dan.length; i++){
      var uri = kaku(im, dan[i][0], dan[i][1], shikaku);
      if(nanKB(uri) <= kbMax) return uri;
    }
    return null;
  }

  function shikaku_tsukuru(a, b){
    return { x: Math.min(a.x, b.x), y: Math.min(a.y, b.y),
             w: Math.abs(a.x - b.x), h: Math.abs(a.y - b.y) };
  }

  /* ══ 面ひとつ ═══════════════════════════════════════════
     opt … { na:画面に出す名前, moto:File か data URI の字,
             oya:入れる所, file:見分け用（任意）, haba:面の画の数（既定1400）,
             noboru:読めたときに呼ぶ（任意）, dame:読めなかったとき（任意） }  */
  function men(opt){
    var haba = opt.haba || 1400;
    var waku = document.createElement('figure');
    waku.className = 'nuru-1';
    waku.innerHTML =
      '<div class="nuru-mado"><canvas class="nuru-c"></canvas></div>'
    + '<figcaption class="nuru-b">'
    +   '<span class="nuru-na"></span>'
    +   '<span class="nuru-kazu" aria-live="polite">まだ ぬっていません</span>'
    +   '<span class="nuru-zoom">'
    +     '<button type="button" class="nuru-x nuru-chiisaku" aria-label="小さくする">－</button>'
    +     '<span class="nuru-bai">1.0倍</span>'
    +     '<button type="button" class="nuru-x nuru-ookiku" aria-label="大きくする">＋</button>'
    +   '</span>'
    +   '<button type="button" class="nuru-x nuru-modosu">ひとつ戻す</button>'
    +   '<button type="button" class="nuru-x nuru-zen">ぜんぶ消す</button>'
    + '</figcaption>';

    var n = {
      file: ('file' in opt) ? opt.file : null,
      na: opt.na || '', shikaku: [], im: null, ima: null, hajime: null,
      waku: waku,
      mado:   waku.querySelector('.nuru-mado'),
      canvas: waku.querySelector('.nuru-c'),
      kazu:   waku.querySelector('.nuru-kazu'),
      bai: 1
    };
    var modosu = waku.querySelector('.nuru-modosu');
    var zen    = waku.querySelector('.nuru-zen');
    var baiJi  = waku.querySelector('.nuru-bai');
    waku.querySelector('.nuru-na').textContent = n.na;
    n.canvas.setAttribute('aria-label', n.na + ' … 隠したいところを なぞる');

    function egaku(){
      if(!n.im) return;
      var c = n.canvas, ctx = c.getContext('2d');
      ctx.drawImage(n.im, 0, 0, c.width, c.height);
      nuru(ctx, c, n.shikaku);
      if(n.ima){   /* なぞっている最中のもの。ふちを白くして、分かるようにします */
        nuru(ctx, c, [n.ima]);
        ctx.strokeStyle = '#FCFBF7'; ctx.lineWidth = 3;
        ctx.strokeRect(n.ima.x * c.width, n.ima.y * c.height,
                       n.ima.w * c.width, n.ima.h * c.height);
      }
    }
    n.egaku = egaku;

    function kazoeru(){
      n.kazu.textContent = n.shikaku.length
        ? (n.shikaku.length + 'か所 ぬりました') : 'まだ ぬっていません';
      modosu.disabled = zen.disabled = !n.shikaku.length;
    }

    /* ── 拡大 ───────────────────────────────────────────
       変えるのは canvas の**CSSの幅**だけです。真ん中を見たまま
       大きくしたいので、入れ物のスクロールも一緒に動かします。 */
    function baisuru(atarashii, mannaka){
      var mae = n.bai;
      n.bai = Math.max(BAI_MIN, Math.min(BAI_MAX, atarashii));
      n.canvas.style.width = (n.bai * 100) + '%';
      baiJi.textContent = (Math.round(n.bai * 10) / 10).toFixed(1) + '倍';
      waku.querySelector('.nuru-chiisaku').disabled = n.bai <= BAI_MIN;
      waku.querySelector('.nuru-ookiku').disabled   = n.bai >= BAI_MAX;
      /* 見ていた所を、そのまま真ん中に置き直します */
      var m = n.mado, r = n.bai / mae;
      var mx = mannaka ? mannaka.x : m.clientWidth  / 2;
      var my = mannaka ? mannaka.y : m.clientHeight / 2;
      m.scrollLeft = (m.scrollLeft + mx) * r - mx;
      m.scrollTop  = (m.scrollTop  + my) * r - my;
    }
    n.baisuru = baisuru;
    waku.querySelector('.nuru-ookiku').addEventListener('click', function(){
      baisuru(n.bai * BAI_DAN);
    });
    waku.querySelector('.nuru-chiisaku').addEventListener('click', function(){
      baisuru(n.bai / BAI_DAN);
    });

    /* ── なぞる ─────────────────────────────────────────
       割合で持つので、拡大していても、ここは何も変わりません。 */
    function ten(ev){
      var r = n.canvas.getBoundingClientRect();
      return { x: Math.min(1, Math.max(0, (ev.clientX - r.left) / r.width)),
               y: Math.min(1, Math.max(0, (ev.clientY - r.top)  / r.height)) };
    }

    var yubi = {};      /* いま触っている指。2本になったら「つまむ」に変わります */
    var tsumami = null;

    function tsumami_hajime(){
      var k = Object.keys(yubi);
      if(k.length < 2) return;
      var a = yubi[k[0]], b = yubi[k[1]], m = n.mado.getBoundingClientRect();
      tsumami = {
        hanare: Math.hypot(a.x - b.x, a.y - b.y) || 1,
        bai: n.bai,
        naka: { x: (a.x + b.x) / 2 - m.left, y: (a.y + b.y) / 2 - m.top },
        su: { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 },
        scroll: { x: n.mado.scrollLeft, y: n.mado.scrollTop }
      };
      /* 途中まで引いていた四角は、つまんだ時点で取り消します
         （指2本めが乗った所まで塗られると、思っていない所が黒くなります） */
      n.hajime = null; n.ima = null; egaku();
    }

    n.canvas.addEventListener('pointerdown', function(ev){
      if(!n.im) return;
      ev.preventDefault();
      yubi[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
      if(Object.keys(yubi).length >= 2){ tsumami_hajime(); return; }
      n.hajime = ten(ev);
      try{ n.canvas.setPointerCapture(ev.pointerId); }catch(e){}
    });
    n.canvas.addEventListener('pointermove', function(ev){
      if(yubi[ev.pointerId]) yubi[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
      if(tsumami){
        var k = Object.keys(yubi);
        if(k.length < 2) return;
        var a = yubi[k[0]], b = yubi[k[1]];
        var ima = Math.hypot(a.x - b.x, a.y - b.y) || 1;
        n.bai = Math.max(BAI_MIN, Math.min(BAI_MAX, tsumami.bai * ima / tsumami.hanare));
        n.canvas.style.width = (n.bai * 100) + '%';
        baiJi.textContent = (Math.round(n.bai * 10) / 10).toFixed(1) + '倍';
        waku.querySelector('.nuru-chiisaku').disabled = n.bai <= BAI_MIN;
        waku.querySelector('.nuru-ookiku').disabled   = n.bai >= BAI_MAX;
        var r = n.bai / tsumami.bai;
        var naka = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
        n.mado.scrollLeft = (tsumami.scroll.x + tsumami.naka.x) * r - tsumami.naka.x
                          - (naka.x - tsumami.su.x);
        n.mado.scrollTop  = (tsumami.scroll.y + tsumami.naka.y) * r - tsumami.naka.y
                          - (naka.y - tsumami.su.y);
        return;
      }
      if(!n.hajime) return;
      n.ima = shikaku_tsukuru(n.hajime, ten(ev));
      egaku();
    });
    var oeru = function(ev){
      delete yubi[ev.pointerId];
      if(tsumami){
        if(Object.keys(yubi).length < 2) tsumami = null;
        return;
      }
      if(!n.hajime) return;
      var k = shikaku_tsukuru(n.hajime, ten(ev));
      n.hajime = null; n.ima = null;
      if(k.w > SAI && k.h > SAI) n.shikaku.push(k);
      egaku(); kazoeru();
    };
    n.canvas.addEventListener('pointerup', oeru);
    n.canvas.addEventListener('pointercancel', oeru);

    modosu.addEventListener('click', function(){ n.shikaku.pop(); egaku(); kazoeru(); });
    zen.addEventListener('click', function(){ n.shikaku = []; egaku(); kazoeru(); });

    /* ── 絵をのせる ─────────────────────────────────────
       canvas の画の数は、**元の絵の大きさまで**しか増やしません。
       増やしても中身は増えず、拡大したときにぼやけるだけだからです。 */
    function noseru(uri){
      var im = new Image();
      im.onerror = function(){ if(opt.dame) opt.dame(); };
      im.onload = function(){
        n.im = im;
        n.canvas.width  = Math.min(haba, im.width);
        n.canvas.height = Math.round(n.canvas.width * im.height / im.width);
        egaku();
        if(opt.noboru) opt.noboru(n);
      };
      im.src = uri;
    }
    if(typeof opt.moto === 'string'){
      noseru(opt.moto);
    } else {
      var fr = new FileReader();
      fr.onerror = function(){ if(opt.dame) opt.dame(); };
      fr.onload = function(){ noseru(fr.result); };
      fr.readAsDataURL(opt.moto);
    }

    kazoeru();
    baisuru(1);
    if(opt.oya) opt.oya.appendChild(waku);
    return n;
  }

  return { men: men, nuru: nuru, kaku: kaku, osameru: osameru,
           nanKB: nanKB, SAI: SAI };
})();
