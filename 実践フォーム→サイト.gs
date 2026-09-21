/**
 * 実践フォーム → サイト（ボタン1回で載る）
 * ─────────────────────────────────────────────────────────
 * 2026-09-21
 *
 * やること
 *   1. フォームに実践が届く
 *   2. この仕掛けが .md の形に整えて、管理人にメールを1通出す
 *      （メールの中に［載せる］［載せない］のボタンがある）
 *   3. ［載せる］を押すと、GitHub に .md が1つ増える
 *   4. GitHub Actions が build.py を走らせて、index.html が新しくなる
 *
 *   押すのは1回。押すまでは、サイトには1文字も出ません。
 *
 * 置き方
 *   フォームの回答スプレッドシート → 拡張機能 → Apps Script → このコードを貼る
 *
 * 先に入れておくもの（プロジェクトの設定 → スクリプト プロパティ）
 *   ADMIN_MAIL     … 知らせを受けとるメールアドレス
 *   GITHUB_TOKEN   … GitHubの細かい権限つきトークン（Contents: Read and write）
 *   GITHUB_REPO    … 例 yuutennis657-beep/tokkatsu-hiroba
 *   GITHUB_BRANCH  … 例 main（空なら main）
 *
 *   LINE_TOKEN     … LINE公式アカウントのチャネルアクセストークン（省いてよい）
 *                    入れると、LINEに［載せる］［載せない］のボタンが届きます
 *   LINE_TO        … 送る相手のユーザーID（省くと「友だち全員」に送ります。
 *                    自分だけが友だちの公式アカウントなら、それで自分だけに届きます）
 *
 * 動かす前に1回だけ
 *   ・関数 hajimeru を実行（送信時のトリガが付きます）
 *   ・デプロイ → 新しいデプロイ → 種類「ウェブアプリ」
 *       次のユーザーとして実行：自分
 *       アクセスできるユーザー：全員        ← ボタンを押すのに要ります
 *     出てきたURLを、スクリプト プロパティ WEBAPP_URL に貼る
 */

/* ══ 0. 設定 ══════════════════════════════════════════════ */

var P = PropertiesService.getScriptProperties();

/** 「場面」の答え → 4つの内容（build.py の naiyo）。当たらなければ学級活動にする。 */
var NAIYO = [
  ['児童会', 'jidokai'], ['代表委員会', 'jidokai'], ['委員会', 'jidokai'],
  ['クラブ', 'club'],
  ['行事', 'gyoji'], ['運動会', 'gyoji'], ['卒業', 'gyoji'], ['遠足', 'gyoji'],
  ['学級活動', 'gakkyu'], ['学級会', 'gakkyu'], ['係', 'gakkyu'], ['当番', 'gakkyu']
];

/**
 * フォームの質問名 → 使うキー。
 * **質問名のどこかに入っていれば当たります**（全部が同じでなくてよい）。
 * 2026-09-21 に、いま動いているフォームの見出しに合わせました。
 *   実践・資料の題名／概要（2〜3行）／場面／学年／かかる時間／
 *   週案にそのまま書ける1行／準備するもの／流れ／板書／写真・PDF資料の添付／
 *   つまずき（よくある姿 → こうしてみる）／サイトに載せるとき、提供者の名前を…／
 *   出してよいお名前・学校名／ご連絡先（メールアドレスなど）
 */
var TOI = {
  title  : '題名',
  lead   : '概要',
  scene  : '場面',
  grade  : '学年',
  time   : 'かかる時間',
  weekly : '週案',
  junbi  : '準備するもの',
  nagare : '流れ',
  bansho : '板書',
  shashin: '添付',
  tsumazuki: 'つまずき',
  nanori : '提供者の名前',
  na     : '出してよいお名前',
  mail   : 'ご連絡先'
};


/* ══ 1. 届いたとき ════════════════════════════════════════ */

function hajimeru() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  ScriptApp.getProjectTriggers().forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('todoita').forSpreadsheet(ss).onFormSubmit().create();
  matsuSheet_();
  Logger.log('トリガを付けました。つぎはウェブアプリとしてデプロイしてください。');
}


function todoita(e) {
  okuru_(hiraku_(e));
}


/** 動きを見るための1件（手で実行します）。メールが届けば、道はつながっています。 */
function tameshi() {
  okuru_({
    title: 'ためしの1件（あとで消してください）',
    lead:  'これは、知らせが届くかを見るための、ためしの実践です。',
    scene: '学級活動(1)・話合い', grade: '全学年', time: '45分',
    weekly: '学級会：ためし',
    junbi: 'ためし', nagare: 'ためし', bansho: 'ためし', tsumazuki: 'ためし',
    nanori: '名前を出さない'
  });
  Logger.log('送りました。メール（と、入れてあればLINE）を見てください。');
}


