/**
 * 板書を受けとる（サイトの中の入力欄 → ここ → 管理人 → GitHub）
 * ─────────────────────────────────────────────────────────
 * 2026-09-21
 *
 * なぜ要るのか
 *   実践フォームには「ファイル添付」の設問があります。添付が1つでもあると、
 *   Googleは**全員にログインを求めます**（実機で確認しました）。
 *   ログイン画面が出たら、そこで終わりです。「誰でも簡単に」になりません。
 *   だから、写真はサイトの入力欄から ここへ直接送ります。ログインは要りません。
 *
 * 流れ
 *   1. サイトの「送る」を押す
 *   2. ブラウザが写真を その場で小さくして（長辺1400px・JPEG）ここへ送る
 *   3. ここが Drive に保存し、管理人にメールを1通出す
 *      （メールの中に［載せる］［載せない］のボタン）
 *   4. ［載せる］を押すと、GitHub に写真が増える
 *   5. Actions が build.py を走らせて、板書のページが新しくなる
 *
 *   押すまでは、サイトには1枚も出ません。
 *
 * 置き方
 *   Apps Script の新しいプロジェクト → このコードを貼る
 *   → デプロイ → 新しいデプロイ → 種類「ウェブアプリ」
 *       次のユーザーとして実行：自分
 *       アクセスできるユーザー：**全員**      ← ログイン無しで送るのに要ります
 *   → 出てきたURL（https://script.google.com/macros/s/……/exec）を
 *     src/hiroba.html の  var OKURU_URL = '';  に貼る
 *
 * 先に入れておくもの（プロジェクトの設定 → スクリプト プロパティ）
 *   ★ GITHUB_TOKEN … GitHubの細かい権限つきトークン（Contents: Read and write）
 *      これ **1つだけ** 入れてください。ほかは空でも動きます。
 *
 *   ほかのものは、空なら次のように自分で決めます。
 *     ADMIN_MAIL    … デプロイした人（あなた）のアドレス
 *     GITHUB_REPO   … yuutennis657-beep/tokkatsu-hiroba
 *     GITHUB_BRANCH … main
 *     WEBAPP_URL    … このウェブアプリ自身のURL
 *     DRIVE_FOLDER  … マイドライブの直下
 *
 * ★ 置き場所について（tokkatu-78 が作っている板書のページに合わせるところ）
 *   写真は  src/bansho/<フォルダ名>/01.jpg 02.jpg …  に置きます
 *   （しっぽは中身に合わせます。WebP で送られたら 01.webp です → _shippo）。
 *   フォルダ名は英小文字・数字・- だけ（build.py がそう検問しています）。
 *   ★ 写真だけ置いても、板書のページには出ません（2026-09-21 実測）。
 *     build.py は写真のフォルダを直接は見ず、src/jissen/*.md の bansho: から
 *     辿ります。だから .md も一緒に作ります（MD_MO_TSUKURU = true）。
 */

/* ══ 0. 設定 ══════════════════════════════════════════════ */

var P = PropertiesService.getScriptProperties();

var MAI_MAX      = 6;        // 1回に受けとる枚数（2026-09-23：3→6）
/* ★フォーム（src/hiroba.html の MAI）は 4枚です。ここを **わざと多め**に
   してあります。理由は2つ。
     ・ここを超えたぶんは .slice で **黙って捨てます**。送信は no-cors
       なので、断っても画面には「送りました」と出ます。つまり受け口が
       フォームより少ないと、先生の写真が音もなく消えます。
     ・ここを直すには clasp の貼り直しが要ります（フォームは push だけ）。
   だから 4枚 → 6枚 までは、貼り直さずにフォームだけで動かせます。
   ★逆に、フォームをここより多くしてはいけません。 */
var KB_MAX       = 400;      // 写真1枚の上限（これを超えたら断る）
var PDF_MB_MAX   = 8;        // PDF1つの上限。GitHubに置いたあと Actions が画像にします
var MD_MO_TSUKURU = true;    // 写真だけ置いても出ません。.md が要ります（2026-09-21 確認）

/* ── 1日に受けとる上限（2026-09-21）────────────────────────
   URLは公開なので、誰でも送れます。それが狙いですが、裏返すと
   誰でも送れます。いたずらが続くと、Driveと受信箱が埋まります。
   ★ふつうの先生が1日に40件も送ることはありません。
     つまり これに当たるのは、いたずらのときだけです。
   上限に当たったら、その回は保存もメールもしません。
   知らせは1日1通だけ出します（同じ知らせで受信箱を埋めないため）。 */
var HI_MAX = 40;

function _p(k, moto) { return (P.getProperty(k) || moto || '').trim(); }

/* ══ 0の2. あいことば（2026-09-22 夜）════════════════════════
   ここを入れるまで、消すところは **誰でも押せました**。
   ウェブアプリのURLは公開ページのソースに書いてあり（書かないと送れない）、
   消す先の名前も id="b-bansho-…" としてページに出ています。
   つまり、ソースを見た人なら誰でも どの1件でも消せる状態でした。

   直し方は「合いことば」です。ログインは要りません。
     ・送るとき、送る人のブラウザが長いでたらめな合いことばを1つ作る
     ・**そのハッシュだけ**を投稿にくっつけて送る（合いことばは送らない）
     ・合いことばは、その人のブラウザの中にだけ残る
     ・消す／なおすときは合いことばを添える。こちらはハッシュと
       突き合わせて、合った人だけ通す
     ・管理人のあいことば（KANRI_KEY）は、ぜんぶにきく

   ★KANRI_KEY が無ければ、初めて要るときに自分で作って控えます。
     入れてもらう設定を1つも増やさないためです。作った合いことばは、
     そのときの知らせのメールに1度だけ出します。                    */
function _kanri_key() {
  var k = _p('KANRI_KEY');
  if (!k) {
    k = Utilities.getUuid().replace(/-/g, '');
    P.setProperty('KANRI_KEY', k);
  }
  return k;
}

/* 合いことば → ハッシュ（16進の字）。同じ字からは いつも同じ答えが出ます。
   逆に、ハッシュから合いことばは出せません。だから公開の .md に
   書いてあっても、そこから消せるようにはなりません。 */
function _hash(s) {
  var b = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256,
                                  String(s), Utilities.Charset.UTF_8);
  var ji = '';
  for (var i = 0; i < b.length; i++) {
    ji += ('0' + (b[i] & 0xFF).toString(16)).slice(-2);
  }
  return ji;
}

/* 送られてきたハッシュが、本物の形をしているか。
   でたらめな字を .md に書きこませないための関門です。 */
function _nushi_arau(s) {
  s = String(s || '').trim().toLowerCase();
  return /^[0-9a-f]{64}$/.test(s) ? s : '';
}

/* 入れてもらうものを1つに減らすため、空のときは自分で決めます。
   ここで決められないのは GITHUB_TOKEN だけです（合言葉なので、
   人の手で入れてもらうしかありません）。 */
/* ★ 匿名で開かれたとき、Session.getEffectiveUser().getEmail() は **空** を返します
   （2026-09-21、メールが1通も来なくてここに行き当たりました）。
   だから ADMIN_MAIL を先に控えておきます。控えるのが saisho_ni_ichido()。 */
function _mail() {
  return _p('ADMIN_MAIL') || Session.getEffectiveUser().getEmail();
}

/* ══ 最初に1回だけ ════════════════════════════════════════
   Apps Script のエディタで、この関数をえらんで ▶ を押してください。
   あなたのアドレスを覚えます。**これをやらないと、メールは飛びません。**
   （エディタから走らせたときだけ、Apps Script はアドレスを教えてくれます） */
function saisho_ni_ichido() {
  var m = Session.getEffectiveUser().getEmail();
  if (!m) throw new Error('アドレスが取れませんでした。ログインを確かめてください');
  P.setProperty('ADMIN_MAIL', m);
  MailApp.sendEmail(m, '【TOKKATSU広場】板書の受け口、ここまで届いています',
    'このメールが読めていれば、板書の知らせも届きます。\n\n' +
    '　覚えたアドレス：' + m + '\n');
  return m;
}
function _webapp() {
  var u = _p('WEBAPP_URL');
  if (u) return u;
  try { return ScriptApp.getService().getUrl(); } catch (e) { return ''; }
}


/* ══ 1. サイトからの受け口 ════════════════════════════════ */

function doPost(e) {
  try {
    /* 管理画面の入り口。管理キーはURLに入れず、POSTで受けます。
       返事は隠し iframe から postMessage で親の画面へ戻します。
       ここを通っても編集権限を渡すわけではありません。
       実際の更新は _naosu がもう1度 KANRI_KEY を確かめます。 */
    if (e.parameter && e.parameter.kind === 'kanri-check') {
      return _kanri_check(e.parameter);
    }
    if (e.parameter && e.parameter.kind === 'kanri-kesu') {
      return _kanri_kesu(e.parameter);
    }
    /* どの画面が見られているか（2026-09-22）。管理人だけが読めます。 */
    if (e.parameter && e.parameter.kind === 'kanri-miru') {
      return _kanri_miru(e.parameter);
    }
    /* その数を、ぜんぶ 0 に戻す（2026-09-23 依頼）。管理人だけができます。 */
    if (e.parameter && e.parameter.kind === 'kanri-miru-kesu') {
      return _kanri_miru_kesu(e.parameter);
    }
    /* 管理人だけのメモ（2026-09-22）。公開ページにも GitHub にも出ません。 */
    if (e.parameter && e.parameter.kind === 'kanri-memo-yomu') {
      return _kanri_memo_yomu(e.parameter);
    }
    if (e.parameter && e.parameter.kind === 'kanri-memo-kaku') {
      return _kanri_memo_kaku(e.parameter);
    }
    /* 管理画面内の編集。通常のJSON送信と違い、form POSTで
       送るので、ここで受ける。返事はpostMessageで元の画面へ戻す。 */
    if (e.parameter && e.parameter.kind === 'kanri-naosu') {
      e.parameter.kanri = '1';
      e.parameter.by_atarashii = '1';
      /* 管理画面から、載ったあとに塗った写真が来ることがあります（2026-09-22 夜）。
         form POST なので、同じ名前の欄が写真の枚数だけ並びます。
         ★e.parameter は1つめの**字**しか持ちません。そのまま _naosu へ渡すと
           (d.e||[]).slice(0,3) が「字の先頭3文字」を切り出し、写真が壊れます。
           何枚めかを持っている e.parameters のほうを渡します。 */
      if (e.parameters && e.parameters.e && e.parameters.e.length) {
        e.parameter.e = e.parameters.e;
      } else {
        delete e.parameter.e;      // 空の欄が来ても「差しかえ」にしない
      }
      return _naosu(e.parameter, true);
    }
    var d = JSON.parse(e.postData.contents);

    // 見られた数（2026-09-22）。いちばん軽いので、いちばん先に返します。
    if (d.kind === 'miru') return _miru(d);

    // やってみたい（2026-09-23 依頼）。押した1回を、その実践に足します。
    if (d.kind === 'yaritai') return _yaritai(d);

    // 困りごと（2026-09-21 夜）。字だけなので、Driveには残しません。
    if (d.kind === 'komari') return _komari(d);

    // 研究日程（2026-09-22）。これも字だけです。
    if (d.kind === 'nittei') return _nittei(d);

    // お悩みへの答え（2026-09-24）。字だけ。お悩みにぶら下がります。
    if (d.kind === 'kotae') return _kotae_okuru(d);

    // 学級会グッズ（2026-09-24 依頼）。PDF・Word・PowerPoint・Excel を
    //   そのまま配ります（画像に変えません）。→ _goods
    if (d.kind === 'goods') return _goods(d);

    // なおす（2026-09-22 夜）。本人と管理人だけ通ります（→ _naosu）
    if (d.kind === 'naosu') return _naosu(d);

    var shashin = (d.e || []).slice(0, MAI_MAX);
    var pdfs    = (d.p || []).slice(0, 1);        // PDFは1つまで（2026-09-21 夜）
    if (!shashin.length && !pdfs.length) {
      return _kotae({ ok: false, riyu: '写真もPDFもありません' });
    }

    if (!_kazoeru()) return _kotae({ ok: false, riyu: '今日はもう受けとれません' });

    var slug = _slug();
    var folder = _folder(slug);
    var uri = [], pdf = null;

    for (var i = 0; i < shashin.length; i++) {
      var b = _dataURI(shashin[i]);
      if (!b) return _kotae({ ok: false, riyu: '写真の形が読めません' });
      /* しっぽは中身から決めます（→ _shippo）。知らない形は断ります。
         置いてから気づくと、その1枚が数に入らず、ビルドが止まります。 */
      var shippo = _shippo(b);
      if (!shippo) {
        return _kotae({ ok: false, riyu: 'この形の写真は受けとれません（JPEG・PNG・WebPだけ）' });
      }
      if (b.getBytes().length > KB_MAX * 1024) {
        return _kotae({ ok: false, riyu: '写真が大きすぎます（1枚 ' + KB_MAX + 'KBまで）' });
      }
      var na = ('0' + (i + 1)).slice(-2) + shippo;
      folder.createFile(b.setName(na));
      uri.push({ na: na, b64: Utilities.base64Encode(b.getBytes()) });
    }

    /* PDFは縮めずにそのまま。GitHubに置いたあと、Actions が
       1ページ＝1枚の画像に変えて、HTMLの中に入れます。 */
    if (pdfs.length) {
      var pb = _dataURI_pdf(pdfs[0]);
      if (!pb) return _kotae({ ok: false, riyu: 'PDFの形が読めません' });
      if (pb.getBytes().length > PDF_MB_MAX * 1024 * 1024) {
        return _kotae({ ok: false, riyu: 'PDFが大きすぎます（' + PDF_MB_MAX + 'MBまで）' });
      }
      folder.createFile(pb.setName('shiryo.pdf'));
      pdf = Utilities.base64Encode(pb.getBytes());
    }

    /* ★ 2026-09-21 夜、ここを変えました。
       いままでは「管理人が［載せる］を押すまで、サイトには1枚も出ない」でした。
       いまは **そのまま載せます**。誰の目も通りません。
       そのかわり、知らせに［すぐ消す］を付けています。 */
    var n = { uri: uri, pdf: pdf, t: d.t || '', g: d.g || '', m: d.m || '',
              n: d.n || '', na: d.na || '', sh: d.sh || '', ko: !!d.ko,
              /* 送った人の合いことばの**ハッシュ**。合いことばそのものは
                 こちらには来ません（来ないほうが安全です）。 */
              nushi: _nushi_arau(d.nushi) };
    var nose = { ok: false, riyu: '' };
    try {
      _noseru(slug, n);
      nose.ok = true;
    } catch (err2) {
      nose.riyu = String(err2);   // 載せられなくても、写真はDriveに残っています
    }

    _shiraseru(slug, d, folder, nose);
    return _kotae({ ok: true, noseta: nose.ok });

  } catch (err) {
    return _kotae({ ok: false, riyu: String(err) });
  }
}

