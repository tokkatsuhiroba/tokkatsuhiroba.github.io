// All coordinates refer to the original SVG school panorama with refined mascot leaders.
const scenes={
 all:{box:'0 250 3200 950',tint:'#ead78d',label:'校舎と校庭の全景。学級会、運動会、児童会、クラブ活動と学校の日常。'},
 class:{box:'30 865 740 335',tint:'#dcebd6',label:'学級会。黒板と机を囲んで、手を挙げたり話を聞いたりする子どもたち。'},
 events:{box:'790 765 960 435',tint:'#f9dfcd',label:'運動会。旗を持つ行人、校庭を走ったり玉入れをしたりする仲間。'},
 council:{box:'1720 775 700 425',tint:'#dceaf4',label:'児童会の集会。たすきとマイクの児童会ちゃんが、集まった仲間に呼びかける。'},
 club:{box:'2390 775 810 425',tint:'#f7edbd',label:'クラブ活動。絵、科学、太鼓、運動。それぞれの好きなことに取り組む仲間。'}
};
function showScene(key){
 const config=scenes[key];if(!config)return;
 const svg=document.getElementById('world-image');
 svg.setAttribute('viewBox',config.box);svg.setAttribute('aria-label',config.label);
 document.getElementById('world').style.setProperty('--chosen',config.tint);
 document.querySelectorAll('[data-scene]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.scene===key)));
 document.getElementById('scene-status').textContent=config.label;
}
document.querySelectorAll('[data-scene]').forEach(button=>button.addEventListener('click',()=>showScene(button.dataset.scene)));
let opener=null;
document.querySelectorAll('[data-dialog]').forEach(button=>button.addEventListener('click',()=>{opener=button;document.getElementById(button.dataset.dialog).showModal();}));
document.querySelectorAll('[data-close]').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));
document.querySelectorAll('dialog').forEach(dialog=>{
 dialog.addEventListener('close',()=>opener?.focus());
 dialog.addEventListener('click',event=>{if(event.target!==dialog)return;const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();});
});
