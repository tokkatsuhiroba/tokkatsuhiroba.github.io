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
 *   写真は  src/bansho/<フォルダ名>/01.jpg 02.jpg …  に置きます。
 *   フォルダ名は英小文字・数字・- だけ（build.py がそう検問しています）。
 *   ★ 写真だけ置いても、板書のページには出ません（2026-09-21 実測）。
 *     build.py は写真のフォルダを直接は見ず、src/jissen/*.md の bansho: から
 *     辿ります。だから .md も一緒に作ります（MD_MO_TSUKURU = true）。
 */

/* ══ 0. 設定 ══════════════════════════════════════════════ */

var P = PropertiesService.getScriptProperties();

var MAI_MAX      = 3;        // 1回に受けとる枚数
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
    var d = JSON.parse(e.postData.contents);

    // 困りごと（2026-09-21 夜）。字だけなので、Driveには残しません。
    if (d.kind === 'komari') return _komari(d);

    // 研究日程（2026-09-22）。これも字だけです。
    if (d.kind === 'nittei') return _nittei(d);

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
      if (b.getBytes().length > KB_MAX * 1024) {
        return _kotae({ ok: false, riyu: '写真が大きすぎます（1枚 ' + KB_MAX + 'KBまで）' });
      }
      var na = ('0' + (i + 1)).slice(-2) + '.jpg';
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
  if (!/^(bansho|komari|nittei)-[0-9]{8}-[0-9a-z]+$/.test(slug)) return _html('行き先がありません');

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
  var keshita = 0;
  try {
    if (slug.indexOf('komari-') === 0) {
      keshita += _kesu_md(slug, 'src/komari');
    } else if (slug.indexOf('nittei-') === 0) {
      keshita += _kesu_md(slug, 'src/nittei');
    } else {
      keshita += _kesu_folder('src/bansho/' + slug, slug);
      keshita += _kesu_folder('src/shiryo/' + slug, slug);   // PDFから作った画像も
      keshita += _kesu_md(slug, 'src/jissen');
    }
  } catch (err) {
    return _html('消せませんでした：' + String(err).slice(0, 200) +
                 '<br><br>手で消すなら GitHub の src/ の中です（' + slug + '）。');
  }
  if (!keshita) return _html('もう残っていませんでした。');
  return _html('消しました（' + keshita + '件）。数分でページから消えます。<br><br>' +
               '<small>GitHub の履歴には残ります。Driveの写真も残っています。</small>');
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
  gyo.push('by: ' + _by(n));
  gyo.push('---');
  gyo.push('');
  gyo.push(m || (n.uri.length ? '送ってもらった板書です。' : '送ってもらった資料です。'));
  return gyo.join('\n');
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