/* ══ 1の2. 困りごと ═══════════════════════════════════════
   字だけです。送られたら、そのまま komari.html に出ます。
   ★誰の目も通りません。知らせの［すぐ消す］で1押しで下ろせます。 */
function _komari(d) {
  var m = _arau_hon(d.m);
  if (!m) return _kotae({ ok: false, riyu: '中身がありません' });
  if (!_kazoeru()) return _kotae({ ok: false, riyu: '今日はもう受けとれません' });

  var slug = _slug('komari');
  var nose = { ok: false, riyu: '' };
  try {
    _github('src/komari/' + _kyou() + '_' + slug + '.md',
            Utilities.base64Encode(_md_komari(d, m), Utilities.Charset.UTF_8),
            '困りごとを1件のせる（' + slug + '）');
    nose.ok = true;
  } catch (err) {
    nose.riyu = String(err);
  }
  _shiraseru_komari(slug, d, m, nose);
  return _kotae({ ok: true, noseta: nose.ok });
}

/* ══ 1の3. お悩みへの答え（2026-09-24 依頼）════════════════
   「外部から答えとか『こんなふうにやっています』って回答できるように」
   LINEの答えは流れて消えます。ここに残れば、あとから同じ困りごとの人が
   読めます。字だけなので、Driveには残しません（困りごとと同じ）。

   ★ぶら下がる相手（toi）が、**いま本当にあるか**を確かめてから置きます。
     消えたお悩みへの答えを置くと、どこにも出ない .md が溜まります
     （build.py は相手のいない答えを飛ばすので、止まりはしません）。 */
function _kotae_okuru(d) {
  var m = _arau_hon(d.m);
  if (!m) return _kotae({ ok: false, riyu: '中身がありません' });
  var toi = String(d.toi || '').trim();
  if (!/^komari-[0-9]{8}-[0-9a-z]+$/.test(toi)) {
    return _kotae({ ok: false, riyu: '答える相手がありません' });
  }
  if (!_md_aru('src/komari', toi)) {
    return _kotae({ ok: false, riyu: 'そのお悩みは、もう残っていません' });
  }
  if (!_kazoeru()) return _kotae({ ok: false, riyu: '今日はもう受けとれません' });

  /* 添えられた写真とPDF（2026-09-24 依頼）。実践と**同じ置き場**に入れます
     （src/bansho/<slug>/ と src/shiryo/<slug>/）。同じ場所にすると、Actions の
     「JPEGをWebPにする」「PDFを画像にする」が、何も足さずにそのまま効きます。
     ★順番は なおすときと同じです。**先に ぜんぶ検めます**。
       途中で断ると、置きかけのフォルダだけが残るためです。 */
  var shashin = (d.e || []).slice(0, MAI_MAX);
  var pdfs    = (d.p || []).slice(0, 1);
  var slug = _slug('kotae');
  var uri = [];
  for (var i = 0; i < shashin.length; i++) {
    var b = _dataURI(shashin[i]);
    if (!b) return _kotae({ ok: false, riyu: '写真の形が読めません' });
    var shippo = _shippo(b);
    if (!shippo) {
      return _kotae({ ok: false, riyu: 'この形の写真は受けとれません（JPEG・PNG・WebPだけ）' });
    }
    if (b.getBytes().length > KB_MAX * 1024) {
      return _kotae({ ok: false, riyu: '写真が大きすぎます（1枚 ' + KB_MAX + 'KBまで）' });
    }
    uri.push({ na: ('0' + (i + 1)).slice(-2) + shippo, b: b,
               b64: Utilities.base64Encode(b.getBytes()) });
  }
  var pdf = null, pdfB = null;
  if (pdfs.length) {
    var pb = _dataURI_pdf(pdfs[0]);
    if (!pb) return _kotae({ ok: false, riyu: 'PDFの形が読めません' });
    if (pb.getBytes().length > PDF_MB_MAX * 1024 * 1024) {
      return _kotae({ ok: false, riyu: 'PDFが大きすぎます（' + PDF_MB_MAX + 'MBまで）' });
    }
    pdf = Utilities.base64Encode(pb.getBytes());
    pdfB = pb;
  }
  /* 手もとの控え（Drive）。ここから先は、もう断りません。 */
  if (uri.length || pdfB) {
    var folder = _folder(slug);
    for (var i2 = 0; i2 < uri.length; i2++) {
      folder.createFile(uri[i2].b.setName(uri[i2].na));
    }
    if (pdfB) folder.createFile(pdfB.setName('shiryo.pdf'));
  }

  var nose = { ok: false, riyu: '' };
  try {
    /* 絵が先。.md が先だと、絵の揃う前に組み立てが走ります */
    for (var j = 0; j < uri.length; j++) {
      _github('src/bansho/' + slug + '/' + uri[j].na, uri[j].b64,
              '答えの写真を1枚のせる（' + slug + '）');
    }
    if (pdf) {
      _github('src/shiryo/' + slug + '/shiryo.pdf', pdf,
              '答えの資料を1つのせる（' + slug + '）');
    }
    _github('src/kotae/' + _kyou() + '_' + slug + '.md',
            Utilities.base64Encode(_md_kotae(d, m, toi, uri.length ? slug : '',
                                             pdf ? slug : ''), Utilities.Charset.UTF_8),
            'お悩みに答えを1つのせる（' + slug + '）');
    nose.ok = true;
  } catch (err) {
    nose.riyu = String(err);
  }
  _shiraseru_kotae(slug, d, m, toi, nose);
  return _kotae({ ok: true, noseta: nose.ok });
}

/* その名前の .md が、いまあるか。答える相手を確かめるのに使います。 */
function _md_aru(doko, slug) {
  var ichiran = _github_miru(doko);
  if (!ichiran) return false;
  for (var i = 0; i < ichiran.length; i++) {
    var na = ichiran[i].name || '';
    if (na.slice(-3) === '.md' && na.indexOf('_' + slug + '.') >= 0) return true;
  }
  return false;
}

function _md_kotae(d, m, toi, bansho, shiryo) {
  return [
    '---',
    'share: true',
    'date: ' + _kyou(),
    /* どのお悩みへの答えか。build.py はこれで札の中に入れます */
    'toi: ' + toi,
    /* 添えられた写真・資料の置き場（実践と同じ名前の欄・同じフォルダ） */
    bansho ? 'bansho: ' + bansho : null,
    shiryo ? 'shiryo: ' + shiryo : null,
    /* 送った人の合いことばのハッシュ。消すときの関門になります（→ doGet） */
    'nushi: ' + _nushi_arau(d.nushi),
    /* 名前は任意。印が入っているときだけ出します（困りごとと同じ） */
    (d.ko && String(d.na || '').trim()) ? 'by: ' + _by(d) : null,
    '---',
    '',
    m
  ].filter(function (x) { return x !== null; }).join('\n');
}

function _shiraseru_kotae(slug, d, m, toi, nose) {
  var url = _webapp();
  var honbun =
    (nose.ok ? 'お悩みに答えが1つとどき、そのまま載せました。数分でページに出ます。\n'
             : 'お悩みに答えが1つとどきましたが、載せられませんでした。\n' +
               '　理由：' + (nose.riyu || '（不明）') + '\n') +
    '\n' +
    '　答えた先：' + toi + '\n' +
    '　お名前　：' + (d.na || '（名乗られていません）')
      + (String(d.na || '').trim()
           ? (d.ko ? '　← サイトにも出しています' : '　← サイトには出していません')
           : '') + '\n' +
    '　所属　　：' + (d.sh || '（なし）') + '\n\n' +
    '＜中身＞\n' + m + '\n\n' +
    '★ 学校名・子どもの名前・同僚の名前が入っていたら、いますぐ下から消してください。\n\n' +
    (url ? 'すぐ消す：' + url + '?v=' + slug + '&k=' + _kanri_key() + '\n\n' +
           '（公開ページからは消えます。GitHubの履歴には残ります）\n'
         : '（WEBAPP_URL が空なので、消すところを出せていません）');

  var mail = _mail();
  if (mail) MailApp.sendEmail(mail, '【TOKKATSU広場】お悩みに答えがとどきました', honbun);
}

/* 札に出す短い言葉。本文の1行目を、文の切れ目で切ります。
   ★これは「たたき台」です。長すぎたり、個別すぎたりしたら、
     あとから .md の title: を手で直してください。 */
