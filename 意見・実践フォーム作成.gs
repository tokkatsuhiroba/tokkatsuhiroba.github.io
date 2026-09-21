/**
 * TOKKATSU広場｜「困りごと・意見」と「実践・板書」の2つのフォームを作るスクリプト
 * ------------------------------------------------------------
 * これは 依頼フォーム作成.gs とは別のものです。
 *   依頼フォーム … サイトの間違い・掲載の取り下げを受けつける（管理のため）
 *   このファイル … 先生から困りごとと実践を受けとる（中身を増やすため）
 *
 * 使い方
 *   1. https://script.google.com/ を開く → 「新しいプロジェクト」
 *   2. 中身をぜんぶ消して、このファイルの中身を貼りつける
 *   3. 上の関数の選択で「フォームを2つ作る」を選び、▶ 実行
 *   4. 最初の1回だけ承認を求められる（自分のアカウントを選び「許可」）
 *   5. 下の「実行ログ」に、2つぶんの公開URLが出る
 *   6. そのURLを build.py の LINKS に貼る（39〜40行目）
 *        'FORM_IKEN'  : '（困りごと・意見の公開URL）',
 *        'FORM_JISSEN': '（実践・板書の公開URL）',
 *      貼ったら  python3 build.py  と  python3 build.py --simple  をやり直す
 *
 *   ★「通知メールを付ける」は、フォームを作ったあとに1回だけ実行する。
 *     2つのフォームのどちらに回答が来ても、TSUUCHI_SAKI へメールが飛ぶ。
 *
 * 写真について
 *   写真を受けとる質問（ファイルのアップロード）は、Apps Script では作れません。
 *   Google フォームの画面で、手で1つ足す必要があります。足すなら：
 *     1. 実践フォームの編集URLを開く
 *     2. 「板書の写真」の質問の下に、質問を1つ足す
 *     3. 質問の種類で「ファイルのアップロード」を選ぶ
 *   ただし、ファイルのアップロードにすると、送る人も Google への
 *   ログインが要ります。ログインなしで送れるほうを大事にするなら、
 *   足さずに、写真はメールで受けとるのが早いです。
 *   （このスクリプトが作るフォームは、メールで受けとる前提になっています）
 */

// ── ここだけ書きかえれば使える ──────────────────────────
var FORM_IKEN_MEI   = 'TOKKATSU広場｜困りごと・意見';
var FORM_JISSEN_MEI = 'TOKKATSU広場｜実践・板書を送る';
var SITE_URL        = 'https://yuutennis657-beep.github.io/tokkatsu-hiroba/';
var TSUUCHI_SAKI    = 'yuutennis657@gmail.com';
// ────────────────────────────────────────────────────


function フォームを2つ作る() {
  var a = 困りごとフォームを作る_();
  var b = 実践フォームを作る_();

  Logger.log('');
  Logger.log('══ できました。この2つを build.py の LINKS に貼ってください ══');
  Logger.log("  'FORM_IKEN'  : '" + a.url + "',");
  Logger.log("  'FORM_JISSEN': '" + b.url + "',");
  Logger.log('');
  Logger.log('── 自分用（編集・回答の置き場） ──');
  Logger.log('困りごと　編集： ' + a.edit);
  Logger.log('困りごと　回答： ' + a.sheet);
  Logger.log('実践　　　編集： ' + b.edit);
  Logger.log('実践　　　回答： ' + b.sheet);
  Logger.log('');
  Logger.log('── 写真について ──');
  Logger.log('写真を受けとる質問は、スクリプトでは作れません。');
  Logger.log('いまのフォームは「写真はメールで送ってもらう」形になっています。');
  Logger.log('フォームで受けとりたいときは、上の「実践　編集」を開いて、');
  Logger.log('「板書の写真」の下に質問を1つ足し、種類を「ファイルのアップロード」にしてください。');
  Logger.log('※ そうすると、送る人も Google へのログインが要るようになります。');
}


