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
   なぞる所の計算（ten）は 1行も変わりません。
   ・指 … 1本で塗る／**2本でつまんで拡大・動かす**
     （canvas は touch-action:none なので、2本ぶんはこちらで動かします）
   ・トラックパッド … **2本指でつまむ**（＝ctrl+ホイール）でも拡大します
   ・マウス … ［＋］［－］。**編集画面の中では、ただのホイールでも**拡大します
     （編集画面はページを送る必要がないので、ホイールを拡大に使えます）

   ── 置いた黒を、あとから動かす（2026-09-23 依頼）──────────
   「一度おいた黒いのを選択して動かせるようにしたい」
   ・黒いところを押す → **えらんだ状態**（白い点線と、四すみのつまみ）
   ・中をドラッグ   → そのまま動かす
   ・角のつまみをドラッグ → 大きさを変える
   ・［この黒を消す］ → えらんでいる1つだけ消す
   ・何もない所を押す → えらびを外す。そのままドラッグで新しく塗る

   ★「黒の上から新しく塗る」はできません。黒の上で押すと、そちらを
     えらんだことになるためです。重ねたいときは、黒の外から引いてください。
   ★あたり判定は **割合のまま**やります。拡大していても、つまみの大きさ
     だけは画面の px でそろえます（指で押せる大きさを保つため）。

   ── 編集画面（2026-09-23 依頼）──────────────────────────
   「編集画面にしてもっと使いやすいようにしたい」
   ［大きく編集］で、面をそのまま画面いっぱいの入れ物へ **引っ越します**。
   ★作り直しません。同じ要素を動かすだけなので、塗ったものも拡大率も
     そのまま残ります（2つ作ると、いつか片方だけ直って ずれます）。
   ══════════════════════════════════════════════════════════ */
