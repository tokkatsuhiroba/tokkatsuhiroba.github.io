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

/* 入れてもらうものを1つに減らすため、空のときは自分で決めます。
   ここで決められないのは GITHUB_TOKEN だけです（合言葉なので、
   人の手で入れてもらうしかありません）。 */
function _mail() {
  return _p('ADMIN_MAIL') || Session.getEffectiveUser().getEmail();
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
    var shashin = (d.e || []).slice(0, MAI_MAX);
    if (!shashin.length) return _kotae({ ok: false, riyu: '写真がありません' });

    if (!_kazoeru()) return _kotae({ ok: false, riyu: '今日はもう受けとれません' });

    var slug = _slug();
    var folder = _folder(slug);
    var uri = [];

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

    // 押すまで、サイトには1枚も出ません。ここでやるのは知らせるところまで。
    CacheService.getScriptCache().put(
      slug, JSON.stringify({ uri: uri, t: d.t || '', g: d.g || '' }), 21600);

    _shiraseru(slug, d, folder);
    return _kotae({ ok: true });

  } catch (err) {
    return _kotae({ ok: false, riyu: String(err) });
  }
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

/* フォルダ名。英小文字・数字・- だけ（build.py の検問に合わせています） */
function _slug() {
  var d = new Date();
  var hi = Utilities.formatDate(d, 'Asia/Tokyo', 'yyyyMMdd');
  var ran = Utilities.getUuid().slice(0, 6);
  return 'bansho-' + hi + '-' + ran;
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

function _shiraseru(slug, d, folder) {
  var url = _webapp();
  var mail = _mail();
  if (!mail) return;

  var honbun =
    '板書が1件とどきました。\n\n' +
    '　ひとこと：' + (d.t || '（なし）') + '\n' +
    '　学年　　：' + (d.g || '（なし）') + '\n' +
    '　枚数　　：' + (d.e || []).length + '枚\n' +
    '　置き場　：' + folder.getUrl() + '\n\n' +
    '★ 送る前に、子どもの顔・名前・学校名が写っていないか見てください。\n\n' +
    (url
      ? '載せる　　：' + url + '?v=' + slug + '&d=1\n' +
        '載せない　：' + url + '?v=' + slug + '&d=0\n'
      : '（WEBAPP_URL が空なので、ボタンは出していません）');

  MailApp.sendEmail(mail, '【TOKKATSU広場】板書が1件とどきました', honbun);
}


/* ══ 3. ［載せる］を押したとき ════════════════════════════ */

function doGet(e) {
  var slug = (e.parameter.v || '').trim();
  var noseru = e.parameter.d === '1';
  if (!slug) return _html('行き先がありません');

  if (!noseru) return _html('載せませんでした。Driveの写真は残っています。');

  var nokori = CacheService.getScriptCache().get(slug);
  if (!nokori) return _html('時間が経ちすぎました（6時間まで）。Driveから手で置いてください。');
  var n = JSON.parse(nokori);

  for (var i = 0; i < n.uri.length; i++) {
    _github('src/bansho/' + slug + '/' + n.uri[i].na, n.uri[i].b64,
            '板書を1枚ふやす（' + slug + '）');
  }
  if (MD_MO_TSUKURU) {
    var md = _md(slug, n);
    _github('src/jissen/' + _kyou() + '_' + slug + '.md',
            Utilities.base64Encode(md, Utilities.Charset.UTF_8),
            '板書の1件を載せる（' + slug + '）');
  }
  return _html('載せました。数分で板書のページに出ます。');
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

function _md(slug, n) {
  var t = _arau(n.t);
  var g = _arau(n.g);
  return [
    '---',
    'share: true',
    'kind: gidai',
    'date: ' + _kyou(),
    'title: ' + (t || '送ってもらった板書'),
    'grade: ' + (g || '学年なし'),
    'naiyo: gakkyu',
    'scene: 学級活動(1)',
    'bansho: ' + slug,
    'by: 送ってくださった先生',
    '---',
    '',
    '送ってもらった板書です。'   // ひとことは title に入れました（ここに入れると二度出ます）
  ].join('\n');
}


/* ══ 4. GitHub に1つ置く ══════════════════════════════════ */

function _github(michi, b64, riyu) {
  var repo = _p('GITHUB_REPO', 'yuutennis657-beep/tokkatsu-hiroba');
  var eda = _p('GITHUB_BRANCH', 'main');
  var token = _p('GITHUB_TOKEN');
  if (!repo || !token) throw new Error('GITHUB_REPO か GITHUB_TOKEN がありません');

  var url = 'https://api.github.com/repos/' + repo + '/contents/' +
            encodeURI(michi).replace(/#/g, '%23');
  var atama = { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' };

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

function _html(ji) {
  return HtmlService.createHtmlOutput(
    '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<div style="font:16px/1.9 -apple-system,sans-serif;padding:40px 24px;text-align:center">' +
    ji + '</div>');
}
