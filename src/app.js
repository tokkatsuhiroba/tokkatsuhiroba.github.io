(function(){
  'use strict';

  /* ══ 1. ことば ══ */
  var lang = window.__langPref || 'ja';
  var T = {
    ja:{ wd:['日','月','火','水','木','金','土'],
         month:function(y,m){return y+'年'+(m+1)+'月';},
         prev:'前の月', next:'次の月',
         ev:'研', dl:'〆',
         evL:'研究会・大会の当日', dlL:'申込の締切日',
         today:'今日', daysLeft:function(n){return n+'日';}, left:'あと',
         dayOf:function(d){return (d.getMonth()+1)+'月'+d.getDate()+'日';},
         deadlineOf:function(t){return t+'の申込〆切';},
         eventOf:function(t){return t+'（当日）';},
         todayLabel:function(d){return (d.getMonth()+1)+'月'+d.getDate()+'日（'+T.ja.wd[d.getDay()]+'）';} },
    ar:{ wd:['أحد','إثن','ثلا','أرب','خمي','جمع','سبت'],
         month:function(y,m){return ['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر'][m]+' '+y;},
         prev:'الشهر السابق', next:'الشهر التالي',
         ev:'لقاء', dl:'تسجيل',
         evL:'يوم انعقاد اللقاء', dlL:'آخر موعد للتسجيل',
         today:'اليوم', daysLeft:function(n){return n+' يوم';}, left:'متبقٍ',
         dayOf:function(d){return d.getDate()+'/'+(d.getMonth()+1);},
         deadlineOf:function(t){return 'آخر موعد للتسجيل: '+t;},
         eventOf:function(t){return t+'（يوم الانعقاد）';},
         todayLabel:function(d){return d.getDate()+' '+['يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر'][d.getMonth()];} }
  };
  function t(){ return T[lang]; }

  function applyLang(l){
    lang = l;
    var d = document.documentElement;
    d.setAttribute('data-lang', l);
    d.lang = (l==='ar') ? 'ar' : 'ja';
    d.dir  = (l==='ar') ? 'rtl' : 'ltr';
    document.querySelectorAll('[data-ar]').forEach(function(el){
      if(el.dataset.ja === undefined) el.dataset.ja = el.innerHTML;
      el.innerHTML = (l==='ar') ? el.dataset.ar : el.dataset.ja;
    });
    document.querySelectorAll('[data-ar-ph]').forEach(function(el){
      if(el.dataset.jaPh === undefined) el.dataset.jaPh = el.placeholder;
      el.placeholder = (l==='ar') ? el.dataset.arPh : el.dataset.jaPh;
    });
    if(window.__talkStage){
      var tk = document.querySelector('.talk');
      if(tk) window.__talkStage(+tk.dataset.stage || 1);
    }
    var lb = document.getElementById('langBtn');
    lb.textContent = (l==='ar') ? '日本語' : 'عربي';
    lb.lang = (l==='ar') ? 'ja' : 'ar';
    if(window.Store) Store.set('lang', l);
    paintSeg();
    renderAll();
  }

  /* ══ 2. 研究会のデータ（いまは見本。実データに差し替えて使う） ══ */
  /* 研究会の予定。出どころは各団体の公式サイト・公式配布物。
     日付を足すときは、この配列に1行足すだけでカレンダーに出ます。
     url を入れると「案内ページを開く」ボタンが有効になります。 */
  var EVENTS = [
    { ja:'第70回 全国研究協議大会', ar:'المؤتمر الوطني الـ70 لبحوث الأنشطة الخاصة',
      s_ja:'全特活 全国大会', s_ar:'المؤتمر الوطني',
      org_ja:'全国特別活動研究会', org_ar:'الجمعية الوطنية لبحوث الأنشطة الخاصة',
      venue:'', place_ja:'東京', place_ar:'طوكيو',
      about_ja:'2日間開催。650名を超える参加。過去の大会の資料も公式サイトから見られます。',
      days:['2026-08-07','2026-08-08'], deadline:'',
      apply_ja:'終了しました', url:'https://zentokkatsu.com/' },

    { ja:'夏の特活まつり', ar:'مهرجان توكاتسو الصيفي',
      s_ja:'都小特活 特活まつり', s_ar:'مهرجان الصيف',
      org_ja:'東京都小学校特別活動研究会（都小特活）', org_ar:'جمعية طوكيو لبحوث الأنشطة الخاصة (الابتدائي)',
      venue:'練馬区立豊玉小学校', place_ja:'東京都練馬区', place_ar:'نيريما، طوكيو',
      about_ja:'実践報告／講演（玉川大学TAPセンター 教授 川本和孝 先生）／4研究部ごとの実践交流会。参加費無料。',
      days:['2026-07-27'], deadline:'', apply_ja:'終了しました', url:'https://tosho-tokkatsu.tokyo/' },

    { ja:'学校行事部 検証授業（学芸会 事前指導）', ar:'درس تحقّق — قسم فعاليات المدرسة',
      s_ja:'都小特活 行事部', s_ar:'قسم الفعاليات',
      org_ja:'東京都小学校特別活動研究会（都小特活）', org_ar:'جمعية طوكيو لبحوث الأنشطة الخاصة (الابتدائي)',
      venue:'町田市立町田第三小学校', place_ja:'東京都町田市', place_ar:'ماتشيدا، طوكيو',
      about_ja:'2年 学芸会の事前指導／13:30〜　講師：全国小学校学校行事研究会 前会長 鈴木恒雄 先生',
      days:['2026-10-02'], deadline:'', apply_ja:'事前登録は不要です', url:'https://tosho-tokkatsu.tokyo/' },

    { ja:'学級活動部 検証授業（学級活動(1)）', ar:'درس تحقّق — قسم أنشطة الفصل',
      s_ja:'都小特活 学活部', s_ar:'قسم أنشطة الفصل',
      org_ja:'東京都小学校特別活動研究会（都小特活）', org_ar:'جمعية طوكيو لبحوث الأنشطة الخاصة (الابتدائي)',
      venue:'世田谷区立山野小学校', place_ja:'東京都世田谷区', place_ar:'سيتاغايا، طوكيو',
      about_ja:'6年 学級活動(1)／14:15〜　講師：帝京大学教育学部 教授 安部恭子 先生',
      days:['2026-10-09'], deadline:'', apply_ja:'事前登録は不要です', url:'https://tosho-tokkatsu.tokyo/' },

    { ja:'クラブ活動部 検証授業（ボッチャクラブ）', ar:'درس تحقّق — قسم الأندية',
      s_ja:'都小特活 クラブ部', s_ar:'قسم الأندية',
      org_ja:'東京都小学校特別活動研究会（都小特活）', org_ar:'جمعية طوكيو لبحوث الأنشطة الخاصة (الابتدائي)',
      venue:'江東区立浅間竪川小学校', place_ja:'東京都江東区', place_ar:'كوتو، طوكيو',
      about_ja:'ボッチャクラブ／14:10〜　講師：玉川大学 客員教授 赤羽根智 先生',
      days:['2026-10-27'], deadline:'', apply_ja:'事前登録は不要です', url:'https://tosho-tokkatsu.tokyo/' },

    { ja:'児童会活動部 検証授業（保健委員会）', ar:'درس تحقّق — قسم مجلس التلاميذ',
      s_ja:'都小特活 児童会部', s_ar:'قسم مجلس التلاميذ',
      org_ja:'東京都小学校特別活動研究会（都小特活）', org_ar:'جمعية طوكيو لبحوث الأنشطة الخاصة (الابتدائي)',
      venue:'北区立滝野川第四小学校', place_ja:'東京都北区', place_ar:'كيتا، طوكيو',
      about_ja:'保健委員会／14:20〜　講師：帝京大学教職センター 教授 佐野匡 先生',
      days:['2026-11-09'], deadline:'', apply_ja:'事前登録は不要です', url:'https://tosho-tokkatsu.tokyo/' },

    { ja:'学級活動部 検証授業（学級活動(1)）', ar:'درس تحقّق — قسم أنشطة الفصل',
      s_ja:'都小特活 学活部', s_ar:'قسم أنشطة الفصل',
      org_ja:'東京都小学校特別活動研究会（都小特活）', org_ar:'جمعية طوكيو لبحوث الأنشطة الخاصة (الابتدائي)',
      venue:'足立区立中川小学校', place_ja:'東京都足立区', place_ar:'أداتشي، طوكيو',
      about_ja:'4年 学級活動(1)／14:30〜　講師：國學院大學人間開発学部 教授 杉田洋 先生',
      days:['2026-11-12'], deadline:'', apply_ja:'事前登録は不要です', url:'https://tosho-tokkatsu.tokyo/' },

    { ja:'学校行事部 検証授業（音楽会 事後指導）', ar:'درس تحقّق — قسم فعاليات المدرسة',
      s_ja:'都小特活 行事部（多摩）', s_ar:'قسم الفعاليات (تاما)',
      org_ja:'東京都小学校特別活動研究会（都小特活）', org_ar:'جمعية طوكيو لبحوث الأنشطة الخاصة (الابتدائي)',
      venue:'多摩市立多摩第三小学校', place_ja:'東京都多摩市', place_ar:'تاما، طوكيو',
      about_ja:'5年 音楽会の事後指導／13:25〜　講師：玉川大学TAPセンター 教授 川本和孝 先生',
      days:['2026-11-30'], deadline:'', apply_ja:'事前登録は不要です', url:'https://tosho-tokkatsu.tokyo/' },

    { ja:'クラブ活動部 検証授業（科学クラブ）', ar:'درس تحقّق — قسم الأندية',
      s_ja:'都小特活 クラブ部', s_ar:'قسم الأندية',
      org_ja:'東京都小学校特別活動研究会（都小特活）', org_ar:'جمعية طوكيو لبحوث الأنشطة الخاصة (الابتدائي)',
      venue:'大田区立矢口東小学校', place_ja:'東京都大田区', place_ar:'أوتا، طوكيو',
      about_ja:'科学クラブ／14:15〜　講師：東京都小学校特別活動研究会 元会長 山口祐一 先生',
      days:['2026-12-03'], deadline:'', apply_ja:'事前登録は不要です', url:'https://tosho-tokkatsu.tokyo/' },

    { ja:'児童会活動部 検証授業（代表委員会）', ar:'درس تحقّق — قسم مجلس التلاميذ',
      s_ja:'都小特活 児童会部', s_ar:'قسم مجلس التلاميذ',
      org_ja:'東京都小学校特別活動研究会（都小特活）', org_ar:'جمعية طوكيو لبحوث الأنشطة الخاصة (الابتدائي)',
      venue:'昭島市立つつじが丘小学校', place_ja:'東京都昭島市', place_ar:'أكيشيما، طوكيو',
      about_ja:'代表委員会／14:15〜　講師：帝京大学教職センター 教授 佐野匡 先生',
      days:['2026-12-04'], deadline:'', apply_ja:'事前登録は不要です', url:'https://tosho-tokkatsu.tokyo/' }
  ];
  var SOURCES = [
    { url:'https://zentokkatsu.com/', ja:'全国特別活動研究会', ar:'الجمعية الوطنية لبحوث الأنشطة الخاصة' },
    { url:'https://jaseatokkatsu.jimdoweb.com/', ja:'日本特別活動学会', ar:'الجمعية اليابانية للأنشطة الخاصة' }
  ];
  function title(e){ return (lang==='ar') ? e.ar : e.ja; }
  function short(e){ return (lang==='ar') ? e.s_ar : e.s_ja; }
  function place(e){ return (lang==='ar') ? e.place_ar : e.place_ja; }
  function org(e){ return (lang==='ar') ? e.org_ar : e.org_ja; }
  function dayList(e){ return e.days || (e.event ? [e.event] : []); }
  function firstDay(e){ return dayList(e)[0]; }
  function esc(x){ return String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;'); }

  var TODAY = new Date(); TODAY.setHours(0,0,0,0);
  function parse(s){ var p=s.split('-'); return new Date(+p[0], +p[1]-1, +p[2]); }
  function key(d){ return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2); }
  function diffDays(d){ return Math.round((d - TODAY)/86400000); }

  /* 日付 → その日に立つ印 */
  function markMap(){
    var m = {};
    EVENTS.forEach(function(e){
      dayList(e).forEach(function(k){ (m[k] = m[k] || []).push({ type:'ev', e:e }); });
      if(e.deadline) (m[e.deadline] = m[e.deadline] || []).push({ type:'dl', e:e });
    });
    return m;
  }

  /* ══ 3. カレンダーを描く ══ */
  function buildCal(host, y, mo){
    var marks = markMap();
    var first = new Date(y, mo, 1), last = new Date(y, mo+1, 0);
    var html = '<div class="cal"><div class="cal-hd">' +
      '<button class="cal-nav" type="button" data-cal="-1">' + t().prev + '</button>' +
      '<p class="cal-title">' + t().month(y, mo) + '</p>' +
      '<button class="cal-nav" type="button" data-cal="1">' + t().next + '</button>' +
      '</div><div class="cal-grid">';
    t().wd.forEach(function(w){ html += '<div class="wd">' + w + '</div>'; });
    for(var i=0; i<first.getDay(); i++) html += '<div class="cal-cell"></div>';
    for(var d=1; d<=last.getDate(); d++){
      var date = new Date(y, mo, d), k = key(date);
      var isToday = (+date === +TODAY);
      var ms = marks[k] || [];
      var tag = ms.length ? 'button' : 'div';
      var attr = ms.length ? ' type="button" data-day="' + k + '"' : '';
      var aria = ms.length ? ' aria-label="' + esc(d + '　' + ms.map(function(m){
            return (m.type==='ev' ? t().eventOf(title(m.e)) : t().deadlineOf(title(m.e)));
          }).join('／')) + '"' : '';
      html += '<' + tag + ' class="cal-cell' + (isToday ? ' today' : '') + (ms.length ? ' has' : '') + '"' + attr + aria + '>' +
              '<span class="n">' + d + '</span>';
      ms.forEach(function(m){
        html += '<span class="mk ' + m.type + '">' +
                (m.type==='ev' ? t().ev : t().dl) + ' ' + esc(short(m.e)) + '</span>';
      });
      html += '</' + tag + '>';
    }
    var tail = (7 - ((first.getDay() + last.getDate()) % 7)) % 7;
    for(var j=0; j<tail; j++) html += '<div class="cal-cell"></div>';
    html += '</div></div>';
    host.innerHTML = html;
    host.dataset.y = y; host.dataset.m = mo;
    host.querySelectorAll('[data-cal]').forEach(function(b){
      b.addEventListener('click', function(){
        var n = mo + (+b.dataset.cal), ny = y;
        if(n < 0){ n = 11; ny--; } if(n > 11){ n = 0; ny++; }
        buildCal(host, ny, n);
      });
    });
    host.querySelectorAll('[data-day]').forEach(function(b){
      b.addEventListener('click', function(){
        host.querySelectorAll('.cal-cell').forEach(function(c){ c.classList.remove('sel'); });
        b.classList.add('sel');
        showDay(host, b.dataset.day);
      });
    });
  }

  /* その日に何があるかを、カレンダーの下に開く */
  function showDay(host, k){
    var box = document.getElementById(host.dataset.detail);
    if(!box) return;
    var ms = markMap()[k] || [];
    var d = parse(k);
    var L = (lang==='ar')
      ? { org:'الجهة المنظِّمة', venue:'المكان', addr:'الموقع', about:'المحتوى', day:'اليوم', apply:'التسجيل', open:'افتح صفحة الإعلان', src:'مصادر مواعيد اللقاءات：' }
      : { org:'主催', venue:'会場', addr:'所在地', about:'内容', day:'日程', apply:'申込', open:'主催団体のページを開く', src:'日程の出どころ：' };
    var html = ms.map(function(m){
      var e = m.e;
      var days = dayList(e).map(function(x){ return t().dayOf(parse(x)); }).join('・');
      if(e.deadline) days += '　' + t().dlL + '：' + t().dayOf(parse(e.deadline));
      var rows = '';
      function row(dt, dd){ if(dd) rows += '<dt>' + dt + '</dt><dd>' + esc(dd) + '</dd>'; }
      row(L.org, org(e));
      row(L.venue, e.venue || (lang==='ar' ? '—' : '公式サイトで確認'));
      row(L.addr, place(e));
      row(L.about, e.about_ja);
      row(L.day, days);
      row(L.apply, e.apply_ja);
      var link = e.url
        ? '<a class="btn wide" href="' + esc(e.url) + '" target="_blank" rel="noopener noreferrer">' + L.open + '</a>'
        : '<p class="none">' + (lang==='ar' ? 'لم تُسجَّل صفحة إعلان بعد.' : '案内ページはまだ登録されていません。') + '</p>';
      return '<div class="evbox">' +
        '<p class="k"><span class="kind ' + m.type + '">' + (m.type==='ev' ? t().ev : t().dl) + '</span>' +
          t().dayOf(d) + '</p>' +
        '<h3>' + esc(title(e)) + '</h3>' +
        '<dl>' + rows + '</dl>' + link +
      '</div>';
    }).join('');
    box.innerHTML = html + '<p class="none" style="margin-top:10px">' + L.src +
      SOURCES.map(function(x){
        return '<a href="' + x.url + '" target="_blank" rel="noopener noreferrer">' + (lang==='ar'?x.ar:x.ja) + '</a>';
      }).join('　') + '</p>';
    box.scrollIntoView({ block:'nearest', behavior:(window.matchMedia('(prefers-reduced-motion:reduce)').matches ? 'auto' : 'smooth') });
  }

  function legend(host){
    host.innerHTML =
      '<li><span class="mk ev">' + t().ev + '</span>' + t().evL + '</li>' +
      '<li><span class="mk dl">' + t().dl + '</span>' + t().dlL + '</li>';
  }

  /* ══ 4. 近いものを並べる（ホームの「いま気にすること」） ══ */
  function renderSoon(){
    var host = document.getElementById('soonList'); if(!host) return;
    var items = [];
    EVENTS.forEach(function(e){
      if(e.deadline) items.push({ kind:'dl', d:parse(e.deadline), e:e });
      dayList(e).forEach(function(x){ items.push({ kind:'ev', d:parse(x), e:e }); });
    });
    items = items.filter(function(i){ return diffDays(i.d) >= 0; })
                 .sort(function(a,b){ return a.d - b.d; })
                 .slice(0, 4);
    if(!items.length){
      host.innerHTML = '<li><span class="tx"><b>' +
        (lang==='ar' ? 'لا مواعيد قادمة مسجَّلة حاليًا.' : 'これから先の予定は、いまのところありません。') +
        '</b></span></li>';
      return;
    }
    host.innerHTML = items.map(function(i){
      var n = diffDays(i.d);
      var head = (n === 0) ? '<b>' + t().today + '</b>'
                           : '<b>' + n + '</b><span>' + (lang==='ar' ? t().daysLeft('').trim() : '日後') + '</span>';
      var what = (i.kind === 'dl') ? t().deadlineOf(title(i.e)) : title(i.e);
      var sub = t().dayOf(i.d) + '　' + (i.e.venue || place(i.e));
      return '<li class="' + i.kind + (n===0 ? ' today' : '') + '" data-open="' + firstDay(i.e) + '">' +
               '<span class="cd">' + head + '</span>' +
               '<span class="tx"><b>' + esc(what) + '</b><span>' + esc(org(i.e)) + '</span><span>' + esc(sub) + '</span></span>' +
             '</li>';
    }).join('');
  }

  /* ══ 5. カレンダーの下の一覧（文字でも読めるように） ══ */
  function renderList(){
    var host = document.getElementById('calList'); if(!host) return;
    host.innerHTML = EVENTS.map(function(e){
      var d0 = parse(firstDay(e)), n = diffDays(d0);
      var badge = (n > 0) ? t().left + ' ' + t().daysLeft(n) : (n === 0 ? t().today : (lang==='ar' ? 'انتهى' : '終了'));
      return '<li><a href="#hiroba" data-open="' + firstDay(e) + '"><span class="t">' + esc(title(e)) +
             '<span class="sub">' + esc(org(e)) + '</span>' +
             '<span class="sub">' + t().dayOf(d0) + '　' + esc(e.venue || place(e)) + '</span></span>' +
             '<span class="d">' + badge + '</span></a></li>';
    }).join('');
    host.querySelectorAll('[data-open]').forEach(function(a){
      a.addEventListener('click', function(ev){
        ev.preventDefault();
        jumpTo(a.dataset.open);
      });
    });
  }

  function jumpTo(k){
    var m = document.getElementById('mainCal');
    if(!m) return;
    var d = parse(k);
    buildCal(m, d.getFullYear(), d.getMonth());
    var cell = m.querySelector('[data-day="' + k + '"]');
    if(cell) cell.click();
  }

  function renderAll(){
    var h = document.getElementById('homeCal');
    var m = document.getElementById('mainCal');
    if(h) h.dataset.detail = 'homeDetail';
    if(m) m.dataset.detail = 'mainDetail';
    if(h) buildCal(h, +(h.dataset.y || TODAY.getFullYear()), +(h.dataset.m !== undefined ? h.dataset.m : TODAY.getMonth()));
    if(m) buildCal(m, +(m.dataset.y || TODAY.getFullYear()), +(m.dataset.m !== undefined ? m.dataset.m : TODAY.getMonth()));
    legend(document.getElementById('homeLegend'));
    legend(document.getElementById('mainLegend'));
    renderSoon();
    renderList();
    var soon = document.getElementById('soonList');
    if(soon) soon.querySelectorAll('[data-open]').forEach(function(li){
      li.style.cursor = 'pointer';
      li.addEventListener('click', function(){ location.hash = '#hiroba'; setTimeout(function(){ jumpTo(li.dataset.open); }, 60); });
    });
    var tl = document.getElementById('todayLabel');
    if(tl) tl.textContent = t().todayLabel(TODAY);
  }

  /* ══ 6. お悩み・サイクル図 → 学習過程の該当ステップを開く ══ */
  function openStep(n, scroll){
    var target = document.querySelector('.step[data-step="' + n + '"]');
    if(!target) return;
    document.querySelectorAll('.step').forEach(function(s){ s.open = (s === target); });
    document.querySelectorAll('.cycle .node').forEach(function(g){
      g.classList.toggle('on', g.dataset.step === String(n));
    });
    if(scroll){
      target.scrollIntoView({ block:'start', behavior:(window.matchMedia('(prefers-reduced-motion:reduce)').matches ? 'auto' : 'smooth') });
      target.querySelector('summary').focus();
    }
  }
  document.querySelectorAll('.cycle .node').forEach(function(g){
    function go(){ openStep(g.dataset.step, true); }
    g.addEventListener('click', go);
    g.addEventListener('keydown', function(e){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); go(); } });
  });
  document.querySelectorAll('.step').forEach(function(d){
    d.addEventListener('toggle', function(){
      if(d.open) document.querySelectorAll('.cycle .node').forEach(function(g){
        g.classList.toggle('on', g.dataset.step === d.dataset.step);
      });
    });
  });

  document.querySelectorAll('.nayami button').forEach(function(b){
    b.addEventListener('click', function(){ openStep(b.dataset.step, true); });
  });

  /* ══ 7. タブの切替 ══ */
  var PAGES = { home:'ホーム', news:'ニュース', manabu:'まなぶ', hiroba:'ひろば', my:'マイ' };
  var secs = document.querySelectorAll('[data-page]');
  var tabs = document.querySelectorAll('[data-tab]');
  var first = true;
  /* #manabu           … タブだけ
     #manabu/j-xxx     … タブの中の場所（実践1件・グッズ1点・節）。LINEに貼って直接ひらける */
  function route(){
    var raw = location.hash.replace(/^#/, '').split('/');
    var id = raw[0], at = raw[1] || '';
    if(!PAGES[id]){ id = 'home'; at = ''; }
    secs.forEach(function(s){
      var on = (s.dataset.page === id);
      s.classList.toggle('is-on', on);
      s.hidden = !on;
    });
    tabs.forEach(function(x){
      if(x.dataset.tab === id) x.setAttribute('aria-current','page');
      else x.removeAttribute('aria-current');
    });
    document.title = 'TOKKATSU広場｜' + PAGES[id];
    var el = at ? document.getElementById(at) : null;
    if(el){
      /* たたまれた中にあれば、ひらいてから行く */
      var d = el.tagName === 'DETAILS' ? el : (el.closest ? el.closest('details') : null);
      while(d){ d.open = true; d = d.parentElement ? d.parentElement.closest('details') : null; }
      var quick = window.matchMedia('(prefers-reduced-motion:reduce)').matches;
      setTimeout(function(){
        el.scrollIntoView({ block:'start', behavior:(quick ? 'auto' : 'smooth') });
        if(!el.hasAttribute('tabindex')) el.setAttribute('tabindex', '-1');
        el.focus({ preventScroll:true });
        el.classList.remove('hit'); void el.offsetWidth; el.classList.add('hit');
      }, first ? 150 : 30);
    }else if(!first){
      var cur = document.querySelector('[data-page="' + id + '"]');
      if(cur) cur.focus({ preventScroll:true });
      window.scrollTo(0, 0);
    }
    first = false;
  }
  window.addEventListener('hashchange', route);

  /* ══ 8. 設定のボタン ══ */
  function paintSeg(){
    var v = window.__view ? window.__view.get() : 'auto';
    document.querySelectorAll('[data-set-view]').forEach(function(b){
      var on = (b.dataset.setView === v);
      b.classList.toggle('on', on); b.setAttribute('aria-pressed', on);
    });
    document.querySelectorAll('[data-set-lang]').forEach(function(b){
      var on = (b.dataset.setLang === lang);
      b.classList.toggle('on', on); b.setAttribute('aria-pressed', on);
    });
  }
  document.querySelectorAll('[data-set-view]').forEach(function(b){
    b.addEventListener('click', function(){ if(window.__view) window.__view.set(b.dataset.setView); paintSeg(); });
  });
  document.querySelectorAll('[data-set-lang]').forEach(function(b){
    b.addEventListener('click', function(){ applyLang(b.dataset.setLang); });
  });
  document.getElementById('langBtn').addEventListener('click', function(){
    applyLang(lang === 'ar' ? 'ja' : 'ar');
  });

  /* ══ 8-2. 動画 ══
     ファイルを直接開いている（file://）ときは、YouTube側が埋め込みを拒むため
     埋め込まずに新しいタブで開く。https で配ったときだけページ内で再生する。 */
  var canEmbed = (location.protocol === 'http:' || location.protocol === 'https:');
  document.querySelectorAll('.yt').forEach(function(box){
    var b = box.querySelector('.ytbtn');
    if(!b) return;
    var id = box.dataset.yt;
    var watch = 'https://www.youtube.com/watch?v=' + id;
    if(!canEmbed){
      var note = box.querySelector('.ytalt');
      if(note){
        note.dataset.ja = '<a href="' + watch + '" target="_blank" rel="noopener noreferrer">YouTubeで開く（別のタブ）</a>' +
          '<br>※ ファイルを直接開いているため、ページの中では再生できません。';
        note.dataset.ar = '<a href="' + watch + '" target="_blank" rel="noopener noreferrer">افتح في YouTube</a>' +
          '<br>※ لا يمكن التشغيل داخل الصفحة عند فتح الملف مباشرة.';
        note.innerHTML = (lang==='ar') ? note.dataset.ar : note.dataset.ja;
      }
    }
    b.addEventListener('click', function(){
      if(!canEmbed){ window.open(watch, '_blank', 'noopener'); return; }
      var f = document.createElement('div');
      f.className = 'ytframe';
      f.innerHTML = '<iframe src="https://www.youtube.com/embed/' + id +
        '?rel=0&modestbranding=1" title="' + (b.querySelector('b').textContent) +
        '" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"' +
        ' referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>';
      box.replaceChild(f, b);
    });
  });

  /* ══ 8-3. 出し合う → くらべ合う → まとめる ══ */
  var CAP = {
    ja:{
      1:'<b>出し合う。</b>思いついたことを、ばらばらのまま全部出します。ここで良し悪しを言うと、次から出てこなくなります。',
      2:'<b>くらべ合う。</b>並べ直して、「にた考えはどれか」「提案理由に合うのはどれか」を見ます。ここが話合いの本体です。',
      3:'<b>まとめる。</b>1つに絞るのではなく、<b>折り合いをつけて</b>決めます。残った意見の良いところを入れると、決めたあとに動きます。'
    },
    ar:{
      1:'<b>نطرح.</b> نُخرج كل ما نفكر فيه دون ترتيب. الحكم المبكر يوقف الأصوات.',
      2:'<b>نقارن.</b> نعيد الترتيب ونسأل: أيّها متشابه؟ وأيّها يخدم سبب الاقتراح؟ هذه هي صُلب الحوار.',
      3:'<b>نقرّر.</b> لا نختار واحدًا فقط، بل <b>نتنازل قليلًا</b> وندمج ما يصلح من الباقي — عندها يتحرّك القرار فعلًا.'
    }
  };
  var talk = document.querySelector('.talk');
  if(talk){
    var cap = talk.querySelector('.talk-cap');
    var timer = null;
    function setStage(n){
      talk.dataset.stage = n;
      talk.querySelectorAll('[data-talk]').forEach(function(b){
        b.setAttribute('aria-pressed', b.dataset.talk === String(n));
      });
      cap.innerHTML = CAP[lang][n];
      cap.dataset.ja = CAP.ja[n]; cap.dataset.ar = CAP.ar[n];
    }
    talk.querySelectorAll('[data-talk]').forEach(function(b){
      b.addEventListener('click', function(){ clearTimeout(timer); setStage(+b.dataset.talk); });
    });
    talk.querySelector('.talk-play').addEventListener('click', function(){
      clearTimeout(timer);
      var quick = window.matchMedia('(prefers-reduced-motion:reduce)').matches;
      setStage(1);
      timer = setTimeout(function(){ setStage(2);
        timer = setTimeout(function(){ setStage(3); }, quick ? 900 : 1900);
      }, quick ? 900 : 1900);
    });
    window.__talkStage = setStage;
  }

  /* ══ 8-4. コピー（週案用のひとこと／実践のURL）。端末の中で完結し、外には何も送らない ══ */
  function copyText(txt, btn){
    function done(){
      var l = (lang==='ar') ? 'تم النسخ' : 'コピーしました';
      btn.classList.add('done'); btn.textContent = l;
      setTimeout(function(){
        btn.classList.remove('done');
        btn.innerHTML = (lang==='ar') ? btn.dataset.ar : (btn.dataset.ja !== undefined ? btn.dataset.ja : btn.dataset.orig);
      }, 1600);
    }
    function legacy(){
      var ta = document.createElement('textarea');
      ta.value = txt; ta.setAttribute('readonly', '');
      ta.style.position = 'fixed'; ta.style.top = '-1000px';
      document.body.appendChild(ta); ta.select();
      try{ if(document.execCommand('copy')) done(); }catch(e){}
      document.body.removeChild(ta);
    }
    if(navigator.clipboard && navigator.clipboard.writeText && (location.protocol === 'https:' || location.hostname === 'localhost')){
      navigator.clipboard.writeText(txt).then(done, legacy);
    }else legacy();
  }
  document.querySelectorAll('[data-copy],[data-copy-text]').forEach(function(b){
    b.dataset.orig = b.innerHTML;
    b.addEventListener('click', function(){
      var txt = b.dataset.copyText;
      if(!txt){ var src = document.getElementById(b.dataset.copy); txt = src ? src.textContent.trim() : ''; }
      if(txt) copyText(txt, b);
    });
  });

  /* ══ 9. ストックの見た目（保存は Step 2） ══ */
  document.querySelectorAll('.stock').forEach(function(b){
    b.addEventListener('click', function(){
      var on = b.classList.toggle('on');
      b.setAttribute('aria-pressed', on);
      if(b.dataset.ja !== undefined){
        b.dataset.ja = on ? 'ストック済み' : 'ストック';
        b.dataset.ar = on ? 'محفوظ' : 'حفظ';
      }
      b.textContent = (lang==='ar') ? (on ? 'محفوظ' : 'حفظ') : (on ? 'ストック済み' : 'ストック');
    });
  });

  /* ══ 10. はじめる ══ */
  route();
  if(lang === 'ar') applyLang('ar'); else { paintSeg(); renderAll(); }
})();