function _mijikaku(hon, n) {
  n = n || 26;
  var gyo = String(hon).split('\n')[0].replace(/^[#\-・\s　]+/, '').trim();
  var ku = ['。', '？', '?', '！', '!'];
  for (var i = 0; i < ku.length; i++) {
    var j = gyo.indexOf(ku[i]);
    if (j > 0 && j <= n) return gyo.slice(0, j);
  }
  return gyo.length <= n ? gyo : gyo.slice(0, n) + '…';
}

function _md_komari(d, m) {
  return [
    '---',
    'share: true',
    'date: ' + _kyou(),
    /* 送った人の合いことばのハッシュ。消すときの関門になります（→ doGet） */
    'nushi: ' + _nushi_arau(d.nushi),
    /* 議題名があれば、それが札の言葉。無ければ本文の1行目から作ります
       （2026-09-22。実践と同じ項目にしたので、同じものが題になります） */
    'title: ' + (_arau(d.t) || _mijikaku(m)),
    'grade: ' + (_arau(d.g) || '学年なし'),
    /* 内容は送り手が選びます（実践と同じ6つ）。
       カードは4つなので、学級活動(1)(2)(3) は gakkyu にまとめます。 */
    'naiyo: ' + _naiyo(d.n)[0],
    'scene: ' + _naiyo(d.n)[1],
    /* saki は、あとから人が足す欄です（いまは空）。
         saki: 2 … 押せる札になり、学習過程の②が開きます
                   ＝ この悩みに答えが付いた、という印 */
    'saki: ',
    /* 提供（2026-09-22）。名前は任意で、**印が入っているときだけ**出します。
       印が無ければ行ごと出しません（「提供：名無し」も出しません）。
       困りごとは打ち明けごとなので、名乗らないほうが既定です。 */
    (d.ko && String(d.na || '').trim()) ? 'by: ' + _by(d) : null,
    '---',
    '',
    m
  ].filter(function (x) { return x !== null; }).join('\n');
}

function _shiraseru_komari(slug, d, m, nose) {
  var url = _webapp();
  var honbun =
    (nose.ok ? '困りごとが1件とどき、そのまま載せました。数分でページに出ます。\n'
             : '困りごとが1件とどきましたが、載せられませんでした。\n' +
               '　理由：' + (nose.riyu || '（不明）') + '\n') +
    '\n' +
    '　内容：' + _naiyo(d.n)[1] + '\n' +
    '　学年：' + (d.g || '（なし）') + '\n' +
    /* ★お名前は、サイトに出ていなくても ここには必ず出します。
       「出さない」を選んだ人の名前も、管理人には届いている、という約束です。 */
    '　お名前：' + (d.na || '（名乗られていません）')
      + (String(d.na || '').trim()
           ? (d.ko ? '　← サイトにも出しています' : '　← サイトには出していません')
           : '') + '\n' +
    '　所属　：' + (d.sh || '（なし）') + '\n\n' +
    '＜中身＞\n' + m + '\n\n' +
    '★ 学校名・子どもの名前・同僚の名前が入っていたら、いますぐ下から消してください。\n\n' +
    (url ? 'すぐ消す：' + url + '?v=' + slug + '&k=' + _kanri_key() + '\n\n' +
           '（公開ページからは消えます。GitHubの履歴には残ります）\n'
         : '（WEBAPP_URL が空なので、消すところを出せていません）');

  var mail = _mail();
  if (mail) MailApp.sendEmail(mail, '【TOKKATSU広場】困りごとが1件とどきました', honbun);
}


/* ══ 1の2の2. 見られた数（2026-09-22 依頼）══════════════════
   「どの画面がいちばん使われているか」を、管理画面で見るためのものです。

   ★残すのは **ページの名前と 日づけ だけ** です。
     受けとらない／残さないもの … IPアドレス、ブラウザや端末の種類、
     どこから来たか（リファラ）、Cookie、端末の番号。
     ★同じ人が2回ひらいても、別々に数えます。
       だから「何人が来たか」は、この仕組みでは **永久に分かりません**。
       分かるのは「何回ひらかれたか」だけです。

   ★これは、このサイトで「開いただけで外へ出る」ただ1つの通信です。
     2026-09-22 までは1つもありませんでした。入れたのは管理人の判断です。

   ★管理画面（kanri.html）は数えません。管理人自身の動きだからです。

   ★1日ぶんを1つの覚え書き（miru_yyyyMMdd）にまとめます。
     日づけごとに1行なので、1年ぶんでも数十KBにしかなりません。       */

/* 数える画面。**帯に出ているものと同じ並び**にしてあります（2026-09-23）。
   ここと src/hiroba.html の正規表現は、いつも同じ顔ぶれにしてください。 */
var MIRU_PAGE = { index:1, okuru:1, bansho:1, atsumaru:1, komari:1,
                  manabu:1, shiru:1, news:1 };
var MIRU_HI_MAX = 120;      // 何日ぶん残すか（これより古い日は、読むときに消します）

function _miru(d) {
  var p = String(d.p || '').replace(/[^a-z]/g, '').slice(0, 16);
  if (!MIRU_PAGE[p]) return _kotae({ ok: true });     // 知らない名前は、数えません
  var lock = LockService.getScriptLock();
  /* 混み合っているときは、待たずに捨てます。
     数がすこし減るより、送った人を待たせないほうが大事なためです。 */
  try { lock.waitLock(3000); } catch (e) { return _kotae({ ok: true }); }
  try {
    var key = 'miru_' + Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyyMMdd');
    var hi;
    try { hi = JSON.parse(P.getProperty(key) || '{}') || {}; } catch (e) { hi = {}; }
    hi[p] = (hi[p] || 0) + 1;
    P.setProperty(key, JSON.stringify(hi));
  } finally {
    lock.releaseLock();
  }
  /* 「やってみたい」の数も、いっしょに返します（2026-09-23）。
     サイトは固定のページなので、数は開いたときに入れるしかありません。
     ★ここで返すことで、**通信が2回にならずに済みます**。
       どうせ1回投げているのだから、その返事に のせます。 */
  return _kotae({ ok: true, yaritai: _yaritai_yomu() });
}

/* ══ 1の2の4. やってみたい（2026-09-23 依頼）════════════════════
   届いた実践に「うちでもやってみたい」を返せるようにするものです。

   ★残すのは **実践の slug と、その回数だけ**。
     誰が押したかは、受けとりませんし、残しません。
     同じ端末から2回押せないようにしているのは、サイト側（localStorage）
     です。だから厳密な人数ではありません。**のべの回数**です。
   ★1つの覚え書き（yaritai）に、まとめて入れます。
     1件30字ほどなので、300件ぶんまでは 9KB の上限に当たりません。       */

function _yaritai_yomu() {
  try { return JSON.parse(P.getProperty('yaritai') || '{}') || {}; }
  catch (e) { return {}; }
}

function _yaritai(d) {
  var slug = String(d.v || '').trim();
  if (!/^bansho-[0-9]{8}-[0-9a-z]+$/.test(slug)) return _kotae({ ok: false });
  var lock = LockService.getScriptLock();
  try { lock.waitLock(5000); } catch (e) { return _kotae({ ok: false }); }
  try {
    var y = _yaritai_yomu();
    y[slug] = (y[slug] || 0) + 1;
    var moji = JSON.stringify(y);
    if (moji.length > 8500) return _kotae({ ok: false });   // 覚え書きの上限の手前
    P.setProperty('yaritai', moji);
    return _kotae({ ok: true, n: y[slug] });
  } finally {
    lock.releaseLock();
  }
}

/* 管理画面へ返す。ここでいちど、古い日を捨てます（掃除の場所はここ1か所）。 */
function _kanri_miru(d) {
  var nonce = String(d.nonce || '').replace(/[^0-9a-z_-]/gi, '').slice(0, 80);
  var kotae = { source: 'tokkatsu-kanri', action: 'miru', ok: false,
                nonce: nonce, riyu: '' };
  if (String(d.key || '').trim() !== _kanri_key()) {
    kotae.riyu = '合いことばがちがいます';
    return _kanri_mado(kotae);
  }
  /* 2026-09-23 依頼「数字をリセットしていいや」。
     合いことばは ここ（受け口）の中にしかないので、管理人が次に1回
     よみこんだ そのときに、いちどだけ 0 に戻します。
     戻したら MIRU_RESET に日づけを残すので、二度目はありません。
     そのあとは、管理画面の［数を0に戻す］から いつでもできます。 */
  if (!P.getProperty('MIRU_RESET')) {
    var mae = P.getProperties();
    for (var mk in mae) { if (mk.slice(0, 5) === 'miru_') P.deleteProperty(mk); }
    P.setProperty('MIRU_RESET',
                  Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyyMMdd'));
  }
  var subete = P.getProperties();
  var furui = new Date();
  furui.setDate(furui.getDate() - MIRU_HI_MAX);
  var kagiri = Utilities.formatDate(furui, 'Asia/Tokyo', 'yyyyMMdd');
  var hi = [];
  for (var k in subete) {
    if (k.slice(0, 5) !== 'miru_') continue;
    var ymd = k.slice(5);
    if (ymd < kagiri) { P.deleteProperty(k); continue; }   // 掃除
    var p;
    try { p = JSON.parse(subete[k]) || {}; } catch (e) { continue; }
    hi.push({ d: ymd, p: p });
  }
  hi.sort(function (a, b) { return a.d < b.d ? 1 : (a.d > b.d ? -1 : 0); });  // 新しい順
  kotae.ok = true;
  kotae.hi = hi;
  kotae.na = Object.keys(MIRU_PAGE);
  return _kanri_mado(kotae);
}


/* 数を ぜんぶ 0 に戻す（2026-09-23 依頼）。
   ★消すのは miru_yyyyMMdd の覚え書きだけです。実践・困りごと・研究日程・
     メモ・合いことばには 指1本ふれません。
   ★戻せません。消えたら、その日より前の回数は 二度と出ません。       */
function _kanri_miru_kesu(d) {
  var nonce = String(d.nonce || '').replace(/[^0-9a-z_-]/gi, '').slice(0, 80);
  var kotae = { source: 'tokkatsu-kanri', action: 'miru-kesu', ok: false,
                nonce: nonce, riyu: '', n: 0 };
  if (String(d.key || '').trim() !== _kanri_key()) {
    kotae.riyu = '合いことばがちがいます';
    return _kanri_mado(kotae);
  }
  var lock = LockService.getScriptLock();
  try { lock.waitLock(5000); } catch (e) {
    kotae.riyu = '混み合っています。少し待ってから、もう一度。';
    return _kanri_mado(kotae);
  }
  try {
    var subete = P.getProperties();
    for (var k in subete) {
      if (k.slice(0, 5) !== 'miru_') continue;
      P.deleteProperty(k);
      kotae.n++;
    }
    kotae.ok = true;
  } finally {
    lock.releaseLock();
  }
  return _kanri_mado(kotae);
}


/* ══ 1の2の3. 管理人だけのメモ（2026-09-22 依頼）════════════
   届いた1件ごとに、管理人が自分の読み取りを書きとめておく所です。

   ★**どこにも公開しません。**
     ・公開ページ（bansho.html など）には1文字も出ません
     ・GitHub にも置きません。ここ（スクリプトの覚え書き）にだけ残ります
     ・送ってくださった先生にも見えません
   ★だから、実践そのものを直すのではなく、**自分の言葉を溜める**ための欄です。

   ★入れ物の大きさ … 覚え書きは ぜんぶで 500KB までです。閲覧数の分と
     取り合いになるので、1件 MEMO_MOJI_MAX 字までにし、合計が近づいたら
     書くのを断ります（黙って消えるより、断られたほうがいいためです）。   */

var MEMO_MOJI_MAX = 800;        // メモ1件の字数
var MEMO_ZEN_MAX  = 380000;     // 覚え書き全体が、これを超えたら断る（500KBの手前）
var MEMO_SLUG = /^(bansho|komari|nittei)-[0-9]{8}-[0-9a-z]+$/;

function _kanri_memo_yomu(d) {
  var nonce = String(d.nonce || '').replace(/[^0-9a-z_-]/gi, '').slice(0, 80);
  var kotae = { source: 'tokkatsu-kanri', action: 'memo-yomu', ok: false,
                nonce: nonce, riyu: '' };
  if (String(d.key || '').trim() !== _kanri_key()) {
    kotae.riyu = '合いことばがちがいます';
    return _kanri_mado(kotae);
  }
  var subete = P.getProperties();
  var memo = {};
  for (var k in subete) {
    if (k.slice(0, 5) === 'memo_') memo[k.slice(5)] = subete[k];
  }
  kotae.ok = true;
  kotae.memo = memo;
  return _kanri_mado(kotae);
}

function _kanri_memo_kaku(d) {
  var nonce = String(d.nonce || '').replace(/[^0-9a-z_-]/gi, '').slice(0, 80);
  var slug = String(d.v || '').trim();
  var kotae = { source: 'tokkatsu-kanri', action: 'memo-kaku', ok: false,
                nonce: nonce, v: slug, riyu: '' };
  if (String(d.key || '').trim() !== _kanri_key()) {
    kotae.riyu = '合いことばがちがいます';
    return _kanri_mado(kotae);
  }
  if (!MEMO_SLUG.test(slug)) {
    kotae.riyu = '行き先がありません';
    return _kanri_mado(kotae);
  }
  var m = String(d.m || '').slice(0, MEMO_MOJI_MAX).trim();
  var lock = LockService.getScriptLock();
  try { lock.waitLock(10000); } catch (e) {
    kotae.riyu = '混み合っています。少し待ってから もう一度。';
    return _kanri_mado(kotae);
  }
  try {
    if (!m) {
      P.deleteProperty('memo_' + slug);      // 空にしたら、消す
    } else {
      /* 入れ物の残りを見ます。書いてから溢れると、**黙って消えます**。
         それがいちばん困るので、書くまえに断ります。 */
      var subete = P.getProperties(), zen = 0;
      for (var k in subete) zen += k.length + String(subete[k]).length;
      var ima = String(subete['memo_' + slug] || '').length;
      if (zen - ima + m.length > MEMO_ZEN_MAX) {
        kotae.riyu = '覚え書きがいっぱいです。古いメモを消してから もう一度。';
        return _kanri_mado(kotae);
      }
      P.setProperty('memo_' + slug, m);
    }
  } finally {
    lock.releaseLock();
  }
  kotae.ok = true;
  kotae.m = m;
  return _kanri_mado(kotae);
}


/* ══ 1の3. 研究日程 ═══════════════════════════════════════
   2026-09-22。これまで研究日程は src/app.js の EVENTS だけでした。
   手で書くしかないので、知っている人がいても、その人からは載りません。
   ここで受けて src/nittei/<日付>_<slug>.md に置くと、build.py の
   load_nittei() が こよみに合流させます。
   ★誰の目も通りません。板書・困りごとと同じです。
     知らせの［すぐ消す］で1押しで下ろせます。 */

var NITTEI_MOJI_MIN = 10;     // 「何をやる会か」の下限（サイト側と同じ線）
var NITTEI_MOJI_MAX = 300;

function _nittei(d) {
  var na = _arau(d.na);
  var m  = _arau_hon(d.m);
  if (!na)                       return _kotae({ ok: false, riyu: '会の名前がありません' });
  if (!_hiduke(d.h1))            return _kotae({ ok: false, riyu: '日がありません' });
  if (m.length < NITTEI_MOJI_MIN) return _kotae({ ok: false, riyu: '中身が短すぎます' });
  if (!_kazoeru())               return _kotae({ ok: false, riyu: '今日はもう受けとれません' });

  var slug = _slug('nittei');
  var nose = { ok: false, riyu: '' };
  try {
    _github('src/nittei/' + _kyou() + '_' + slug + '.md',
            Utilities.base64Encode(_md_nittei(d, na, m), Utilities.Charset.UTF_8),
            '研究日程を1件のせる（' + slug + '）');
    nose.ok = true;
  } catch (err) {
    nose.riyu = String(err);
  }
  _shiraseru_nittei(slug, d, na, m, nose);
  return _kotae({ ok: true, noseta: nose.ok });
}

/* 2026-10-09 の形だけ通します。ちがえば空を返します
   （front matter に変な字が入ると、その1件が こよみから落ちるだけで
     サイトは止まりません。build.py の load_nittei() が飛ばします）。 */
function _hiduke(s) {
  var t = String(s || '').trim();
  return /^\d{4}-\d{2}-\d{2}$/.test(t) ? t : '';
}

/* 外へ出る道は http(s) だけ。javascript: などは入れさせません。 */
function _url(s) {
  var t = _arau(s);
  return /^https?:\/\//.test(t) ? t : '';
}

function _md_nittei(d, na, m) {
  var hi = [_hiduke(d.h1), _hiduke(d.h2)].filter(String).join('|');
  return [
    '---',
    'share: true',
    'date: ' + _kyou(),
    'title: ' + na,
    'org: ' + _arau(d.sy),
    'days: ' + hi,
    'deadline: ' + _hiduke(d.sh),
    'venue: ' + _arau(d.ba),
    'place: ' + _arau(d.to),
    'apply: ' + _arau(d.mo),
    'url: ' + _url(d.u),
    /* 名前は、出してよいと押した人だけ出ます。
       押していなければ空にして、サイト側が「送ってくださった先生」と出します。 */
    'by: ' + (Number(d.ko) === 1 ? _arau(d.by) : ''),
    'nushi: ' + _nushi_arau(d.nushi),
    '---',
    '',
    m.slice(0, NITTEI_MOJI_MAX)
  ].join('\n');
}

/* 知らせのメール。★ここに「LINEに貼る文」も入れます（2026-09-22）。
   オープンチャットには外から書きこめないので（ボットは入れません。
   LINE Notify も2025年3月で終わりました）、
   **文はこちらで作っておいて、押すだけ**にします。
   スマホでこのメールを開いて、下のリンクを1回押せば、
   LINEが開いて送り先をえらぶところまで行きます。 */
function _shiraseru_nittei(slug, d, na, m, nose) {
  var url = _webapp();
  var bun = _line_bun(d, na, m);
  var honbun =
    (nose.ok ? '研究日程が1件とどき、そのまま載せました。数分でこよみに出ます。\n'
             : '研究日程が1件とどきましたが、載せられませんでした。\n' +
               '　理由：' + (nose.riyu || '（不明）') + '\n') +
    '\n' +
    '　会の名前：' + na + '\n' +
    '　いつ　　：' + _hiduke(d.h1) + (_hiduke(d.h2) ? '〜' + _hiduke(d.h2) : '') + '\n' +
    '　〆切　　：' + (_hiduke(d.sh) || '（なし）') + '\n' +
    '　会場　　：' + (_arau(d.ba) || '（なし）') + '　' + (_arau(d.to) || '') + '\n' +
    '　主催　　：' + (_arau(d.sy) || '（なし）') + '\n' +
    '　案内　　：' + (_url(d.u) || '（なし）') + '\n' +
    '　送り主　：' + (_arau(d.by) || '（名前なし）') +
        (Number(d.ko) === 1 ? '（出してよい）' : '（出しません）') + '\n\n' +
    '＜中身＞\n' + m + '\n\n' +
    '★ 主催の案内と、日づけを見くらべてください。ちがっていたら、下から消せます。\n\n' +
    '───────────────────────────\n' +
    '■ LINEに知らせる（スマホでこのメールを開いて、下を1回押す）\n\n' +
    'https://line.me/R/share?text=' + encodeURIComponent(bun) + '\n\n' +
    '　押すとLINEが開いて、送り先をえらぶだけです。\n' +
    '　「みんなの特活ひろば」をえらんでください。\n' +
    '　（パソコンのLINEでは開きません。下の文をコピーして貼ってください）\n\n' +
    '＜貼る文＞\n' + bun + '\n' +
    '───────────────────────────\n\n' +
    (url ? 'すぐ消す：' + url + '?v=' + slug + '&k=' + _kanri_key() + '\n\n' +
           '（公開ページからは消えます。GitHubの履歴には残ります）\n'
         : '（WEBAPP_URL が空なので、消すところを出せていません）');

  var mail = _mail();
  if (mail) MailApp.sendEmail(mail, '【TOKKATSU広場】研究日程が1件とどきました', honbun);
}

/* LINEに貼る文。サイト側（src/hiroba.html の ntBun）と同じ形にそろえています。
   どちらを直すときも、もう一方も直してください。 */
function _line_bun(d, na, m) {
  var gyo = ['【TOKKATSU広場】研究日程を更新しました！', ''];
  gyo.push(_hi_ja(_hiduke(d.h1))
           + (_hiduke(d.h2) ? '〜' + _hi_ja(_hiduke(d.h2)) : '') + '　' + na);
  var ba = [_arau(d.ba), _arau(d.to)].filter(String).join('　');
  if (ba) gyo.push('会場：' + ba);
  if (_hiduke(d.sh)) gyo.push('申込〆切：' + _hi_ja(_hiduke(d.sh)));
  gyo.push(m);
  if (_url(d.u)) gyo.push('案内：' + _url(d.u));
  gyo.push('');
  gyo.push('こよみで見てね！');
  gyo.push(SITE_URL + '#ima');
  return gyo.join('\n');
}

var SITE_URL = 'https://yuutennis657-beep.github.io/tokkatsu-hiroba/';
var NITTEI_YOUBI = ['日', '月', '火', '水', '木', '金', '土'];

/* 2026-10-09 → 10月9日（木） */
function _hi_ja(ymd) {
  if (!ymd) return '';
  var a = ymd.split('-');
  var d = new Date(Number(a[0]), Number(a[1]) - 1, Number(a[2]));
  return Number(a[1]) + '月' + Number(a[2]) + '日（' + NITTEI_YOUBI[d.getDay()] + '）';
}


/* サイト側は fetch で投げっぱなしなので、返す中身は使われません。
   それでも、あとで見たときに分かるように返しておきます。 */
function _kotae(o) {
  return ContentService.createTextOutput(JSON.stringify(o))
    .setMimeType(ContentService.MimeType.JSON);
}

/* 名前のしっぽ（拡張子）は、**中身から**決めます。
   ★ずれると2つ困ります。
     ・build.py は しっぽを見て data:image/… を書くので、WebPのバイトに
       「image/jpeg」と札を付けて埋めることになります。
     ・build.py が知らないしっぽ（.gif や .svg）だと、その1枚は数に入らず、
       「src/bansho/<slug>/ に画像がありません」で**ビルドが止まります**。
   だから、知らない形は ここで断ります（置いてから気づくのでは遅い）。 */
var GAZOU_SHIPPO = { 'image/jpeg': '.jpg', 'image/jpg': '.jpg',
                     'image/png': '.png', 'image/webp': '.webp' };

function _shippo(b) {
  return GAZOU_SHIPPO[String(b.getContentType() || '').toLowerCase()] || '';
}

function _dataURI(s) {
  var m = String(s).match(/^data:(image\/[a-z+]+);base64,(.+)$/);
  if (!m) return null;
  return Utilities.newBlob(Utilities.base64Decode(m[2]), m[1]);
}

function _dataURI_pdf(s) {
  var m = String(s).match(/^data:application\/pdf;base64,(.+)$/);
  if (!m) return null;
  return Utilities.newBlob(Utilities.base64Decode(m[1]), 'application/pdf');
}

/* フォルダ名。英小文字・数字・- だけ（build.py の検問に合わせています） */
function _slug(atama) {
  var d = new Date();
  var hi = Utilities.formatDate(d, 'Asia/Tokyo', 'yyyyMMdd');
  var ran = Utilities.getUuid().slice(0, 6);
  return (atama || 'bansho') + '-' + hi + '-' + ran;
}

function _folder(slug) {
  var oya = _p('DRIVE_FOLDER')
    ? DriveApp.getFolderById(_p('DRIVE_FOLDER'))
    : DriveApp.getRootFolder();
  return oya.createFolder(slug);
}


/* 今日は何件めか。上限までなら true、越えたら false。
   数えるあいだは鍵をかけます（同時に届いても二重に数えないため）。 */
function _kazoeru() {
  var kyou = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyyMMdd');
  var lock = LockService.getScriptLock();
  try { lock.waitLock(10000); } catch (e) { return true; }   // 鍵が取れない日は通す
  try {
    var key = 'kazu_' + kyou;
    var n = parseInt(P.getProperty(key) || '0', 10) + 1;
    P.setProperty(key, String(n));
    if (n === HI_MAX + 1) _uwamawatta(kyou, n);   // 知らせるのは、越えた1回だけ
    return n <= HI_MAX;
  } finally {
    lock.releaseLock();
  }
}

function _uwamawatta(kyou, n) {
  var mail = _mail();
  if (!mail) return;
  MailApp.sendEmail(mail, '【TOKKATSU広場】板書の受けとりを、今日はここで止めました',
    kyou + ' に ' + HI_MAX + '件を受けとったので、今日はこれ以上 受けとりません。\n\n' +
    'ふつうの使い方では当たらない数です。いたずらが続いているなら、\n' +
    'Apps Script でデプロイを作り直すと、URLが変わって止まります。\n' +
    '（作り直したら、src/hiroba.html の OKURU_URL も差しかえてください）\n');
}


/* ══ 2. 管理人に知らせる ══════════════════════════════════ */

function _shiraseru(slug, d, folder, nose) {
  var url = _webapp();

  var honbun =
    (nose && nose.ok
      ? '板書が1件とどき、そのまま載せました。数分で板書のページに出ます。\n'
      : '板書が1件とどきましたが、載せられませんでした。写真はDriveに残っています。\n' +
        '　理由：' + ((nose && nose.riyu) || '（不明）') + '\n') +
    '\n' +
    '　内容　　：' + _naiyo(d.n)[1] + '（カードは「'
      + { gakkyu: '学級活動', gyoji: '学校行事',
          jidokai: '児童会活動', club: 'クラブ活動' }[_naiyo(d.n)[0]] + '」へ）\n' +
    '　議題名　：' + (d.t || '（なし）') + '\n' +
    '　学年　　：' + (d.g || '（なし）') + '\n' +
    /* ★お名前は、サイトに出ていなくても ここには必ず出します。
       「出さない」を選んだ人の名前も、管理人には届いている、という約束です。 */
    '　お名前　：' + (d.na || '（なし）')
      + (d.ko ? '　← サイトにも出しています' : '　← サイトには出していません') + '\n' +
    '　所属　　：' + (d.sh || '（なし）') + '\n' +
    '　枚数　　：' + (d.e || []).length + '枚' +
      ((d.p || []).length ? '／PDF1つ' : '') + '\n' +
    '　置き場　：' + folder.getUrl() + '\n\n' +
    '＜概要・ポイント＞\n' +
    (d.m ? d.m : '（書かれていません）') + '\n\n' +
    '★ 子どもの顔・名前・学校名が写っていたら、いますぐ下から消してください。\n\n' +
    (url
      ? 'すぐ消す：' + url + '?v=' + slug + '&k=' + _kanri_key() + '\n\n' +
        '（公開ページからは消えます。GitHubの履歴には残ります）\n'
      : '（WEBAPP_URL が空なので、消すところを出せていません）');

  var mail = _mail();
  if (mail) {
    MailApp.sendEmail(mail, '【TOKKATSU広場】板書が1件とどきました', honbun);
    return;
  }
  /* アドレスが取れないときは、黙って消さずに、写真のとなりに置き手紙を残します。
     ここが空のまま気づかないと、送ってくれた板書がどこにも出ません。 */
  folder.createFile('★メールを出せませんでした.txt',
    honbun + '\n\n' +
    '───────────────\n' +
    'ADMIN_MAIL が空です。Apps Script のエディタで saisho_ni_ichido() を\n' +
    '1回だけ走らせてください。次からメールが届きます。\n',
    MimeType.PLAIN_TEXT);
}


/* ══ 3. 載せる／消す ══════════════════════════════════════ */

/* 写真と .md を GitHub に置きます。数分で板書のページに出ます。 */
function _noseru(slug, n) {
  for (var i = 0; i < n.uri.length; i++) {
    _github('src/bansho/' + slug + '/' + n.uri[i].na, n.uri[i].b64,
            '板書を1枚ふやす（' + slug + '）');
  }
  /* PDFは src/shiryo/<slug>/ に置きます。Actions がここを見て画像に変え、
     元のPDFは消します（.github/workflows/build.yml の「送られたPDFを画像にする」）。 */
  if (n.pdf) {
    _github('src/shiryo/' + slug + '/shiryo.pdf', n.pdf,
            '資料を1つふやす（' + slug + '）');
  }
  if (MD_MO_TSUKURU) {
    _github('src/jissen/' + _kyou() + '_' + slug + '.md',
            Utilities.base64Encode(_md(slug, n), Utilities.Charset.UTF_8),
            '板書の1件を載せる（' + slug + '）');
  }
}

/* 知らせの［すぐ消す］。GitHub から、その1件ぶんを全部消します。
   ★ 公開ページからは消えますが、**GitHub の履歴には残ります**。
     履歴ごと消すには、手もとで git の作り直しが要ります。 */
function doGet(e) {
  var slug = (e.parameter.v || '').trim();
  var key  = String(e.parameter.k || '').trim();
  /* 2026-09-24：kotae と todoita を足しました。
       ★kotae … 答えの知らせメールに［すぐ消す］は出ていたのに、
         ここで弾かれて「行き先がありません」になっていました（積み残し）。
       ★todoita … 届いた学級会グッズです。 */
  if (!/^(bansho|komari|nittei|kotae|todoita)-[0-9]{8}-[0-9a-z]+$/.test(slug)) return _html('行き先がありません');

  /* ★ここが無いと、URLを知った人が誰でも消せます（2026-09-22 夜に入れました）。
       通るのは次の2つだけです。
         ・管理人のあいことば
         ・その1件を送った人の合いことば（ハッシュが .md のものと合う） */
  var kanri = (key && key === _kanri_key());
  if (!kanri) {
    var nushi = _nushi_yomu(slug);
    if (!nushi) {
      return _html('この1件には合いことばが付いていません。'
                 + '<br><br>管理人のリンクからなら消せます。');
    }
    if (!key || _hash(key) !== nushi) {
      return _html('合いことばが ちがいます。<br><br>'
                 + '送ったときと<b>同じ端末・同じブラウザ</b>から消してください。'
                 + '（合いことばは、その中にだけ残っています）');
    }
  }

  /* 押すまでは、何もしません。メールを読む道具がリンクを先に開いてしまっても、
     ここで止まります（2026-09-22 夜。前は x=1 を最初から付けていました）。 */
  if (e.parameter.x !== '1') {
    var mata = ScriptApp.getService().getUrl()
             + '?v=' + encodeURIComponent(slug) + '&k=' + encodeURIComponent(key) + '&x=1';
    return _html('この1件を消しますか。<br><small>' + slug + '</small><br><br>'
               + '<a href="' + mata + '" style="display:inline-block;padding:14px 26px;'
               + 'background:#D2552A;color:#fff;border-radius:999px;text-decoration:none;'
               + 'font-weight:700">消す</a>'
               + '<br><br><small>公開ページからは消えます。GitHubの履歴には残ります。</small>');
  }
  try {
    var keshita = _slug_kesu(slug);
  } catch (err) {
    return _html('消せませんでした：' + String(err).slice(0, 200) +
                 '<br><br>手で消すなら GitHub の src/ の中です（' + slug + '）。');
  }
  if (!keshita) return _html('もう残っていませんでした。');
  return _html('消しました（' + keshita + '件）。数分でページから消えます。<br><br>' +
               '<small>GitHub の履歴には残ります。Driveの写真も残っています。</small>');
}

/* ══ 4. なおす（2026-09-22 夜 依頼）══════════════════════════
   送った本人（合いことばが合う人）と管理人だけが、あとから直せます。

   直せるもの … 題・推しポイント・実践内容・学年・内容・写真／PDF
   ★写真を送りなおしたときは、**古い写真を先に消します**。
     消さずに足すと、1枚めが古いまま残って、直したつもりが直りません。
   ★写真を送ってこなければ、写真はそのままです（字だけ直せます）。
   ★front matter は作りなおしますが、**届いた日と時こく（date・todoita）
     と 合いことば（nushi）は、はじめのものを引きつぎます**。
     直すたびに新しくなると、並びが変わって別ものに見えるためです。      */
function _naosu(d, kanriMado) {
  function kotae(x) {
    if (!kanriMado) return _kotae(x);
    return _kanri_mado({ source: 'tokkatsu-kanri', action: 'naosu',
                         ok: !!x.ok, riyu: x.riyu || '',
                         nonce: String(d.nonce || '').replace(/[^0-9a-z_-]/gi, '').slice(0, 80) });
  }
  var slug = String(d.v || '').trim();
  if (!/^bansho-[0-9]{8}-[0-9a-z]+$/.test(slug)) {
    return kotae({ ok: false, riyu: '行き先がありません' });
  }
  var key = String(d.key || '').trim();
  var moto = _md_yomu(slug);
  if (!moto.hon) return kotae({ ok: false, riyu: 'もう残っていません' });
  var kanri = !!(key && key === _kanri_key());
  if (!kanri) {
    if (!moto.nushi)  return kotae({ ok: false, riyu: 'この1件には合いことばが付いていません' });
    if (!key || _hash(key) !== moto.nushi) {
      return kotae({ ok: false, riyu: '合いことばが ちがいます' });
    }
  }
  if (!_kazoeru()) return kotae({ ok: false, riyu: '今日はもう受けとれません' });

  var shashin = (d.e || []).slice(0, MAI_MAX);
  var pdfs    = (d.p || []).slice(0, 1);
  var folder  = _folder(slug);
  var uri = [];
  /* ══ 順番がいのちです（2026-09-23 夜）════════════════════
     前は「①GitHubの古い写真を消す → ②1枚ずつ検める」でした。
     2枚めが読めない／大きすぎると、そこで return します。すると
     src/bansho/<slug>/ は**空のまま**なのに、.md は bansho: を
     指したままになり、build.py の検問で止まります。
     ＝ その1件のせいで、サイト全体が更新できなくなります。
     しかも no-cors なので、送った人の画面には「送りました」と出たまま。
     だから いまは この順です。
       ① ぜんぶ検める（ここで転んでも、まだ1枚も消していない）
       ② 手もとの控え（Drive）
       ③ 新しいぶんを GitHub に置く（同じ名前は上書き）
       ④ 余ったぶんだけを消す（しっぽ違いも ここで片づく）
       ⑤ 最後に .md
     どこで転んでも、src/bansho/ が空になりません。                */
  for (var i = 0; i < shashin.length; i++) {
    var b = _dataURI(shashin[i]);
    if (!b) return kotae({ ok: false, riyu: '写真の形が読めません' });
    var shippo = _shippo(b);
    if (!shippo) {
      return kotae({ ok: false, riyu: 'この形の写真は受けとれません（JPEG・PNG・WebPだけ）' });
    }
    if (b.getBytes().length > KB_MAX * 1024) {
      return kotae({ ok: false, riyu: '写真が大きすぎます（1枚 ' + KB_MAX + 'KBまで）' });
    }
    uri.push({ na: ('0' + (i + 1)).slice(-2) + shippo, b: b,
               b64: Utilities.base64Encode(b.getBytes()) });
  }
  var pdf = null, pdfB = null;
  if (pdfs.length) {
    var pb = _dataURI_pdf(pdfs[0]);
    if (!pb) return kotae({ ok: false, riyu: 'PDFの形が読めません' });
    if (pb.getBytes().length > PDF_MB_MAX * 1024 * 1024) {
      return kotae({ ok: false, riyu: 'PDFが大きすぎます（' + PDF_MB_MAX + 'MBまで）' });
    }
    pdf = Utilities.base64Encode(pb.getBytes());
    pdfB = pb;
  }
  /* ② 手もとの控え（Drive）。ここから先は、もう断りません。 */
  for (var i2 = 0; i2 < uri.length; i2++) {
    folder.createFile(uri[i2].b.setName(uri[i2].na));
  }
  if (pdfB) folder.createFile(pdfB.setName('shiryo.pdf'));

  var hon = d.m || '';
  // 推しポイントは40字まで（2026-09-23 依頼）。
  // 画面の入力欄（maxlength="40"）と build.py の OSHI_MOJI_MAX と、同じ数です。
  var oshi = _arau(d.o || '').slice(0, 40);
  if (oshi) hon = '★推しポイント：' + oshi + '\n\n' + hon;
  var n = { uri: uri, pdf: pdf, t: d.t || '', g: d.g || '', m: hon,
            n: d.n || '', na: d.na || '', sh: d.sh || '', ko: !!d.ko,
            nushi: moto.nushi };
  /* 新しい管理画面は、名前・所属・公開の有無をそのまま送る。
     以前は古い by を必ず優先していたため、名前や所属を
     書き換えても更新されなかった。古い公開済み画面だけ互換用に by を引きつぐ。 */
  if (kanri && d.kanri && !d.by_atarashii) n.by_hyoji = _arau(d.by).slice(0, 100);
  /* ③ 新しいぶんを GitHub に置きます。
     ★2026-09-23、ここが丸ごと抜けていました（実際にビルドが止まりました）。
       新しい写真を Drive にしか置いていなかったため、.md が指す
       src/bansho/<slug>/ が空になり、build.py の検問で止まりました。
     ★.md より先に押します。.md が先だと、写真が揃う前に組み立てが走ります。
     ★同じ名前は _github が sha を取って上書きするので、消さずに重ねられます。 */
  /* GitHub が途中で断ることがあります（鍵切れ・向こうの不調）。
     投げっぱなしにすると、管理画面は「保存しています…」のまま止まります。
     どこまで行ったか分からないので、そのとおりに伝えます。 */
  try {
  for (var j = 0; j < uri.length; j++) {
    _github('src/bansho/' + slug + '/' + uri[j].na, uri[j].b64,
            '板書を1枚ふやす（' + slug + '）');
  }
  /* ④ 余ったぶんだけ消します（置いたあとに消す）。
     ★3枚だったものが2枚になったときの 03、しっぽが変わったときの
       01.webp が、ここで片づきます。1枚も置いていないときは、
       何も触りません（写真はそのまま残す、という意味だからです）。 */
  if (uri.length) {
    var nokosu = [];
    for (var k = 0; k < uri.length; k++) nokosu.push(uri[k].na);
    _amari_kesu('src/bansho/' + slug, nokosu, slug);
  }
  if (pdf) {
    _github('src/shiryo/' + slug + '/shiryo.pdf', pdf,
            '資料を1つふやす（' + slug + '）');
    /* 古いページの絵（01.webp …）を落とします。この回の Actions が
       置いたばかりのPDFを絵に変えてから、組み立てが走ります。 */
    _amari_kesu('src/shiryo/' + slug, ['shiryo.pdf'], slug);
  }

  var md = _md(slug, n);
  md = _hikitsugu(md, moto.hon, ['date', 'todoita']);
  if (!uri.length && moto.bansho) md = md.replace(/\n---\n/, '\nbansho: ' + slug + '\n---\n');
  if (!pdf && moto.shiryo)        md = md.replace(/\n---\n/, '\nshiryo: 送ってもらった資料|' + slug + '\n---\n');
  _github('src/jissen/' + moto.michi_na, Utilities.base64Encode(md, Utilities.Charset.UTF_8),
          '実践を1件 なおす（' + slug + '）');
  } catch (err) {
    return kotae({ ok: false, riyu: '途中で止まりました（写真は入れかわっているかもしれません）。'
                                  + 'もう一度ためしてください：' + String(err).slice(0, 120) });
  }
  _shiraseru_naoshita(slug, d, n);
  return kotae({ ok: true });
}

/* 管理画面の開錠結果。返すのは「合った／ちがう」だけで、
   管理キーそのものやハッシュは画面へ戻しません。 */
function _kanri_check(d) {
  var nonce = String(d.nonce || '').replace(/[^0-9a-z_-]/gi, '').slice(0, 80);
  var ok = !!(String(d.key || '').trim() === _kanri_key());
  return _kanri_mado({ source: 'tokkatsu-kanri', action: 'login', ok: ok, nonce: nonce });
}

/* 管理画面からの削除。GETのURLに管理キーを出さず、
   確認画面の「削除する」を押したPOSTだけを受ける。 */
function _kanri_kesu(d) {
  var nonce = String(d.nonce || '').replace(/[^0-9a-z_-]/gi, '').slice(0, 80);
  var slug = String(d.v || '').trim();
  var kotae = { source: 'tokkatsu-kanri', action: 'kesu', ok: false,
                nonce: nonce, v: slug, riyu: '' };
  if (String(d.key || '').trim() !== _kanri_key()) {
    kotae.riyu = '合いことばがちがいます';
    return _kanri_mado(kotae);
  }
  /* 2026-09-22：困りごと・研究日程も、管理画面から下ろせるようにしました。
     _slug_kesu は もともと3つとも扱えます（komari- / nittei- / それ以外）。
     ここの形あわせだけが、実践に絞られていました。 */
  if (!/^(bansho|komari|nittei|kotae|todoita)-[0-9]{8}-[0-9a-z]+$/.test(slug)) {
    kotae.riyu = '行き先がありません';
    return _kanri_mado(kotae);
  }
  try {
    var n = _slug_kesu(slug);
    if (!n) {
      kotae.riyu = 'もう残っていません';
    } else {
      kotae.ok = true;
      kotae.kazu = n;
    }
  } catch (err) {
    kotae.riyu = '削除できませんでした：' + String(err).slice(0, 160);
  }
  return _kanri_mado(kotae);
}

function _kanri_mado(kotae) {
  /* Apps Script の HtmlService は、返したHTMLを Google の内側フレームに
     もう1枚入れる。parent だとそこで止まるので、最上位の管理画面へ戻す。 */
  var payload = JSON.stringify(kotae).replace(/</g, '\\u003c');
  var js = '<!doctype html><meta charset="utf-8"><script>'
    + 'top.postMessage(' + payload + ',"*");<\/script>';
  return HtmlService.createHtmlOutput(js)
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/* もとの .md を読んで、引きつぐものを取り出します */
function _md_yomu(slug) {
  var ichiran = _github_miru('src/jissen');
  if (!ichiran) return {};
  for (var i = 0; i < ichiran.length; i++) {
    var na = ichiran[i].name || '';
    if (na.slice(-3) === '.md' && na.indexOf('_' + slug + '.') >= 0) {
      var hon = _github_yomu(ichiran[i].path);
      var m = hon && hon.match(/^nushi:\s*([0-9a-f]{64})\s*$/m);
      return { michi_na: na, hon: hon, nushi: m ? m[1] : '',
               bansho: /^bansho:\s*\S/m.test(hon || ''),
               shiryo: /^shiryo:\s*\S/m.test(hon || '') };
    }
  }
  return {};
}

/* 新しい front matter の中の、決めた行だけを もとの値に戻します */
function _hikitsugu(atarashii, moto, kagi) {
  for (var i = 0; i < kagi.length; i++) {
    var m = moto.match(new RegExp('^' + kagi[i] + ':.*$', 'm'));
    if (!m) continue;
    if (new RegExp('^' + kagi[i] + ':.*$', 'm').test(atarashii)) {
      atarashii = atarashii.replace(new RegExp('^' + kagi[i] + ':.*$', 'm'), m[0]);
    } else {
      atarashii = atarashii.replace(/\n---\n/, '\n' + m[0] + '\n---\n');
    }
  }
  return atarashii;
}

function _shiraseru_naoshita(slug, d, n) {
  var url = _webapp();
  var mail = _mail();
  if (!mail) return;
  MailApp.sendEmail(mail, '【TOKKATSU広場】実践が1件 なおされました',
    '送った人（または管理人）が、1件をなおしました。数分でページに出ます。\n\n' +
    '　議題名：' + (_arau(d.t) || '（なし）') + '\n' +
    '　学年　：' + (_arau(d.g) || '（なし）') + '\n' +
    '　写真　：' + (n.uri.length ? n.uri.length + '枚に差しかえ' : 'そのまま') + '\n' +
    '　PDF　 ：' + (n.pdf ? '差しかえ' : 'そのまま') + '\n\n' +
    (url ? 'すぐ消す：' + url + '?v=' + slug + '&k=' + _kanri_key() + '\n' : ''));
}


/* その1件の .md から、合いことばのハッシュ（nushi:）を読みます。
   無ければ空。★受け口を貼り直す前に届いたものは、これを持っていません。
   その1件は、管理人のあいことばでしか消せません（それでよい、と決めました）。 */
function _nushi_yomu(slug) {
  var doko = slug.indexOf('komari-') === 0 ? 'src/komari'
           : slug.indexOf('nittei-') === 0 ? 'src/nittei' : 'src/jissen';
  var ichiran = _github_miru(doko);
  if (!ichiran) return '';
  for (var i = 0; i < ichiran.length; i++) {
    var na = ichiran[i].name || '';
    if (na.slice(-3) === '.md' && na.indexOf('_' + slug + '.') >= 0) {
      var hon = _github_yomu(ichiran[i].path);
      var m = hon && hon.match(/^nushi:\s*([0-9a-f]{64})\s*$/m);
      return m ? m[1] : '';
    }
  }
  return '';
}

function _github_yomu(michi) {
  var kotae = UrlFetchApp.fetch(_gh_url(michi) + '?ref=' + _p('GITHUB_BRANCH', 'main'),
    { headers: _gh_atama(), muteHttpExceptions: true });
  if (kotae.getResponseCode() !== 200) return '';
  var j = JSON.parse(kotae.getContentText());
  if (!j || !j.content) return '';
  return Utilities.newBlob(Utilities.base64Decode(j.content.replace(/\n/g, '')))
                  .getDataAsString('UTF-8');
}

function _kesu_folder(michi, slug) {
  var ichiran = _github_miru(michi);
  if (!ichiran || !ichiran.length) return 0;
  var n = 0;
  for (var i = 0; i < ichiran.length; i++) {
    _github_kesu(ichiran[i].path, ichiran[i].sha, '板書を1件消す（' + slug + '）');
    n++;
  }
  return n;
}

/* 新しく置いたもの以外を消す（_naosu の差しかえ用）。
   ★**置いたあとに消す**のが肝です。先に消して途中で転ぶと、
     src/bansho/<slug>/ が空のまま残り、.md は bansho: を指したままなので
     build.py の検問で止まり、その1件のせいで**サイト全体が更新できなく
     なります**（2026-09-23 に実際に起きました）。
   ★しっぽ違い（01.webp → 01.jpg）も、ここで一緒に片づきます。
     名前で残すものを選ぶので、01.webp は「余り」になります。 */
function _amari_kesu(michi, nokosu, slug) {
  var ichiran = _github_miru(michi);
  if (!ichiran || !ichiran.length) return 0;
  var n = 0;
  for (var i = 0; i < ichiran.length; i++) {
    var na = ichiran[i].name || '';
    if (!na || nokosu.indexOf(na) >= 0) continue;
    _github_kesu(ichiran[i].path, ichiran[i].sha, '古いぶんを1つ消す（' + slug + '）');
    n++;
  }
  return n;
}

/* 1件の字・写真・資料をまとめて削除する。
   メールのリンクと管理画面の両方が、この同じ道を使う。 */
function _slug_kesu(slug) {
  var n = 0;
  if (slug.indexOf('komari-') === 0) {
    n += _kesu_md(slug, 'src/komari');
    /* お悩みを消したら、その答えも一緒に消します。残すと、どこにも
       出ない .md が溜まります（build.py は相手のいない答えを飛ばします）。 */
    n += _kotae_kesu(slug);
  } else if (slug.indexOf('kotae-') === 0) {
    /* 答えに添えられた写真・資料も、一緒に落とします */
    n += _kesu_folder('src/bansho/' + slug, slug);
    n += _kesu_folder('src/shiryo/' + slug, slug);
    n += _kesu_md(slug, 'src/kotae');
  } else if (slug.indexOf('nittei-') === 0) {
    n += _kesu_md(slug, 'src/nittei');
  } else if (slug.indexOf('todoita-') === 0) {
    /* グッズ（2026-09-24）。.md と、配っていたファイルと、見本を消します。
       ★.md の名前には日づけが付きません（名前がそのまま id になり、
         URL の #goods-… になるためです）。だから _kesu_md ではなく、
         名ざしで消します。 */
    n += _kesu_hitotsu('src/goods/' + slug + '.md', slug);
    n += _kesu_hitotsu('src/goods/mihon/' + slug + '.webp', slug);
    for (var gk in GOODS_KATA) {
      n += _kesu_hitotsu('src/downloads/' + slug + '.' + gk, slug);
    }
  } else {
    n += _kesu_folder('src/bansho/' + slug, slug);
    n += _kesu_folder('src/shiryo/' + slug, slug);
    n += _kesu_md(slug, 'src/jissen');
  }
  return n;
}

/* あるお悩みにぶら下がっている答えを、ぜんぶ消します。
   中身の toi を読んで選ぶので、名前だけでは分かりません。 */
function _kotae_kesu(toi) {
  var ichiran = _github_miru('src/kotae');
  if (!ichiran) return 0;
  var n = 0;
  for (var i = 0; i < ichiran.length; i++) {
    var na = ichiran[i].name || '';
    if (na.slice(-3) !== '.md' || na.charAt(0) === '_') continue;
    var hon = _github_yomu(ichiran[i].path);
    if (!hon) continue;
    if (new RegExp('^toi:\\s*' + toi + '\\s*$', 'm').test(hon)) {
      /* その答えに添えられた写真・資料も一緒に。ファイル名から名前を取ります
         （2026-09-24_kotae-…….md の、_ から後ろ・.md の手前）。 */
      var ko = na.replace(/^.*?_/, '').replace(/\.md$/, '');
      if (ko.indexOf('kotae-') === 0) {
        n += _kesu_folder('src/bansho/' + ko, ko);
        n += _kesu_folder('src/shiryo/' + ko, ko);
      }
      _github_kesu(ichiran[i].path, ichiran[i].sha, '答えを1つ消す（' + toi + '）');
      n++;
    }
  }
  return n;
}

/* 名ざしで1つ消す（2026-09-24）。無ければ 0 を返すだけです。
   ★_kesu_md は「2026-09-24_<slug>.md」の形を探します。グッズの .md には
     日づけが付かないので、こちらを使います。 */
function _kesu_hitotsu(michi, slug) {
  var ichiran = _github_miru(michi);
  if (!ichiran || !ichiran.length) return 0;
  _github_kesu(michi, ichiran[0].sha, '1つ消す（' + slug + '）');
  return 1;
}

function _kesu_md(slug, doko) {
  var ichiran = _github_miru(doko);
  if (!ichiran) return 0;
  var n = 0;
  for (var i = 0; i < ichiran.length; i++) {
    var na = ichiran[i].name || '';
    if (na.slice(-3) === '.md' && na.indexOf('_' + slug + '.') >= 0) {
      _github_kesu(ichiran[i].path, ichiran[i].sha, '1件を消す（' + slug + '）');
      n++;
    }
  }
  return n;
}


/* front matter は build.py の検問に合わせてあります（2026-09-21 実測で確認）。
   ここを触るときは build.py の kenmon_jissen() を見てください。
     share: true … これが無いと **丸ごと飛ばされます**（ここで1度つまずきました）
     naiyo     … gakkyu / gyoji / jidokai / club のどれか。gakkatsu は無い
     kind      … gidai なので time は要りません
   送り手は学年も内容も選びません。だから naiyo と scene は既定値です。
   ちがっていたら、あとから .md を手で直してください。 */
function _kyou() {
  return Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd');
}

/* front matter と本文に入れてはいけない形を落とします。
   1件の .md が検問に当たると、サイト全体のビルドが止まるためです。 */
function _arau(s) {
  return String(s || '')
    .replace(/[\r\n]+/g, ' ')                                   // 改行（front matter が壊れる）
    .replace(/^[#\-\s]+/, '')                                    // 行頭の # と -（見出し・--- 扱い）
    .replace(/^(効き目|自分の考え|返し|分野|kikime|kangae|kaeshi)\s*[:：]\s*/, '')  // 優アンテナの欄
    .trim();
}

/* 自由に書いてもらうところ。何行でも来ます。
   build.py が読める記法は ## 見出し／- 箇条書き／1. 番号／空行で段落 です。
   front matter を壊す形だけ落として、あとはそのまま通します。 */
function _arau_hon(s) {
  var gyo = String(s || '').replace(/\r\n?/g, '\n').split('\n');
  var deru = [];
  for (var i = 0; i < gyo.length; i++) {
    var l = gyo[i].replace(/\s+$/, '');
    if (/^\s*-{3,}\s*$/.test(l)) continue;   // --- は front matter の閉じと読まれます
    l = l.replace(/^(効き目|自分の考え|返し|分野|kikime|kangae|kaeshi)\s*[:：]\s*/, '');
    deru.push(l);
  }
  var hon = deru.join('\n').replace(/\n{3,}/g, '\n\n').trim();
  if (hon.charAt(0) === '#') hon = hon.replace(/^#+\s*/, '');   // 本文は見出しで始められません
  return hon;
}

/* ══ 内容：フォームの6つ → サイトの4つ（2026-09-22）══════════
   学習指導要領は 学級活動(1)(2)(3)・学校行事・児童会活動・クラブ活動 の6つ。
   サイトのカードは 学級活動・学校行事・児童会活動・クラブ活動 の4つです。
   だから **(1)(2)(3) は ぜんぶ「学級活動」のカードに集まります。**
   選んだ6つのほうは scene に残るので、札には (1)(2)(3) まで出ます。
   ★左の合言葉は src/hiroba.html の <option value="…"> と同じにしてください。
   ★naiyo に書けるのは gakkyu / gyoji / jidokai / club の4つだけです。
     ほかを書くと build.py が止まり、サイトが更新されません。 */
var NAIYO6 = {
  gakkyu1: ['gakkyu',  '学級活動(1)'],
  gakkyu2: ['gakkyu',  '学級活動(2)'],
  gakkyu3: ['gakkyu',  '学級活動(3)'],
  gyoji:   ['gyoji',   '学校行事'],
  jidokai: ['jidokai', '児童会活動'],
  club:    ['club',    'クラブ活動']
};

function _naiyo(kotae) {
  /* 選ばれていない・知らない合言葉のときは、いちばん多いところへ置きます。
     ここで落とすと、せっかく送ってもらったものが消えるためです。 */
  return NAIYO6[String(kotae || '')] || NAIYO6.gakkyu1;
}

/* 「提供：」に出す名前。
   ★名前を書いてもらうことと、サイトに出すことは別です（2026-09-22）。
     出すのは、本人が「名前を出してよい」に印を入れたときだけ。
     印が無ければ、名前は管理人へのお知らせにだけ残ります。 */
function _by(n) {
  if (!n.ko || !String(n.na || '').trim()) return '送ってくださった先生';
  var na = _arau(n.na);
  var sh = _arau(n.sh);
  return sh ? (na + '（' + sh + '）') : na;
}

function _md(slug, n) {
  var t = _arau(n.t);
  var g = _arau(n.g);
  var m = _arau_hon(n.m);
  var naiyo = _naiyo(n.n);
  var gyo = [
    '---',
    'share: true',
    /* 届いたもの、という目じるし（2026-09-22）。
       これが付いたものは「みんなの実践」に並びます。
       付いていないものは、こちらで用意した「すぐ使える道具」の棚です。
       ★外すと、届いた実践が道具箱のほうに出てしまいます。 */
    'okuri: true',
    'kind: gidai',
    'date: ' + _kyou(),
    /* 届いた時こく（2026-09-22）。並べるためだけに使います。
       日づけだけだと、同じ日に2件 届いたときに順が決まりません
       （名前のうしろ6文字はでたらめなので、くじ引きになります）。
       build.py の load_jissen() が、ここを見て新しい順に並べます。 */
    'todoita: ' + Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd HH:mm'),
    'title: ' + (t || (n.uri.length ? '送ってもらった板書' : '送ってもらった資料')),
    'grade: ' + (g || '学年なし'),
    'naiyo: ' + naiyo[0],
    'scene: ' + naiyo[1]
  ];
  if (n.nushi)      gyo.push('nushi: ' + n.nushi);
  if (n.uri.length) gyo.push('bansho: ' + slug);
  if (n.pdf)        gyo.push('shiryo: 送ってもらった資料|' + slug);
  gyo.push('by: ' + (n.by_hyoji !== undefined
                     ? (n.by_hyoji || '送ってくださった先生') : _by(n)));
  gyo.push('---');
  gyo.push('');
  gyo.push(m || (n.uri.length ? '送ってもらった板書です。' : '送ってもらった資料です。'));
  return gyo.join('\n');
}



/* ══ 1の6. 学級会グッズ（2026-09-24 依頼）═════════════════
   「学級会グッズのデータも募集できるようにしたい。
     ワードとかPDFのデータを受信できるようにしたい」

   ★板書のPDFとちがって、**画像に変えません**。そのまま配ります。
     グッズは「刷って使う／Wordで直して使う」ものなので、画像にしたら
     用が足りないためです。置き場は src/downloads/ で、workflow が
     _site/downloads/ に写します。**押した人だけ**が取りにいきます。
   ★Driveには残しません（GitHubに置いたものが、そのまま配るものです）。
   ★誰の目も通りません。そのまま公開ページへ出ます（板書と同じ）。
     知らせの［すぐ消す］で、1押しで下ろせます。

   ★ここを直すときに いっしょに見るところ
       build.py の load_goods（front matter の検問）
       src/hiroba.html の GD_KATA（受けとる形と上限）
     3つのうち1つだけ直すと、送れたのに出ない（またはその逆）になります。 */

/* しっぽ → [front matter の欄, 画面に出す名前, 上限MB, 中身の型] */
var GOODS_KATA = {
  pdf:  ['pdf',  'PDF',        8, 'application/pdf'],
  docx: ['docx', 'Word',       4, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
  pptx: ['pptx', 'PowerPoint', 8, 'application/vnd.openxmlformats-officedocument.presentationml.presentation'],
  xlsx: ['xlsx', 'Excel',      4, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
};
/* 種類。build.py の GOODS_SHURUI と同じ合いことばにしてください。
   知らないものが来たら g-sonota に寄せます（落とすと札が消えるため）。 */
var GOODS_ICON = { 'g-post':1, 'g-card':1, 'g-note':1, 'g-shikai':1, 'g-flow':1,
                   'g-mark':1, 'g-corner':1, 'g-digital':1, 'g-sonota':1 };
/* 刷る紙・学年。build.py の GOODS_KAMI / GOODS_NEN と同じ並びです。 */
var GOODS_KAMI = { 'A4たて':1, 'A4よこ':1, 'B4たて':1, 'B4よこ':1,
                   'A3たて':1, 'A3よこ':1, 'その他':1 };
var GOODS_NEN  = { '1年':1, '2年':1, '3年':1, '4年':1, '5年':1, '6年':1,
                   '中学校':1, '全学年':1 };
/* 直して使ってよいか。**直せる形を配ってよいのは下の2つだけ**です。
   空や知らない合いことばは「そのまま刷るだけ」に倒します
   （許しの無いほうへ倒す。Wordを出してからでは取り返せません）。 */
var GOODS_NAOSERU = { naoshite:1, kubatte:1 };
var GOODS_SITE = 'https://yuutennis657-beep.github.io/tokkatsu-hiroba/downloads/';
var GOODS_T_MAX = 30;     // グッズの名前
var GOODS_D_MAX = 60;     // どんなものか（1行）
var GOODS_M_MAX = 600;    // 使い方

function _goods(d) {
  var f = d.f || {};
  var naoseru = !!GOODS_NAOSERU[String(d.no || '')];

  var t = _arau(d.t).slice(0, GOODS_T_MAX);
  var de = _arau(d.d).slice(0, GOODS_D_MAX);
  if (!t) return _kotae({ ok: false, riyu: 'グッズの名前がありません' });
  if (!de) return _kotae({ ok: false, riyu: '「どんなものか」がありません' });

  /* 送られたファイルを、先に ぜんぶ読んで確かめます。
     1つでもだめなら、GitHubには1つも置きません（半分だけ置いて、
     .md が それを指す、という形を作らないため）。 */
  /* 名前は todoita- で始めます（2026-09-24）。
     ★goods- にすると、札のidが #goods-goods-… と二重になります。
     ★_slug_kesu は、この頭の字を見てグッズだと決めています。 */
  var slug = _slug('todoita');
  var oku = [];
  for (var s in GOODS_KATA) {
    if (!f[s]) continue;
    /* そのまま刷るだけ、と決めた人のぶんは、直せる形を受けとりません。
       受けとってから出さないのではなく、**はじめから置きません**。 */
    if (s !== 'pdf' && !naoseru) continue;
    var b = _dataURI_kata(f[s], GOODS_KATA[s][3]);
    if (!b) {
      return _kotae({ ok: false, riyu: GOODS_KATA[s][1] + 'の形が読めません' });
    }
    if (b.getBytes().length > GOODS_KATA[s][2] * 1024 * 1024) {
      return _kotae({ ok: false,
        riyu: GOODS_KATA[s][1] + 'が大きすぎます（' + GOODS_KATA[s][2] + 'MBまで）' });
    }
    /* ★ほんとうに開けるか、ここで1度あけてみます（2026-09-24 実測）。
       壊れた .docx が1つ置かれただけで、ワークフローの
       「作成者を消す」が落ち、**サイトがまるごと更新されなくなりました**。
       あちらも止まらないように直しましたが、**読めないものは
       はじめから置かない**のが、いちばん確かです。 */
    if (!_akeru(b, s)) {
      return _kotae({ ok: false, riyu: GOODS_KATA[s][1] + 'が開けません（壊れています）' });
    }
    oku.push({ s: s, na: slug + '.' + s, b64: Utilities.base64Encode(b.getBytes()) });
  }

  var u = _goods_link(d.u);
  if (!oku.length && !u) {
    return _kotae({ ok: false, riyu: 'ファイルも 資料リンクもありません' });
  }
  if (!_kazoeru()) return _kotae({ ok: false, riyu: '今日はもう受けとれません' });

  var nose = { ok: false, riyu: '' };
  try {
    for (var i = 0; i < oku.length; i++) {
      _github('src/downloads/' + oku[i].na, oku[i].b64,
              'グッズのファイルを1つ置く（' + oku[i].na + '）');
    }
    /* .md は **いちばん最後**です。build.py は .md から辿るので、
       先に .md を置くと、ファイルの着く前のビルドが「404になるリンク」を
       見つけて、その欄を削ってしまいます。 */
    _github('src/goods/' + slug + '.md',
            Utilities.base64Encode(_md_goods(slug, d, t, de, oku, u, naoseru),
                                   Utilities.Charset.UTF_8),
            'グッズを1点のせる（' + slug + '）');
    nose.ok = true;
  } catch (err) {
    nose.riyu = String(err);
  }

  _shiraseru_goods(slug, d, t, de, oku, u, naoseru, nose);
  return _kotae({ ok: true, noseta: nose.ok });
}

/* ほんとうに開けるファイルかどうか。
     PDF   … 頭が %PDF- で始まるか
     Office … zip として開けて、[Content_Types].xml が入っているか
   ★ここで見るのは「形が壊れていないか」だけです。中身は見ません。 */
function _akeru(b, shippo) {
  try {
    if (shippo === 'pdf') {
      var atama = b.getBytes().slice(0, 5);
      return String.fromCharCode.apply(null, atama) === '%PDF-';
    }
    var naka = Utilities.unzip(b.setContentType('application/zip'));
    b.setContentType(GOODS_KATA[shippo][3]);      // 型を戻す
    for (var i = 0; i < naka.length; i++) {
      if (naka[i].getName().indexOf('[Content_Types].xml') >= 0) return true;
    }
    return false;
  } catch (err) {
    return false;
  }
}

/* data URI を、決めた型のときだけ受けとります。
   ★型を見ないと、拡張子だけ .docx の何かを置けてしまいます。 */
function _dataURI_kata(s, kata) {
  var m = String(s).match(/^data:([^;,]*);base64,(.+)$/);
  if (!m) return null;
  var kita = String(m[1] || '').toLowerCase();
  /* 端末によっては型が空で来ます（拡張子から決められなかったとき）。
     そのときは、こちらで決めた型として受けます。ちがう型を名のって
     いるときだけ、断ります。 */
  if (kita && kita !== kata && kita !== 'application/octet-stream') return null;
  return Utilities.newBlob(Utilities.base64Decode(m[2]), kata);
}

/* 外の資料リンク。受ける置き場だけです（build.py の SHIRYO_SOTO_DOKO と
   src/hiroba.html の SHIRYO_DOKO と、同じ顔ぶれにしてください）。 */
var GOODS_DOKO = ['canva.com', 'canva.link', 'docs.google.com',
                  'drive.google.com', 'onedrive.live.com', '1drv.ms', 'dropbox.com'];

function _goods_link(u) {
  u = String(u || '').trim().slice(0, 300);
  var m = /^https:\/\/([^\/?#]+)/i.exec(u);
  if (!m) return '';
  var h = m[1].toLowerCase().split(':')[0];
  for (var i = 0; i < GOODS_DOKO.length; i++) {
    var dd = GOODS_DOKO[i];
    if (h === dd || h.slice(-(dd.length + 1)) === '.' + dd) return u;
  }
  return '';
}

function _md_goods(slug, d, t, de, oku, u, naoseru) {
  var gyo = ['---'];
  /* 届いたぶん、という印。**これが無いと道具箱のほうに出ます**
     （build.py の load_goods が、ここだけを見て棚を分けています）。 */
  gyo.push('okurareta: true');
  gyo.push('order: 99');
  gyo.push('date: ' + _kyou());
  gyo.push('title: ' + t);
  gyo.push('desc: ' + de);
  gyo.push('icon: ' + (GOODS_ICON[String(d.sh || '')] ? d.sh : 'g-sonota'));

  var kami = _arau(d.kami);
  if (GOODS_KAMI[kami]) gyo.push('kami: ' + kami);

  var nen = String(d.g || '').split('・').filter(function (x) {
    return GOODS_NEN[x.trim()];
  }).map(function (x) { return x.trim(); });
  if (nen.length) gyo.push('nen: ' + nen.join(','));

  /* 直して使ってよいか。知らない合いことばは sonomama に倒します。 */
  gyo.push('naoshi: ' + (naoseru ? d.no : 'sonomama'));

  /* 提供者。サイトに名前を出すかどうかは、本人が決めています（→ _by）。
     所属は かっこの中に入り、公開ページでは build.py の namae_dake() が
     落とします（管理画面には残ります）。 */
  gyo.push('by: ' + _by({ ko: d.ko, na: d.na, sh: d.s }));

  var ken = _arau(d.ken);
  if (/^.{2,5}[都道府県]$/.test(ken)) {
    gyo.push('ken: ' + ken);
    var shi = _arau(d.shk).slice(0, 20);
    if (shi) gyo.push('shi: ' + shi);
  }
  if (u) gyo.push('u: ' + u);

  for (var i = 0; i < oku.length; i++) {
    gyo.push(GOODS_KATA[oku[i].s][0] + ': ' + GOODS_SITE + oku[i].na);
  }
  /* mihon: は書きません。見本（PDFの1ページ目）は、このあと
     .github/workflows/build.yml が作って、ここへ書き足します。
     先に書くと、画像の無いうちに検問へかかります。 */
  gyo.push('---');
  gyo.push('');
  gyo.push(_arau_hon(d.m).slice(0, GOODS_M_MAX));
  return gyo.join('\n');
}

function _shiraseru_goods(slug, d, t, de, oku, u, naoseru, nose) {
  var url = _webapp();
  var katachi = oku.map(function (o) { return GOODS_KATA[o.s][1]; }).join('・') || '（なし）';
  var kesareta = [];
  for (var s in GOODS_KATA) {
    if (d.f && d.f[s] && s !== 'pdf' && !naoseru) kesareta.push(GOODS_KATA[s][1]);
  }
  var honbun =
    (nose.ok ? 'グッズが1点とどき、そのまま載せました。数分でページに出ます。\n'
             : 'グッズが1点とどきましたが、載せられませんでした。\n' +
               '　理由：' + (nose.riyu || '（不明）') + '\n') +
    '\n' +
    '　名前　：' + t + '\n' +
    '　1行　 ：' + de + '\n' +
    '　種類　：' + (d.sh || '（なし）') + '\n' +
    '　学年　：' + (d.g || '（なし）') + '\n' +
    '　刷る紙：' + (d.kami || '（なし）') + '\n' +
    '　直して：' + (naoseru ? d.no : 'sonomama（直せる形は出しません）') + '\n' +
    '　ファイル：' + katachi + '\n' +
    (kesareta.length
       ? '　　★' + kesareta.join('・') + ' は受けとっていません'
         + '（「そのまま刷って使ってください」が選ばれているため）\n' : '') +
    '　資料リンク：' + (u || '（なし）') + '\n' +
    /* ★お名前は、サイトに出ていなくても ここには必ず出します。 */
    '　お名前：' + (d.na || '（名乗られていません）')
      + (String(d.na || '').trim()
           ? (d.ko ? '　← サイトにも出しています' : '　← サイトには出していません')
           : '') + '\n' +
    '　所属　：' + (d.s || '（なし）') + '\n\n' +
    '＜使い方＞\n' + (_arau_hon(d.m) || '（なし）') + '\n\n' +
    '★ ファイルの中（本文・ヘッダー・フッター）に 学校名や子どもの名前が\n' +
    '　 残っていないか、**かならず開いて**確かめてください。\n' +
    '　 作成者の名前だけは、こちらで機械が消しています。中身は消せません。\n\n' +
    '★ 市販のワークシートが混ざっていないかも、あわせて見てください。\n\n' +
    (url ? 'すぐ消す：' + url + '?v=' + slug + '&k=' + _kanri_key() + '\n\n' +
           '（公開ページとファイルの置き場から消えます。GitHubの履歴には残ります）\n'
         : '（WEBAPP_URL が空なので、消すところを出せていません）');

  var mail = _mail();
  if (mail) MailApp.sendEmail(mail, '【TOKKATSU広場】学級会グッズが1点とどきました', honbun);
}


/* ══ 4. GitHub に1つ置く ══════════════════════════════════ */

function _github(michi, b64, riyu) {
  var eda = _p('GITHUB_BRANCH', 'main');
  var url = _gh_url(michi);
  var atama = _gh_atama();

  // 同じ名前がすでにあれば、上書きのために sha が要ります
  var sha = null;
  var ima = UrlFetchApp.fetch(url + '?ref=' + eda,
    { headers: atama, muteHttpExceptions: true });
  if (ima.getResponseCode() === 200) sha = JSON.parse(ima.getContentText()).sha;

  var nakami = { message: riyu, content: b64, branch: eda };
  if (sha) nakami.sha = sha;

  var kotae = UrlFetchApp.fetch(url, {
    method: 'put', headers: atama, contentType: 'application/json',
    payload: JSON.stringify(nakami), muteHttpExceptions: true
  });
  if (kotae.getResponseCode() >= 300) {
    throw new Error('GitHub が断りました：' + kotae.getContentText().slice(0, 200));
  }
}

/* フォルダの中身を見る（無ければ null）。消すときに sha が要ります。 */
function _github_miru(michi) {
  var kotae = UrlFetchApp.fetch(_gh_url(michi) + '?ref=' + _p('GITHUB_BRANCH', 'main'),
    { headers: _gh_atama(), muteHttpExceptions: true });
  if (kotae.getResponseCode() === 404) return null;
  if (kotae.getResponseCode() >= 300) {
    throw new Error('GitHub が断りました：' + kotae.getContentText().slice(0, 200));
  }
  var j = JSON.parse(kotae.getContentText());
  return (j && j.length) ? j : (j && j.path ? [j] : null);
}

function _github_kesu(michi, sha, riyu) {
  var kotae = UrlFetchApp.fetch(_gh_url(michi), {
    method: 'delete', headers: _gh_atama(), contentType: 'application/json',
    payload: JSON.stringify({ message: riyu, sha: sha,
                              branch: _p('GITHUB_BRANCH', 'main') }),
    muteHttpExceptions: true
  });
  if (kotae.getResponseCode() >= 300) {
    throw new Error('GitHub が断りました：' + kotae.getContentText().slice(0, 200));
  }
}

function _gh_url(michi) {
  return 'https://api.github.com/repos/' + _p('GITHUB_REPO', 'yuutennis657-beep/tokkatsu-hiroba') +
         '/contents/' + encodeURI(michi).replace(/#/g, '%23');
}
function _gh_atama() {
  var token = _p('GITHUB_TOKEN');
  if (!token) throw new Error('GITHUB_TOKEN がありません');
  return { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' };
}

function _html(ji) {
  return HtmlService.createHtmlOutput(
    '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<div style="font:16px/1.9 -apple-system,sans-serif;padding:40px 24px;text-align:center">' +
    ji + '</div>');
}