function okuru_(ans) {
  var id  = Utilities.getUuid().slice(0, 8);
  var md  = tsukuru_(ans, id);

  var sh = matsuSheet_();
  sh.appendRow([new Date(), id, ans.title || '(題名なし)', 'まち', mdPath_(ans, id), md]);

  var url = P.getProperty('WEBAPP_URL') || '';
  var honbun =
    '実践が1件とどきました。\n\n' +
    '■ 題名\n' + (ans.title || '(題名なし)') + '\n\n' +
    '■ ひとこと\n' + (ans.lead || '') + '\n\n' +
    '■ 場面／学年／時間\n' + [ans.scene, ans.grade, ans.time].join('・') + '\n\n' +
    '■ 提供\n' + teikyo_(ans) + '\n\n' +
    (ans.shashin ? '■ 添付（板書の写真・PDF）\n' + ans.shashin + '\n' +
                   '　画像は src/shiryo/◯◯/ に置くと、ページの中で開きます。\n\n' : '') +
    '───────────────\n' +
    '［載せる］  ' + url + '?do=of&id=' + id + '\n' +
    '［載せない］' + url + '?do=ng&id=' + id + '\n' +
    '───────────────\n\n' +
    '［載せる］を押すと、GitHubに1ファイル増えて、サイトが作り直されます。\n' +
    '押すまでは、サイトには1文字も出ません。\n\n' +
    '■ 入るファイル（' + mdPath_(ans, id) + '）\n\n' + md;

  // LINEにはボタンだけ、メールには中身ぜんぶ。どちらか片方でも動きます。
  lineDe_(ans.title || '(題名なし)', id);
  var mail = P.getProperty('ADMIN_MAIL');
  if (mail) {
    MailApp.sendEmail({
      to: mail,
      subject: '【特活広場】実践がとどきました：' + (ans.title || '(題名なし)'),
      body: honbun
    });
  }
}


/**
 * LINE公式アカウント（Messaging API）に、ボタン2つの知らせを送る。
 * LINE_TOKEN が入っていなければ、何もしません（メールだけになります）。
 */
function lineDe_(title, id) {
  var token = P.getProperty('LINE_TOKEN');
  var url   = P.getProperty('WEBAPP_URL') || '';
  if (!token || !url) return;

  var to = (P.getProperty('LINE_TO') || '').trim();
  var hako = {
    type: 'template',
    altText: '実践がとどきました：' + title,
    template: {
      type: 'buttons',
      title: '実践がとどきました',
      text: kiru_(title, 60),
      actions: [
        { type: 'uri', label: '載せる',     uri: url + '?do=of&id=' + id },
        { type: 'uri', label: '載せない',   uri: url + '?do=ng&id=' + id },
        { type: 'uri', label: '中身を見る', uri: SpreadsheetApp.getActiveSpreadsheet().getUrl() }
      ]
    }
  };
  var saki = to ? 'https://api.line.me/v2/bot/message/push'
                : 'https://api.line.me/v2/bot/message/broadcast';
  var tsutsumi = to ? { to: to, messages: [hako] } : { messages: [hako] };

  var res = UrlFetchApp.fetch(saki, {
    method: 'post',
    contentType: 'application/json',
    headers: { Authorization: 'Bearer ' + token },
    payload: JSON.stringify(tsutsumi),
    muteHttpExceptions: true
  });
  if (res.getResponseCode() !== 200) {
    Logger.log('LINEに送れませんでした： ' + res.getResponseCode() + ' ' + res.getContentText());
  }
}


/** LINEのボタンは字数に上限がある（題名60字・題40字）。はみ出たら…で切る。 */
function kiru_(s, n) {
  s = String(s || '');
  return s.length <= n ? s : s.slice(0, n - 1) + '…';
}


/** LINEがつながるか、いますぐ試すための関数（手で実行します）。 */
function lineTameshi() {
  lineDe_('つなぎの確認（これはためしです）', 'tameshi');
  Logger.log('送りました。LINEに届いていなければ、実行ログを見てください。');
}


/* ══ 2. ボタンを押したとき ════════════════════════════════ */

function doGet(e) {
  var id = (e.parameter.id || '').trim();
  var do_ = (e.parameter.do || '').trim();
  var sh = matsuSheet_();
  var hyo = sh.getDataRange().getValues();

  for (var i = 1; i < hyo.length; i++) {
    if (hyo[i][1] !== id) continue;
    if (hyo[i][3] !== 'まち') return kaesu_('もう押してあります（' + hyo[i][3] + '）。');

    if (do_ === 'ng') {
      sh.getRange(i + 1, 4).setValue('載せない');
      return kaesu_('載せませんでした。サイトは何も変わりません。');
    }
    if (do_ === 'of') {
      var r = commit_(hyo[i][4], hyo[i][5], hyo[i][2]);
      sh.getRange(i + 1, 4).setValue(r.ok ? '載せた' : 'しくじり');
      return kaesu_(r.ok
        ? '載せました。1〜2分でサイトが新しくなります。<br>' + hyo[i][4]
        : 'GitHubに置けませんでした。<br>' + r.mes);
    }
  }
  return kaesu_('その知らせは見つかりませんでした。');
}


