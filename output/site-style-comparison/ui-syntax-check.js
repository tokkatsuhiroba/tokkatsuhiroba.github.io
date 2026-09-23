
const sceneConfig={all:{origin:'50% 70%',tint:'#edf4eb',alt:'4人のキャラクターと多くの仲間が過ごす学校の遠景。学級会・運動会・児童会・クラブ活動と日常の小さな場面がつながる広場。'},class:{origin:'9% 76%',tint:'#e5efe5',alt:'学活くんと学級会。黒板と机を囲んで話し合う仲間たち。'},events:{origin:'39% 71%',tint:'#f8e4da',alt:'行人と運動会。旗で応援しながら、仲間がリレーをする場面。'},council:{origin:'65% 72%',tint:'#e2edf5',alt:'児童会ちゃんの集会。マイクで呼びかけ、仲間が参加する場面。'},club:{origin:'96% 75%',tint:'#fbf0c9',alt:'クラブマンとクラブ活動。絵を描いたり模型を作ったりする場面。'}};
document.querySelectorAll('[data-scene]').forEach(button=>button.addEventListener('click',()=>{const key=button.dataset.scene;const config=sceneConfig[key];document.querySelectorAll('[data-scene]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));const world=document.getElementById('world');world.classList.toggle('zoomed',key!=='all');world.style.setProperty('--origin',config.origin);world.style.setProperty('--chosen',config.tint);document.getElementById('world-image').setAttribute('aria-label',config.alt);}));
let opener=null;
document.querySelectorAll('[data-dialog]').forEach(button=>button.addEventListener('click',()=>{opener=button;document.getElementById(button.dataset.dialog).showModal();}));
document.querySelectorAll('[data-close]').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));
document.querySelectorAll('dialog').forEach(dialog=>{dialog.addEventListener('close',()=>opener?.focus());dialog.addEventListener('click',event=>{if(event.target!==dialog)return;const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();});});
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