// ══════════════════════════════════════════════════════════
// 1. 困りごと・意見フォーム（1分で送れることを最優先にする）
// ══════════════════════════════════════════════════════════

function 困りごとフォームを作る_() {

  var form = FormApp.create(FORM_IKEN_MEI);

  form.setDescription(
    'うまくいかないこと、聞きたいこと、サイトへの要望を送るところです。\n' +
    '\n' +
    '・無記名で構いません。ログインも要りません。\n' +
    '・1つだけ書いて送っていただいて大丈夫です。\n' +
    '・いただいた困りごとは、そのまま載せることはしません。\n' +
    '　同じ困りごとが集まったら、答えになる実践を「すぐ使える実践」に置きます。\n' +
    '\n' +
    'サイト： ' + SITE_URL
  );

  form.setCollectEmail(false);
  form.setAllowResponseEdits(false);
  form.setProgressBar(false);

  // ── 1. 困りごと（必須。これだけで送れる）──
  form.addParagraphTextItem()
      .setTitle('いま、うまくいかないこと')
      .setHelpText('ひとことで構いません。例：「話合いが時間内に終わらない」「同じ子しか発言しない」')
      .setRequired(true);

  // ── 2. いつの場面か ──
  var bamen = form.addMultipleChoiceItem();
  bamen.setTitle('どの場面のことですか')
       .setChoices([
         bamen.createChoice('学級活動(1)　話合い活動（学級会）'),
         bamen.createChoice('学級活動(2)　日常の生活づくり'),
         bamen.createChoice('学級活動(3)　キャリア形成'),
         bamen.createChoice('計画委員会・議題集め'),
         bamen.createChoice('係活動・当番活動'),
         bamen.createChoice('児童会・委員会活動'),
         bamen.createChoice('学校行事'),
         bamen.createChoice('特活ぜんぱん・どれでもない')
       ])
       .showOtherOption(true)
       .setRequired(false);

  // ── 3. 学年 ──
  var gakunen = form.addMultipleChoiceItem();
  gakunen.setTitle('学年')
         .setChoices([
           gakunen.createChoice('1〜2年'),
           gakunen.createChoice('3〜4年'),
           gakunen.createChoice('5〜6年'),
           gakunen.createChoice('中学校'),
           gakunen.createChoice('答えにくい・いくつもある')
         ])
         .setRequired(false);

  // ── 4. 返事の要る／要らない ──
  var henji = form.addMultipleChoiceItem();
  henji.setTitle('返事は要りますか')
       .setChoices([
         henji.createChoice('要りません（読んでもらえれば十分です）'),
         henji.createChoice('できれば返事がほしいです')
       ])
       .setRequired(false);

  // ── 5. 連絡先（返事が要るときだけ）──
  form.addTextItem()
      .setTitle('ご連絡先（メールアドレスなど）')
      .setHelpText('返事が要るときだけで大丈夫です。返事以外には使いません。')
      .setRequired(false);

  // ── 6. お名前 ──
  form.addTextItem()
      .setTitle('お名前・学校名')
      .setHelpText('無記名で構いません。')
      .setRequired(false);

  form.setConfirmationMessage(
    'お送りいただき、ありがとうございました。\n' +
    '同じ困りごとが集まったら、答えになる実践をサイトに置きます。\n' +
    '\n' +
    'すぐ使える実践： ' + SITE_URL + '#manabu'
  );

  var ss = SpreadsheetApp.create(FORM_IKEN_MEI + '｜回答');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());

  return {
    url  : form.shortenFormUrl(form.getPublishedUrl()),
    edit : form.getEditUrl(),
    sheet: ss.getUrl()
  };
}


// ══════════════════════════════════════════════════════════
// 2. 実践・板書フォーム
//    設問の並びは src/jissen/_テンプレート.md と同じにしてある。
//    回答をそのまま上から順に写せば、1件ぶんの .md ができる。
// ══════════════════════════════════════════════════════════

