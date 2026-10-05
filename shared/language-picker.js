/* One disclosure for every page. Page dictionaries decide which languages exist.
   Flags are SVG files so Windows does not replace flag emoji with country letters. */
(()=>{
  const LANGUAGES={
    ko:{name:'한국어',flag:'/assets/language/kr.svg'},
    en:{name:'English',flag:'/assets/language/us.svg'}
  };
  const mounted=new WeakMap();
  function label(node,language){
    node.replaceChildren();
    if(LANGUAGES[language.code]?.flag){
      const img=document.createElement('img');
      img.src=LANGUAGES[language.code].flag;img.alt='';img.className='lp-flag';
      img.width=24;img.height=18;img.setAttribute('aria-hidden','true');
      node.appendChild(img);
    }
    const name=document.createElement('span');
    name.textContent=language.name;name.lang=language.code;node.appendChild(name);
  }
  function mount(host,config){
    if(!host)return;
    let state=mounted.get(host);
    const languages=(config.languages||options(['ko','en'])).slice().sort((a,b)=>
      (a.code==='ko'?0:a.code==='en'?1:2)-(b.code==='ko'?0:b.code==='en'?1:2));
    const key=JSON.stringify(languages);
    if(!state){
      const details=document.createElement('details');details.className='language-picker';
      const summary=document.createElement('summary');summary.className='lp-trigger';
      const current=document.createElement('span');current.className='lp-current';
      const arrow=document.createElement('span');arrow.className='lp-arrow';arrow.setAttribute('aria-hidden','true');
      summary.append(current,arrow);
      const list=document.createElement('ul');list.className='lp-options';
      details.append(summary,list);host.replaceChildren(details);
      state={details,summary,current,list,key:null,lang:null,onChange:null};mounted.set(host,state);
      details.addEventListener('keydown',event=>{
        if(event.key==='Escape'&&details.open){event.preventDefault();details.open=false;summary.focus();}
      });
      document.addEventListener('click',event=>{if(!details.contains(event.target))details.open=false;});
      details.addEventListener('focusout',event=>{if(!details.contains(event.relatedTarget))details.open=false;});
    }
    state.onChange=config.onChange;
    if(key!==state.key){
      state.list.replaceChildren();
      for(const language of languages){
        const item=document.createElement('li'),button=document.createElement('button');
        button.type='button';button.dataset.languageOption=language.code;button.setAttribute('aria-label',language.name);label(button,language);
        const check=document.createElement('span');check.className='lp-check';check.textContent='✓';check.setAttribute('aria-hidden','true');button.appendChild(check);
        button.addEventListener('click',()=>{
          state.details.open=false;
          if(language.code!==state.lang)state.onChange(language.code);
          state.summary.focus();
        });
        item.appendChild(button);state.list.appendChild(item);
      }
      state.key=key;
    }
    const selected=languages.find(language=>language.code===config.lang)||languages[0];
    if(!selected)return;
    if(state.lang!==selected.code){label(state.current,selected);state.details.open=false;}
    state.lang=selected.code;
    state.summary.setAttribute('aria-label',(config.lang==='ko'?'언어 선택: ':'Select language: ')+selected.name);
    state.list.querySelectorAll('button').forEach(button=>{
      button.setAttribute('aria-current',String(button.dataset.languageOption===selected.code));
    });
  }
  function options(codes){return codes.map(code=>({code,name:LANGUAGES[code]?.name||code}));}
  window.LanguagePicker={mount,options};
})();
