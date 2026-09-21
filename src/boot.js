/* 表示モードと言語を、描いてしまう前に決める。保存は storage.js の中だけ。 */
(function(){
  var d=document.documentElement, mq=window.matchMedia('(min-width:900px)');
  d.className='js';
  var view=(window.Store&&Store.get('view'))||'auto';
  var lang=(window.Store&&Store.get('lang'))||'ja';
  function applyView(){
    var pc=(view==='pc')||(view==='auto'&&mq.matches);
    d.setAttribute('data-w',pc?'pc':'sp');
    d.setAttribute('data-view',view);
  }
  d.setAttribute('data-lang',lang);
  d.lang=(lang==='ar')?'ar':'ja';
  d.dir=(lang==='ar')?'rtl':'ltr';
  window.__view={get:function(){return view;},set:function(v){view=v;if(window.Store)Store.set('view',v);applyView();},apply:applyView};
  window.__langPref=lang;
  applyView();
  function onchange(){ if(view==='auto') applyView(); }
  if(mq.addEventListener) mq.addEventListener('change',onchange); else if(mq.addListener) mq.addListener(onchange);
  window.addEventListener('resize',onchange);
  window.addEventListener('orientationchange',onchange);
})();