/* ══ 3. GitHub に1ファイル置く ════════════════════════════ */

function commit_(path, md, title) {
  var repo   = P.getProperty('GITHUB_REPO');
  var token  = P.getProperty('GITHUB_TOKEN');
  var branch = P.getProperty('GITHUB_BRANCH') || 'main';
  if (!repo || !token) return { ok: false, mes: 'GITHUB_REPO か GITHUB_TOKEN が入っていません。' };

  var url = 'https://api.github.com/repos/' + repo + '/contents/' + encodeURI(path);
  var res = UrlFetchApp.fetch(url, {
    method: 'put',
    contentType: 'application/json',
    headers: { Authorization: 'Bearer ' + token, Accept: 'application/vnd.github+json' },
    payload: JSON.stringify({
      message: '実践を1件足す：' + title,
      content: Utilities.base64Encode(md, Utilities.Charset.UTF_8),
      branch: branch
    }),
    muteHttpExceptions: true
  });
  var code = res.getResponseCode();
  return (code === 201 || code === 200)
    ? { ok: true, mes: '' }
    : { ok: false, mes: code + ' ' + res.getContentText().slice(0, 300) };
}


/* ══ 4. .md を組む ════════════════════════════════════════ */

function tsukuru_(a, id) {
  var kyou = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd');
  var s = [];
  s.push('---');
  s.push('date: ' + kyou);
  s.push('share: true');
  s.push('title: ' + ichigyo_(a.title));
  s.push('grade: ' + ichigyo_(a.grade || '全学年'));
  s.push('naiyo: ' + naiyo_(a.scene));
  s.push('scene: ' + ichigyo_(a.scene || '学級活動(1)'));
  s.push('time: ' + ichigyo_(a.time || '45分'));
  if (a.weekly) s.push('weekly: ' + ichigyo_(a.weekly));
  s.push('by: ' + teikyo_(a));
  s.push('---');
  s.push(a.lead || '');
  if (a.junbi)     { s.push(''); s.push('## 準備するもの'); s.push(kajo_(a.junbi)); }
  if (a.nagare)    { s.push(''); s.push('## 流れ');         s.push(banme_(a.nagare)); }
  if (a.bansho)    { s.push(''); s.push('## 板書');         s.push(a.bansho); }
  if (a.tsumazuki) { s.push(''); s.push('## つまずき');     s.push(kajo_(a.tsumazuki)); }
  return s.join('\n') + '\n';
}

function mdPath_(a, id) {
  var kyou = Utilities.formatDate(new Date(), 'Asia/Tokyo', 'yyyy-MM-dd');
  return 'src/jissen/' + kyou + '_okuri-' + id + '.md';
}

function naiyo_(scene) {
  var t = String(scene || '');
  for (var i = 0; i < NAIYO.length; i++) if (t.indexOf(NAIYO[i][0]) >= 0) return NAIYO[i][1];
  return 'gakkyu';
}

function teikyo_(a) {
  var n = String(a.nanori || '');
  if (n.indexOf('出さない') >= 0 || !a.na) return '送ってくださった先生';
  return ichigyo_(a.na);
}

/** front matter は1行しか置けない。改行と : を落とす。 */
function ichigyo_(s) {
  return String(s == null ? '' : s).replace(/[\r\n]+/g, ' ').replace(/:/g, '：').trim();
}

function kajo_(s) {
  return String(s).split(/\r?\n/).filter(function (x) { return x.trim(); })
                  .map(function (x) { return '- ' + x.trim().replace(/^[-・]\s*/, ''); }).join('\n');
}

function banme_(s) {
  var g = String(s).split(/\r?\n/).filter(function (x) { return x.trim(); });
  return g.map(function (x, i) {
    return (i + 1) + '. ' + x.trim().replace(/^\d+[.．)]\s*/, '');
  }).join('\n');
}


/* ══ 5. 小道具 ════════════════════════════════════════════ */

/** 質問名のことばが入っていれば、その答えを拾う。 */
function hiraku_(e) {
  var out = {}, mae = e.namedValues || {};
  Object.keys(TOI).forEach(function (k) {
    var sagasu = TOI[k];
    Object.keys(mae).forEach(function (toi) {
      if (toi.indexOf(sagasu) >= 0 && !out[k]) {
        var v = mae[toi];
        out[k] = (v && v.join) ? v.join(' ').trim() : String(v || '').trim();
      }
    });
  });
  return out;
}

function matsuSheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName('まち');
  if (!sh) {
    sh = ss.insertSheet('まち');
    sh.appendRow(['とどいた', 'id', '題名', '様子', '入るファイル', '中身']);
    sh.setFrozenRows(1);
  }
  return sh;
}

function kaesu_(mes) {
  return HtmlService.createHtmlOutput(
    '<meta name="viewport" content="width=device-width,initial-scale=1">' +
    '<div style="font-family:system-ui;padding:28px;font-size:17px;line-height:1.9">' +
    mes + '</div>');
}
