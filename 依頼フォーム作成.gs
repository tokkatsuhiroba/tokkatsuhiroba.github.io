/**
 * TOKKATSU広場｜ご依頼・修正フォームを作るスクリプト
 * ------------------------------------------------------------
 * 使い方
 *   1. https://script.google.com/ を開く → 「新しいプロジェクト」
 *   2. 中身をぜんぶ消して、このファイルの中身を貼りつける
 *   3. 上の関数の選択で「フォームを作る」を選び、▶ 実行
 *   4. 最初の1回だけ承認を求められる（自分のアカウントを選び「許可」）
 *   5. 下の「実行ログ」に、公開URLと編集URLが出る。公開URLをサイトに貼る
 *
 *   ★「通知メールを付ける」は、フォームを作ったあとに1回だけ実行する。
 *     回答が届くたびに、下の TSUUCHI_SAKI へメールが飛ぶようになる。
 */

// ── ここだけ書きかえれば使える ──────────────────────────
var FORM_MEI   = 'TOKKATSU広場｜ご依頼・修正フォーム';
var SITE_URL   = 'https://tokkatsuhiroba.github.io/';
var TSUUCHI_SAKI = 'yuutennis657@gmail.com';
// ────────────────────────────────────────────────────


function フォームを作る() {

  var form = FormApp.create(FORM_MEI);

  form.setDescription(
    'TOKKATSU広場（' + SITE_URL + '）への、ご依頼・修正のお願いです。\n' +
    '\n' +
    '・無記名でも構いません。\n' +
    '・掲載をやめてほしいというご依頼は、1週間以内に反映します。\n' +
    '・このフォームの回答は、サイトの運営以外には使いません。'
  );

  // 誰でも書ける状態にする
  // ※ setRequireLogin は Workspace 専用。個人のGmailでは使えない（もともとログイン不要）
  form.setCollectEmail(false);
  form.setAllowResponseEdits(false);
  form.setProgressBar(false);

  // ── 1. お名前 ──
  form.addTextItem()
      .setTitle('お名前')
      .setHelpText('無記名でも構いません。')
      .setRequired(false);

  // ── 2. ご連絡先 ──
  form.addTextItem()
      .setTitle('ご連絡先（メールアドレスなど）')
      .setHelpText('返事が必要なときだけで大丈夫です。')
      .setRequired(false);

  // ── 3. 種類（必須・その他あり）──
  var shurui = form.addMultipleChoiceItem();
  shurui.setTitle('どれについてのご連絡ですか')
        .setChoices([
          shurui.createChoice('ニュースの内容がちがう'),
          shurui.createChoice('リンクが切れている'),
          shurui.createChoice('掲載をやめてほしい'),
          shurui.createChoice('こんな機能がほしい'),
          shurui.createChoice('研究会の情報を載せてほしい')
        ])
        .showOtherOption(true)
        .setRequired(true);

  // ── 4. 該当のページ ──
  form.addTextItem()
      .setTitle('該当のページ・記事')
      .setHelpText('分かる範囲で大丈夫です。URLでも、見出しの文字でもかまいません。')
      .setRequired(false);

  // ── 5. 内容（必須）──
  form.addParagraphTextItem()
      .setTitle('内容')
      .setHelpText('できるだけ具体的に書いていただけると助かります。')
      .setRequired(true);

  form.setConfirmationMessage(
    'お送りいただき、ありがとうございました。\n' +
    '掲載の取り下げのご依頼は、1週間以内に反映します。'
  );

  // 回答をスプレッドシートに貯める
  var ss = SpreadsheetApp.create(FORM_MEI + '｜回答');
  form.setDestination(FormApp.DestinationType.SPREADSHEET, ss.getId());

  Logger.log('── できました ──');
  Logger.log('公開URL（サイトに貼るのはこちら）： ' + form.getPublishedUrl());
  Logger.log('短縮URL： ' + form.shortenFormUrl(form.getPublishedUrl()));
  Logger.log('編集URL（自分用）： ' + form.getEditUrl());
  Logger.log('回答シート： ' + ss.getUrl());
}


/**
 * 回答が届いたらメールで知らせる（フォームを作ったあとに1回だけ実行する）
 * 実行すると、いま自分のドライブにある同じ名前のフォームに通知を仕込む。
 */
function 通知メールを付ける() {

  var files = DriveApp.getFilesByName(FORM_MEI);
  if (!files.hasNext()) {
    throw new Error('「' + FORM_MEI + '」が見つかりません。先に「フォームを作る」を実行してください。');
  }
  var form = FormApp.openById(files.next().getId());

  // 同じ通知を二重に付けないよう、古いものを外す
  var old = ScriptApp.getProjectTriggers();
  for (var i = 0; i < old.length; i++) {
    if (old[i].getHandlerFunction() === '回答が届いたとき') ScriptApp.deleteTrigger(old[i]);
  }

  ScriptApp.newTrigger('回答が届いたとき')
           .forForm(form)
           .onFormSubmit()
           .create();

  Logger.log('通知メールを ' + TSUUCHI_SAKI + ' に送るようにしました。');
}


/** 通知の中身（自分では実行しない。上の仕掛けから呼ばれる） */
function 回答が届いたとき(e) {

  var kotae = e.response.getItemResponses();
  var honbun = ['TOKKATSU広場のフォームに、回答が届きました。', ''];

  for (var i = 0; i < kotae.length; i++) {
    honbun.push('■ ' + kotae[i].getItem().getTitle());
    honbun.push(kotae[i].getResponse() || '（未記入）');
    honbun.push('');
  }
  honbun.push('――');
  honbun.push('掲載の取り下げのご依頼なら、1週間以内に反映すると約束しています。');

  MailApp.sendEmail(
    TSUUCHI_SAKI,
    '[TOKKATSU広場] フォームに回答が届きました',
    honbun.join('\n')
  );
}
