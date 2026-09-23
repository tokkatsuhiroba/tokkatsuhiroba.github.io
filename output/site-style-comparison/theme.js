const themeConfig={
  three:{world:'#asset-world-3d',worldBox:'0 0 1942 809',mascots:'#asset-mascots-3d',crops:['0 80 432 684','432 30 455 734','887 100 430 664','1317 80 457 684'],label:'立体キャラクター版'},
  pixel:{world:'#asset-pixel',worldBox:'0 384 1536 640',mascots:'#asset-pixel',crops:['0 24 384 344','384 24 384 344','768 24 384 344','1152 24 384 344'],label:'ドット絵版'}
};
function setTheme(key){
  const config=themeConfig[key];
  if(!config)return;
  document.body.dataset.theme=key;
  document.querySelectorAll('[data-style]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.style===key)));
  document.getElementById('world-image').setAttribute('viewBox',config.worldBox);
  document.getElementById('world-use').setAttribute('href',config.world);
  document.querySelectorAll('[data-avatar-index]').forEach(svg=>{
    svg.setAttribute('viewBox',config.crops[Number(svg.dataset.avatarIndex)]);
    svg.querySelector('use').setAttribute('href',config.mascots);
  });
  document.getElementById('style-status').textContent=config.label+'を表示中。同じ内容で見比べられます。';
  document.title='TOKKATSU広場｜'+config.label+'・デザイン比較';
}
document.querySelectorAll('[data-style]').forEach(button=>button.addEventListener('click',()=>setTheme(button.dataset.style)));
setTheme(new URLSearchParams(location.search).get('style')||'three');