function 実践フォームを作る_() {

  var form = FormApp.create(FORM_JISSEN_MEI);

  form.setDescription(
    '明日そのまま使えた実践を、持ち寄るところです。板書の写真1枚でも構いません。\n' +
    '\n' +
    '・いただいたものは、こちらで確認のうえ「すぐ使える実践」に載せます。\n' +
    '・載せるときは、提供者のお名前を出すか、出さないかを選べます（下で選べます）。\n' +
    '・子どもの顔・名前が写っているものは、そのままでは載せられません。\n' +
    '　黒板だけが写るように撮っていただけると助かります。\n' +
    '・載せたあとでも「やめてほしい」と言っていただければ、1週間以内に下ろします。\n' +
    '・写真は、このフォームを送ったあとに ' + TSUUCHI_SAKI + ' 宛てにメールしてください。\n' +
    '\n' +
    'サイト： ' + SITE_URL
  );

  form.setCollectEmail(false);
  form.setAllowResponseEdits(true);   // 実践は後から直したくなるので、編集できるようにする
  form.setProgressBar(true);

  // ── 0. 実践か、議題か（2026-09-21）──
  //   議題ボックスを、実践と同じ箱に入れると決めました。ちがうのは厚みだけです。
  //   実践は「準備・流れ・つまずき」まで書ける人しか送れません。
  //   議題は、題名とひとことだけで送れます。**送る人のハードルを下げるための問い**です。
  //   ★この問いの題に「送るのは」が入っていること。
  //     実践フォーム→サイト.gs の TOI が、その字で見つけています。
  var shurui = form.addMultipleChoiceItem();
  shurui.setTitle('送るのは、どちらですか')
        .setHelpText('議題なら、題名とひとことだけで大丈夫です。' +
                     '下の「かかる時間」「流れ」は空のままで送れます。')
        .setChoices([
          shurui.createChoice('実践（準備・流れ・板書まで書けます）'),
          shurui.createChoice('議題だけ（こんな議題が出ました、の1件）')
        ])
        .setRequired(true);

  // ── 1. 題名（md の title）──
  form.addTextItem()
      .setTitle('実践の題名')
      .setHelpText('何をしたかが一目で分かるように。例：「計画委員会を10分で回す（学級会の前日）」\n' +
                   '議題を送る方は、議題をそのまま。例：「たてわり班であそぶ会をしよう」')
      .setRequired(true);

  // ── 2. ひとこと（md の最初の段落）──
  form.addParagraphTextItem()
      .setTitle('ひとこと（2〜3行）')
      .setHelpText('これをやると何が変わるかを書いてください。一覧に出る文になります。\n' +
                   '議題を送る方は、どんな声から出た議題かを2〜3行で。' +
                   'うまくいったかどうかは書かなくて構いません。')
      .setRequired(true);

  // ── 3. 場面（md の scene）──
  var scene = form.addMultipleChoiceItem();
  scene.setTitle('場面')
       .setChoices([
         scene.createChoice('学級活動(1)・話合い活動'),
         scene.createChoice('学級活動(1)・計画委員会'),
         scene.createChoice('学級活動(1)・当日の準備'),
         scene.createChoice('学級活動(2)・日常の生活づくり'),
         scene.createChoice('学級活動(3)・キャリア形成'),
         scene.createChoice('係活動・当番活動'),
         scene.createChoice('児童会・委員会活動'),
         scene.createChoice('学校行事')
       ])
       .showOtherOption(true)
       .setRequired(true);

  // ── 4. 学年（md の grade）──
  var grade = form.addMultipleChoiceItem();
  grade.setTitle('学年')
       .setChoices([
         grade.createChoice('1〜2年'),
         grade.createChoice('3〜4年'),
         grade.createChoice('5〜6年'),
         grade.createChoice('3〜6年'),
         grade.createChoice('全学年'),
         grade.createChoice('中学校')
       ])
       .showOtherOption(true)
       .setRequired(true);

  // ── 5. かかる時間（md の time）──
  var time = form.addMultipleChoiceItem();
  time.setTitle('かかる時間')
      .setChoices([
        time.createChoice('5分'),
        time.createChoice('10分'),
        time.createChoice('15分'),
        time.createChoice('45分（1時間）'),
        time.createChoice('何日かに分ける')
      ])
      .showOtherOption(true)
      .setRequired(false);   // 議題には時間がありません（2026-09-21）

  // ── 6. 週案の1行（md の weekly）──
  form.addTextItem()
      .setTitle('週案にそのまま書ける1行')
      .setHelpText('例：「昼休み：計画委員会10分（議題を1つに決める・話合いの順番・司会の分担）」\n' +
                   '思いつかなければ空でも構いません。こちらで書きます。')
      .setRequired(false);

  // ── 7. 準備するもの（md の ## 準備するもの）──
  form.addParagraphTextItem()
      .setTitle('準備するもの')
      .setHelpText('1行に1つずつ、改行で並べてください。')
      .setRequired(false);

  // ── 8. 流れ（md の ## 流れ）──
  form.addParagraphTextItem()
      .setTitle('流れ')
      .setHelpText('1行に1つずつ、順番に。何分かかるかも書いていただけると助かります。\n' +
                   '議題だけを送る方は、空のままで大丈夫です。')
      .setRequired(false);   // 議題には流れがありません（2026-09-21）

  // ── 9. 板書（md の ## 板書）──
  form.addParagraphTextItem()
      .setTitle('板書')
      .setHelpText('黒板に何をどう書いたかを、ことばで書いてください。写真は次でお願いします。')
      .setRequired(false);

  // ── 10. 板書の写真 ──
  //  ※ 写真を受けとる質問（ファイルのアップロード）は、Apps Script では作れません。
  //    Google フォームの画面で、手で1つ足す必要があります（下のログに手順が出ます）。
  //    ここでは、その代わりに「どう送るか」だけ聞いておきます。
  var shashin = form.addMultipleChoiceItem();
  shashin.setTitle('板書の写真')
         .setHelpText('黒板だけが写るように撮ってください。子どもの顔・名前が写っているものは載せられません。')
         .setChoices([
           shashin.createChoice('写真はありません（文だけで大丈夫です）'),
           shashin.createChoice('このあとメールで送ります（' + TSUUCHI_SAKI + ' 宛て）'),
           shashin.createChoice('すでにメールで送りました')
         ])
         .setRequired(false);

  // ── 11. つまずき（md の ## つまずき）──
  form.addParagraphTextItem()
      .setTitle('つまずき（よくある姿 → こうしてみる）')
      .setHelpText('うまくいかなかったことこそ、読む人の役に立ちます。\n' +
                   '例：「委員会が長引く → たいてい先生が話しすぎています。先生の出番は最後の2分だけにします。」')
      .setRequired(false);

  form.addPageBreakItem().setTitle('載せ方について');

  // ── 12. 名前の出し方（md の by）──
  var nanori = form.addMultipleChoiceItem();
  nanori.setTitle('サイトに載せるとき、提供者の名前をどうしますか')
        .setChoices([
          nanori.createChoice('出さない（「提供：先生方から」と書きます）'),
          nanori.createChoice('学校名だけ出す'),
          nanori.createChoice('名前も出してよい')
        ])
        .setRequired(true);

  form.addTextItem()
      .setTitle('出してよいお名前・学校名')
      .setHelpText('上で「出さない」を選んだ方は、空のままで大丈夫です。')
      .setRequired(false);

  // ── 13. 確認（必須）──
  var kakunin = form.addCheckboxItem();
  kakunin.setTitle('送る前の確認')
         .setChoices([
           kakunin.createChoice('写真に、子どもの顔や名前は写っていません'),
           kakunin.createChoice('この実践を、TOKKATSU広場に載せてよいです')
         ])
         .setRequired(true);

  //  2つとも入っていないと送れないようにする（片方だけでは送れない）
  kakunin.setValidation(
    FormApp.createCheckboxValidation()
           .setHelpText('2つとも確かめて、両方にチェックを入れてください。')
           .requireSelectExactly(2)
           .build()
  );

  // ── 14. 連絡先 ──
  form.addTextItem()
      .setTitle('ご連絡先（メールアドレスなど）')
      .setHelpText('載せる前に一度お見せしたいので、あると助かります。返事以外には使いません。')
      .setRequired(false);

  form.setConfirmationMessage(
    'ありがとうございました。持ち寄っていただいたものが、そのまま誰かの明日になります。\n' +
    '\n' +
    'こちらで確認のうえ「すぐ使える実践」に載せます。\n' +
    'ご連絡先をいただいた方には、載せる前に一度お見せします。\n' +
    '\n' +
    'すぐ使える実践： ' + SITE_URL + '#manabu'
  );

  var ss = SpreadsheetApp.create(FORM_JISSEN_MEI + '｜回答');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());

  return {
    url  : form.shortenFormUrl(form.getPublishedUrl()),
    edit : form.getEditUrl(),
    sheet: ss.getUrl()
  };
}