window.NURU = (function(){
  'use strict';

  var SAI = .012;       /* これより小さい四角は、押しまちがいとみなします */
  var TSUMAMI = 26;     /* 角のつまみ（画面のpx）。指で押せる大きさにします */
  var ima_ooki = null;  /* いま編集画面にいる面（1つだけ） */
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

  /* ══ 編集画面の入れ物 ═══════════════════════════════════
     ページに1つだけ作ります。中身は、そのとき編集している面が
     引っ越してくるので、ここは **空の箱**です。                 */
  function ooki_bako(){
    var b = document.getElementById('nuru-ooki');
    if(b) return b;
    b = document.createElement('div');
    b.id = 'nuru-ooki';
    b.className = 'nuru-ooki';
    b.hidden = true;
    b.innerHTML = '<div class="nuru-ooki-naka" role="dialog" aria-modal="true"'
                + ' aria-label="隠すところを編集"></div>';
    /* 外がわ（黒いところ）を押したら とじます。中は素通しにします */
    b.addEventListener('pointerdown', function(ev){
      if(ev.target === b && ima_ooki) ima_ooki.dekaku(false);
    });
    document.addEventListener('keydown', function(ev){
      if(ev.key === 'Escape' && ima_ooki && !ima_ooki.shikaku[ima_ooki.eranda]){
        ima_ooki.dekaku(false);
      }
    });
    document.body.appendChild(b);
    return b;
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
    +   '<button type="button" class="nuru-x nuru-kesu">この黒を消す</button>'
    +   '<button type="button" class="nuru-x nuru-modosu">ひとつ戻す</button>'
    +   '<button type="button" class="nuru-x nuru-zen">ぜんぶ消す</button>'
    +   '<button type="button" class="nuru-x nuru-dekai">大きく編集</button>'
    + '</figcaption>'
    + '<p class="nuru-tetsudai">黒いところを<b>押すとえらべます</b>。'
    +   'そのまま動かす／角をつまんで大きさを変える。'
    +   '何もない所をなぞると、新しく塗れます。</p>';

    var n = {
      file: ('file' in opt) ? opt.file : null,
      na: opt.na || '', shikaku: [], im: null, ima: null, hajime: null,
      waku: waku,
      mado:   waku.querySelector('.nuru-mado'),
      canvas: waku.querySelector('.nuru-c'),
      kazu:   waku.querySelector('.nuru-kazu'),
      bai: 1,
      eranda: -1,      /* えらんでいる四角の番号。-1 は「えらんでいない」 */
      dekai: false     /* 編集画面にいるか */
    };
    var modosu = waku.querySelector('.nuru-modosu');
    var zen    = waku.querySelector('.nuru-zen');
    var kesu   = waku.querySelector('.nuru-kesu');
    var dekaiB = waku.querySelector('.nuru-dekai');
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
      /* えらんでいる1つ（2026-09-23 依頼）。
         ★点線と、四すみのつまみ。黒の上なので、白で描きます。
         ★線とつまみは **画面の px でそろえます**。拡大すると canvas の
           1px は画面では小さくなるので、そのぶん太く描かないと、
           4倍にしたときに線が見えなくなります。 */
      var k = n.shikaku[n.eranda];
      if(k){
        var r = c.getBoundingClientRect();
        var bai = (r.width ? c.width / r.width : 1);   /* 画面1px ＝ canvas 何px */
        var x = k.x * c.width, y = k.y * c.height;
        var w = k.w * c.width, h = k.h * c.height;
        ctx.save();
        ctx.strokeStyle = '#FCFBF7'; ctx.lineWidth = 2 * bai;
        ctx.setLineDash([8 * bai, 6 * bai]);
        ctx.strokeRect(x, y, w, h);
        ctx.setLineDash([]);
        ctx.fillStyle = '#FCFBF7'; ctx.strokeStyle = '#1C1C1A';
        ctx.lineWidth = 2 * bai;
        [[x, y], [x + w, y], [x, y + h], [x + w, y + h]].forEach(function(t){
          ctx.beginPath();
          ctx.arc(t[0], t[1], TSUMAMI * bai / 2, 0, Math.PI * 2);
          ctx.fill(); ctx.stroke();
        });
        ctx.restore();
      }
    }
    n.egaku = egaku;

    /* ── あたり判定 ─────────────────────────────────────
       割合のままくらべます。つまみだけは、画面の px を割合に直してから
       くらべます（拡大しても、指で押せる大きさを保つため）。 */
    function atari_tsumami(p){
      var k = n.shikaku[n.eranda];
      if(!k) return null;
      var r = n.canvas.getBoundingClientRect();
      var tx = (TSUMAMI / 2 + 6) / (r.width  || 1);
      var ty = (TSUMAMI / 2 + 6) / (r.height || 1);
      var kado = [['nw', k.x, k.y], ['ne', k.x + k.w, k.y],
                  ['sw', k.x, k.y + k.h], ['se', k.x + k.w, k.y + k.h]];
      for(var i = 0; i < kado.length; i++){
        if(Math.abs(p.x - kado[i][1]) <= tx && Math.abs(p.y - kado[i][2]) <= ty){
          return kado[i][0];
        }
      }
      return null;
    }
    function atari_shikaku(p){
      /* 重なっているときは、**あとから置いたほう**（上に見えているほう）。 */
      for(var i = n.shikaku.length - 1; i >= 0; i--){
        var k = n.shikaku[i];
        if(p.x >= k.x && p.x <= k.x + k.w && p.y >= k.y && p.y <= k.y + k.h) return i;
      }
      return -1;
    }
    function erabu(i){
      if(n.eranda === i) return;
      n.eranda = i;
      egaku(); kazoeru();
    }
    n.erabu = erabu;

    function kazoeru(){
      n.kazu.textContent = n.shikaku.length
        ? (n.shikaku.length + 'か所 ぬりました'
           + (n.shikaku[n.eranda] ? '（1つ えらんでいます）' : ''))
        : 'まだ ぬっていません';
      modosu.disabled = !rireki.length;      /* 動かしたぶんも戻せます */
      zen.disabled = !n.shikaku.length;
      kesu.disabled = !n.shikaku[n.eranda];
    }

    /* ── 拡大 ───────────────────────────────────────────
       変えるのは canvas の**CSSの幅**だけです。真ん中を見たまま
       大きくしたいので、入れ物のスクロールも一緒に動かします。 */
    /* 1.0倍のときの大きさ（2026-09-23 依頼）。
       ふつうの面は「幅いっぱい」が1.0倍です（はみ出したぶんはスクロール）。
       **編集画面の中だけ**は「まるごと収まる大きさ」を1.0倍にします。
       あちらは窓の高さが決まっているので、幅いっぱいのままだと、たての
       写真が窓からはみ出して、ぜんたいを見ながら塗れなくなるためです。 */
    function motozumi(){
      if(!n.dekai || !n.im) return 1;
      var hb = n.mado.clientWidth, tk = n.mado.clientHeight;
      if(!hb || !tk || !n.canvas.width) return 1;
      var takasa = hb * (n.canvas.height / n.canvas.width);   /* 幅いっぱいの高さ */
      return takasa > tk ? (tk / takasa) : 1;
    }

    function baisuru(atarashii, mannaka){
      var mae = n.bai;
      n.bai = Math.max(BAI_MIN, Math.min(BAI_MAX, atarashii));
      n.canvas.style.width = (n.bai * motozumi() * 100) + '%';
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
         （指2本めが乗った所まで塗られると、思っていない所が黒くなります）。
         動かしかけ・大きさを変えかけのものも、つまんだ時点で元に戻します。 */
      if(ugoki && ugoki.moto && n.shikaku[n.eranda]) n.shikaku[n.eranda] = ugoki.moto;
      ugoki = null;
      n.hajime = null; n.ima = null; egaku();
    }

    /* いまの手つき。'hiku'＝新しく塗る、'utsusu'＝動かす、'nobasu'＝大きさを変える */
    var ugoki = null;
    function kopi(k){ return { x: k.x, y: k.y, w: k.w, h: k.h }; }

    /* ── ひとつ戻す（2026-09-23 依頼で作り直し）──────────────
       前は「最後に置いた1つを取る」だけでした。動かせるようにしたので、
       **うっかり動かした**ときに戻せないのが、いちばん困ります
       （黒を1つずらすと、隠していたはずの名札が出てしまいます）。
       変える前のぜんぶを控えて、そこへ戻す形にします。 */
    var rireki = [];
    function oboeru(){
      rireki.push(n.shikaku.map(kopi));
      if(rireki.length > 30) rireki.shift();   /* 控えは30手ぶんまで */
    }

    n.canvas.addEventListener('pointerdown', function(ev){
      if(!n.im) return;
      ev.preventDefault();
      yubi[ev.pointerId] = { x: ev.clientX, y: ev.clientY };
      if(Object.keys(yubi).length >= 2){ tsumami_hajime(); return; }
      var p = ten(ev);
      /* ① えらんでいる四角の角 → 大きさを変える
         ② どれかの黒の中     → その1つをえらんで、動かす
         ③ 何もない所         → えらびを外して、新しく塗る          */
      var kado = atari_tsumami(p);
      if(kado){
        oboeru();
        ugoki = { shurui: 'nobasu', kado: kado, moto: kopi(n.shikaku[n.eranda]) };
      } else {
        var i = atari_shikaku(p);
        if(i >= 0){
          n.eranda = i; egaku(); kazoeru();
          oboeru();
          ugoki = { shurui: 'utsusu', hajime: p, moto: kopi(n.shikaku[i]) };
        } else {
          if(n.eranda >= 0){ n.eranda = -1; egaku(); kazoeru(); }
          n.hajime = p;
          ugoki = { shurui: 'hiku' };
        }
      }
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
        n.canvas.style.width = (n.bai * motozumi() * 100) + '%';
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
      if(!ugoki) return;
      var p = ten(ev);
      if(ugoki.shurui === 'hiku'){
        if(!n.hajime) return;
        n.ima = shikaku_tsukuru(n.hajime, p);
        egaku();
        return;
      }
      var k = n.shikaku[n.eranda];
      if(!k) return;
      if(ugoki.shurui === 'utsusu'){
        /* そのまま平行に動かします。面からはみ出さないように止めます */
        var m = ugoki.moto;
        k.x = Math.min(1 - m.w, Math.max(0, m.x + (p.x - ugoki.hajime.x)));
        k.y = Math.min(1 - m.h, Math.max(0, m.y + (p.y - ugoki.hajime.y)));
      } else {
        /* つまんだ角だけを動かします。向かいの角は止めたままです。
           'nw' に 'w' が入っていれば左、'n' が入っていれば上、という見方。 */
        var o = ugoki.moto;
        var x1 = o.x, y1 = o.y, x2 = o.x + o.w, y2 = o.y + o.h;
        if(ugoki.kado.indexOf('w') >= 0) x1 = p.x; else x2 = p.x;
        if(ugoki.kado.indexOf('n') >= 0) y1 = p.y; else y2 = p.y;
        k.x = Math.max(0, Math.min(x1, x2));
        k.y = Math.max(0, Math.min(y1, y2));
        k.w = Math.min(1 - k.x, Math.abs(x2 - x1));
        k.h = Math.min(1 - k.y, Math.abs(y2 - y1));
      }
      egaku();
    });
    var oeru = function(ev){
      delete yubi[ev.pointerId];
      if(tsumami){
        if(Object.keys(yubi).length < 2) tsumami = null;
        return;
      }
      if(!ugoki) return;
      if(ugoki.shurui === 'hiku'){
        if(n.hajime){
          var k = shikaku_tsukuru(n.hajime, ten(ev));
          n.hajime = null; n.ima = null;
          /* 引いたものが小さすぎるときは、押しまちがいとして捨てます。
             ★ただし、置いたぶんは **そのままえらんだ状態**にします。
               置いてすぐ動かしたい、がふつうだからです。 */
          if(k.w > SAI && k.h > SAI){
            oboeru();
            n.shikaku.push(k);
            n.eranda = n.shikaku.length - 1;
          }
        }
      } else {
        /* 動かした／大きさを変えたあと。つぶれていたら、元に戻します
           （消したいときは［この黒を消す］。うっかり消えると気づけません） */
        var s2 = n.shikaku[n.eranda];
        if(s2 && (s2.w <= SAI || s2.h <= SAI)) n.shikaku[n.eranda] = ugoki.moto;
        /* **押しただけ**（えらんだだけで動かしていない）ときは、控えを取り消します。
           取り消さないと［ひとつ戻す］が、何も起きない空振りを1回はさみます。 */
        s2 = n.shikaku[n.eranda];
        var m2 = ugoki.moto;
        if(s2 && m2 && s2.x === m2.x && s2.y === m2.y && s2.w === m2.w && s2.h === m2.h){
          rireki.pop();
        }
      }
      ugoki = null;
      egaku(); kazoeru();
    };
    n.canvas.addEventListener('pointerup', oeru);
    n.canvas.addEventListener('pointercancel', oeru);

    modosu.addEventListener('click', function(){
      if(!rireki.length) return;
      n.shikaku = rireki.pop();
      n.eranda = -1; egaku(); kazoeru();
    });
    zen.addEventListener('click', function(){
      if(!n.shikaku.length) return;
      oboeru();
      n.shikaku = []; n.eranda = -1; egaku(); kazoeru();
    });
    /* えらんでいる1つだけ消します（2026-09-23 依頼）。
       ［ひとつ戻す］は「最後に置いたもの」なので、途中の1つは消せませんでした。 */
    kesu.addEventListener('click', function(){
      if(!n.shikaku[n.eranda]) return;
      oboeru();
      n.shikaku.splice(n.eranda, 1);
      n.eranda = -1; egaku(); kazoeru();
    });

    /* ── 手で自由に拡大（2026-09-23 依頼）──────────────────
       ★ふだんは **ctrl（＝トラックパッドの2本指でつまむ）のときだけ**です。
         ただのホイールまで奪うと、面の上でページを送れなくなります。
       ★編集画面の中では、ただのホイールでも拡大します。あちらは
         ページを送る必要がないので、奪っても困りません。
       ★指でつまむぶんは、上の tsumami が受けもちます。 */
    n.mado.addEventListener('wheel', function(ev){
      if(!n.im) return;
      if(!ev.ctrlKey && !n.dekai) return;
      ev.preventDefault();
      var m = n.mado.getBoundingClientRect();
      baisuru(n.bai * Math.pow(1.0025, -ev.deltaY),
              { x: ev.clientX - m.left, y: ev.clientY - m.top });
    }, { passive: false });

    /* えらんでいる1つを、Delete／BackSpace でも消せます（PCの人むけ）。
       Escape は、えらびを外す／編集画面をとじる。 */
    n.canvas.setAttribute('tabindex', '0');
    n.canvas.addEventListener('keydown', function(ev){
      if((ev.key === 'Delete' || ev.key === 'Backspace') && n.shikaku[n.eranda]){
        ev.preventDefault();
        oboeru();
        n.shikaku.splice(n.eranda, 1);
        n.eranda = -1; egaku(); kazoeru();
      } else if(ev.key === 'Escape' && n.eranda >= 0){
        ev.preventDefault();
        n.eranda = -1; egaku(); kazoeru();
      }
    });

    /* ── 編集画面（2026-09-23 依頼）───────────────────────
       面を作り直さず、**同じ要素を引っ越します**。塗ったものも拡大率も
       そのまま残ります。戻る場所は、印（コメント）を置いて覚えておきます。 */
    dekaiB.addEventListener('click', function(){ dekaku(!n.dekai); });
    function dekaku(yaru){
      var bako = ooki_bako(), naka = bako.querySelector('.nuru-ooki-naka');
      if(yaru){
        if(ima_ooki && ima_ooki !== n) ima_ooki.dekaku(false);
        n.modoru = document.createComment('nuru');
        waku.parentNode.insertBefore(n.modoru, waku);
        naka.appendChild(waku);
        waku.classList.add('nuru-1--ooki');
        bako.hidden = false;
        document.documentElement.classList.add('nuru-tomeru');
        n.dekai = true; ima_ooki = n;
        dekaiB.textContent = 'とじる';
        try{ n.canvas.focus({ preventScroll: true }); }catch(e){}
      } else {
        if(n.modoru && n.modoru.parentNode){
          n.modoru.parentNode.insertBefore(waku, n.modoru);
          n.modoru.parentNode.removeChild(n.modoru);
        }
        n.modoru = null;
        waku.classList.remove('nuru-1--ooki');
        bako.hidden = true;
        document.documentElement.classList.remove('nuru-tomeru');
        n.dekai = false; if(ima_ooki === n) ima_ooki = null;
        dekaiB.textContent = '大きく編集';
      }
      /* 入れ物の幅が変わったので、拡大率はそのままに置き直します */
      baisuru(n.bai);
      egaku();
    }
    n.dekaku = dekaku;
    /* 画面の向きが変わったら、編集画面の中の大きさを取り直します */
    window.addEventListener('resize', function(){
      if(n.dekai) baisuru(n.bai);
    });

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
