/* 特活広場｜保存はここだけ。localStorage 以外は触らない。
   将来ネイティブ化するときは、このファイルの中だけを差し替える。
   扱うキー：stock / memo / read / mode / view / yaritai / lang                      */
(function (g) {
  'use strict';
  var NS = 'tokkatsu.';
  var fallback = {};          // localStorage が使えない端末のための一時置き場
  var usable = (function () {
    try {
      var k = NS + '__test';
      localStorage.setItem(k, '1');
      localStorage.removeItem(k);
      return true;
    } catch (e) { return false; }
  })();

  function raw(key) {
    if (!usable) return (key in fallback) ? fallback[key] : null;
    try { return localStorage.getItem(NS + key); } catch (e) { return null; }
  }

  var Store = {
    usable: usable,

    get: function (key, dflt) {
      var v = raw(key);
      if (v === null || v === undefined) return (dflt === undefined ? null : dflt);
      try { return JSON.parse(v); } catch (e) { return v; }
    },

    set: function (key, value) {
      var v = (typeof value === 'string') ? value : JSON.stringify(value);
      if (!usable) { fallback[key] = v; return true; }
      try { localStorage.setItem(NS + key, v); return true; }
      catch (e) { fallback[key] = v; return false; }   // 容量超過でも落とさない
    },

    remove: function (key) {
      delete fallback[key];
      if (!usable) return;
      try { localStorage.removeItem(NS + key); } catch (e) {}
    },

    /* マイタブの「書き出し」用。Obsidian にそのまま貼れるテキストにする */
    dump: function () {
      var keys = ['mode', 'view', 'stock', 'memo', 'read'], out = ['# 特活広場 書き出し'];
      keys.forEach(function (k) {
        var v = Store.get(k);
        if (v === null) return;
        out.push('', '## ' + k, (typeof v === 'string') ? v : JSON.stringify(v, null, 2));
      });
      return out.join('\n');
    }
  };

  g.Store = Store;
})(window);