// ══════════════════════════════════════════════════════════
// 3. 通知メール（フォームを作ったあとに1回だけ実行する）
// ══════════════════════════════════════════════════════════

function 通知メールを付ける() {

  var mei = [FORM_IKEN_MEI, FORM_JISSEN_MEI];

  // 同じ通知を二重に付けないよう、古いものを外す
  var old = ScriptApp.getProjectTriggers();
  for (var i = 0; i < old.length; i++) {
    if (old[i].getHandlerFunction() === '回答が届いたとき') ScriptApp.deleteTrigger(old[i]);
  }

  for (var j = 0; j < mei.length; j++) {
    var files = DriveApp.getFilesByName(mei[j]);
    if (!files.hasNext()) {
      throw new Error('「' + mei[j] + '」が見つかりません。先に「フォームを2つ作る」を実行してください。');
    }
    var form = FormApp.openById(files.next().getId());
    ScriptApp.newTrigger('回答が届いたとき')
             .forForm(form)
             .onFormSubmit()
             .create();
    Logger.log('通知を付けました： ' + mei[j]);
  }

  Logger.log('回答が届くと ' + TSUUCHI_SAKI + ' にメールが飛びます。');
}


/** 通知の中身（自分では実行しない。上の仕掛けから呼ばれる） */
function 回答が届いたとき(e) {

  var mei    = e.source ? e.source.getTitle() : 'TOKKATSU広場のフォーム';
  var kotae  = e.response.getItemResponses();
  var honbun = ['「' + mei + '」に、回答が届きました。', ''];

  for (var i = 0; i < kotae.length; i++) {
    var item = kotae[i].getItem();
    var ans  = kotae[i].getResponse();
    honbun.push('■ ' + item.getTitle());
    if (ans instanceof Array) ans = ans.join('／');
    honbun.push(String(ans || '（未記入）'));
    honbun.push('');
  }

  honbun.push('――');
  if (mei === FORM_JISSEN_MEI) {
    honbun.push('実践を載せるには：');
    honbun.push('  1. src/jissen/ に  YYYY-MM-DD_すきな名前.md  を作る');
    honbun.push('  2. src/jissen/_テンプレート.md を写して、上の回答を上から順に入れる');
    honbun.push('  3. python3 build.py  と  python3 build.py --simple');
    honbun.push('  ※ 載せる前に、ご連絡先のある方には一度お見せする約束です。');
  } else {
    honbun.push('困りごとは、そのままは載せません。');
    honbun.push('同じものが集まったら、答えになる実践を「すぐ使える実践」に置きます。');
  }

  MailApp.sendEmail(
    TSUUCHI_SAKI,
    '[TOKKATSU広場] ' + mei + ' に回答が届きました',
    honbun.join('\n')
  );
}
