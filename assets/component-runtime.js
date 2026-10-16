/* Local compatibility components for exported layout code. No network APIs. */
(() => {
  'use strict';
  const {h, Fragment, createContext} = preact;
  const hooks = preactHooks;
  const md = markdownit({html:false,breaks:true,linkify:false});
  const colors = {default:'#0f172a',secondary:'#64748b',tertiary:'#94a3b8',success:'#15803d',danger:'#dc2626',warning:'#b45309',primary:'#0f766e',strong:'#475569',subtle:'#e2e8f0','surface-secondary':'#f5f6f8','surface-primary':'#ffffff','surface-tertiary':'#eef0f3'};
  const sizes = {xs:12,sm:14,md:16,lg:19,xl:22,'2xl':28,'3xl':34};
  const align = {start:'flex-start',end:'flex-end',center:'center',between:'space-between',around:'space-around',evenly:'space-evenly',stretch:'stretch'};
  const color = v => colors[v] || v;
  const space = v => typeof v === 'number' ? v*4+'px' : v;
  const literal = text => ({__mdfigLiteral:text});
  const isLiteral = value => value && typeof value === 'object' && '__mdfigLiteral' in value;
  const flattened = items => items.flat(Infinity).filter(v=>v!==null&&v!==undefined&&v!==false);
  function markdown(text, block=false) {
    text = text.replace(/^\s*\n/,'').replace(/\n\s*$/,'');
    if(!text.trim()) return null;
    if(text.includes('\n')) text=text.split('\n').map(line=>line.replace(/^ {1,6}/,'')).join('\n');
    const tag=block?'div':'span';
    return h(tag,{class:'mdfig-markdown',dangerouslySetInnerHTML:{__html:block?md.render(text):md.renderInline(text.trim())}});
  }
  function content(children, block=false) {
    return flattened(children).map(child => isLiteral(child)?markdown(child.__mdfigLiteral,block):typeof child==='string'?markdown(child,block):child);
  }
  function styleFor(p, base={}) {
    const s={...base};
    for(const key of ['padding','gap','margin']) if(p[key]!==undefined)s[key]=space(p[key]);
    for(const [key, sides] of Object.entries({px:['paddingLeft','paddingRight'],py:['paddingTop','paddingBottom'],mx:['marginLeft','marginRight'],my:['marginTop','marginBottom']}))
      if(p[key]!==undefined)for(const side of sides)s[side]=space(p[key]);
    for(const key of ['width','height','minWidth','maxWidth','minHeight','maxHeight']) if(p[key]!==undefined)s[key]=typeof p[key]==='number'?p[key]+'px':p[key];
    if(p.border){const b=typeof p.border==='object'?p.border:{};s.border=`${b.size||1}px solid ${color(b.color||'subtle')}`;}
    if(p.radius)s.borderRadius=({sm:4,md:6,lg:10,xl:14,full:999}[p.radius]||p.radius)+'px';
    if(p.background)s.background=color(p.background);
    if(p.color)s.color=color(p.color);
    if(p.size)s.fontSize=(sizes[p.size]||16)+'px';
    if(p.weight)s.fontWeight=({normal:400,medium:500,semibold:600,bold:700}[p.weight]||p.weight);
    if(p.align)s.alignItems=align[p.align]||p.align;
    if(p.justify)s.justifyContent=align[p.justify]||p.justify;
    if(p.wrap)s.flexWrap=p.wrap===true?'wrap':p.wrap;
    if(p.textAlign)s.textAlign=p.textAlign;
    if(p.tabularNums)s.fontVariantNumeric='tabular-nums';
    if(p.preserveWhitespace)s.whiteSpace='pre-wrap';
    if(typeof p.style==='string'){
      const el=document.createElement('span');el.style.cssText=p.style;
      for(const key of el.style)s[key]=el.style.getPropertyValue(key);
    }else if(p.style)Object.assign(s,p.style);
    return s;
  }
  function propsFor(p, base={}) {
    return {id:p.id,class:['mdfig-component',p.class||p.className||''].join(' '),style:styleFor(p,base),title:p.title};
  }
  const groupContext=createContext(null);
  function RadioGroup(p) {
    return h(groupContext.Provider,{value:{value:p.value,onChange:p.onChange}},h('div',{...propsFor(p,{display:'flex',flexDirection:p.direction==='row'?'row':'column',gap:'10px'}),role:'radiogroup'},content(p.children)));
  }
  function Radio(p) {
    const group=hooks.useContext(groupContext);
    return h('label',{...propsFor(p,{display:'flex',alignItems:'center',gap:'9px',cursor:'pointer'})},
      h('input',{type:'radio',value:p.value,checked:group?.value===p.value,onChange:()=>group?.onChange?.(p.value)}),content(p.children));
  }
  const icons={
    'arrow-down':['M12 4v16','m5 13 7 7 7-7'],
    'arrow-right':['M4 12h16','m13 5 7 7-7 7'],
    'copy':['M8 8h12v12H8z','M16 8V4H4v12h4'],
    'check':['m5 12 4 4L19 6'],
    'waves':['M2 6q3-4 6 0t6 0t6 0','M2 12q3-4 6 0t6 0t6 0','M2 18q3-4 6 0t6 0t6 0'],
    'scan-search':['M3 8V3h5','M16 3h5v5','M21 16v5h-5','M8 21H3v-5','M16 16l3 3','M15 11a4 4 0 1 1-8 0 4 4 0 0 1 8 0'],
    'chart-no-axes-combined':['M3 19l5-6 4 2 8-10','M4 9v10','M10 7v4','M16 12v7','M22 3v16'],
    'cpu':['M6 6h12v12H6z','M9 9h6v6H9z','M9 2v4m6-4v4M9 18v4m6-4v4M2 9h4m-4 6h4m12-6h4m-4 6h4'],
    'info':['M12 10v7','M12 7h.01','M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0'],
    'chevron-down':['m6 9 6 6 6-6']
  };
  function Icon(p){
    if(!icons[p.name])throw Error('尚不支持图标：'+p.name);
    return h('svg',{'data-mdfig-icon':p.name,viewBox:'0 0 24 24',width:p.size==='xs'?14:18,height:p.size==='xs'?14:18,fill:'none',stroke:color(p.color||'secondary'),'stroke-width':1.7,'stroke-linecap':'round','stroke-linejoin':'round',style:{flexShrink:0}},icons[p.name].map(d=>h('path',{d})));
  }
  const components={
    box:p=>h('div',propsFor(p,{display:'flex',flexDirection:'column',minWidth:0}),content(p.children)),
    row:p=>h('div',propsFor(p,{display:'flex',alignItems:'center',minWidth:0}),content(p.children)),
    grid:p=>h('div',{...propsFor(p,{display:'grid',gridTemplateColumns:`repeat(${Number(p.columns)||2},minmax(0,1fr))`,minWidth:0}),'data-mdfig-grid':p.columns||2},content(p.children)),
    'grid-item':p=>h('div',propsFor(p,{minWidth:0}),content(p.children)),
    text:p=>h('span',propsFor(p,{lineHeight:1.65}),p.preserveWhitespace?flattened(p.children).map(v=>isLiteral(v)?v.__mdfigLiteral:v):content(p.children)),
    title:p=>h('div',propsFor(p,{fontSize:'19px',fontWeight:600,lineHeight:1.4}),content(p.children)),
    caption:p=>h('div',propsFor(p,{color:colors.secondary,fontSize:'13px',lineHeight:1.6}),content(p.children)),
    badge:p=>h('span',propsFor(p,{display:'inline-flex',alignItems:'center',alignSelf:'flex-start',borderRadius:'6px',padding:'3px 8px',fontSize:'12px',fontWeight:500,lineHeight:1.5,background:p.color==='success'?'#edf9ef':'#f1f3f5',color:color(p.color||'secondary'),whiteSpace:'normal'}),content(p.children)),
    divider:p=>h('hr',{...propsFor(p,{border:0,borderTop:'1px solid '+color(p.color||'subtle'),margin:0,width:'100%',flexShrink:0})}),
    button:p=>h('button',{...propsFor(p,{display:'inline-flex',alignItems:'center',gap:'5px',alignSelf:'flex-start',border:'1px solid #d1d5db',borderRadius:'7px',padding:'6px 10px',background:'#fff',fontSize:'13px',fontFamily:'inherit'}),type:'button',onClick:p.onClick},content(p.children)),
    list:p=>h(p.marker==='number'?'ol':'ul',propsFor(p,{display:'flex',flexDirection:'column',margin:0,paddingLeft:'24px'}),content(p.children)),
    'list-item':p=>h('li',propsFor(p),content(p.children)),
    'radio-group':RadioGroup,radio:Radio,icon:Icon,
    'writing-block':p=>h('div',propsFor(p,{border:'1px solid #e2e8f0',borderRadius:'12px',padding:'18px',lineHeight:1.8}),content(p.children,true)),
    'app-block':p=>h('div',propsFor(p,{minWidth:0}),content(p.children)),
    'mdfig-cite':()=>null,'mdfig-memory-cite':()=>null
  };
  const nativeTags=new Set('a abbr address article aside b bdi bdo blockquote br caption cite code col colgroup dd del details dfn div dl dt em figcaption figure footer h1 h2 h3 h4 h5 h6 header hr i img input kbd label legend li link main mark nav ol p pre q s samp section small source span strong style sub summary sup table tbody td textarea tfoot th thead time tr u ul var video wbr svg g path circle ellipse line polyline polygon rect text tspan textPath defs marker pattern linearGradient radialGradient stop clipPath mask use symbol foreignObject filter feGaussianBlur title desc'.split(' '));
  const svgTags=new Set('svg g path circle ellipse line polyline polygon rect tspan textPath defs marker pattern linearGradient radialGradient stop clipPath mask use symbol foreignObject filter feGaussianBlur desc'.split(' '));
  function factory(tag,p,...children) {
    p=p||{};
    if(typeof tag!=='string')return h(tag,p,...content(children));
    const forcedSvg=tag==='mdfig-svg-text'||tag==='mdfig-svg-title';
    if(forcedSvg)tag=tag==='mdfig-svg-text'?'text':'title';
    const isSvgText=forcedSvg||tag==='text'&&('x' in p||'y' in p||'textAnchor' in p||'text-anchor' in p);
    if(components[tag]&&!isSvgText)return h(components[tag],{...p,children});
    if(!nativeTags.has(tag))throw Error('尚不支持组件：<'+tag+'>，已保留原代码');
    if(svgTags.has(tag)||isSvgText){
      const attrs={};
      for(const [k,v] of Object.entries(p))attrs[/^(stroke|fill|font|text|dominant|stop|clip)[A-Z]/.test(k)?k.replace(/[A-Z]/g,c=>'-'+c.toLowerCase()):k]=v;
      return h(tag,attrs,...flattened(children).map(v=>isLiteral(v)?v.__mdfigLiteral.trim():v));
    }
    return h(tag,p,...content(children));
  }
  window.DIL={...hooks,h:factory,Fragment,literal};
  window.GenUI={copy:async text=>{window.__mdfigClipboardText=String(text);}};
  window.__mdfigCompile=(source)=>{
    const plugin=({types:t})=>({visitor:{
      JSXElement(path){
        const name=path.node.openingElement.name;
        if(!t.isJSXIdentifier(name)||!['text','title'].includes(name.name))return;
        let parent=path.parentPath;
        while(parent){
          if(parent.isJSXElement()){
            const ancestor=parent.node.openingElement.name.name;
            if(ancestor==='foreignObject')break;
            if(ancestor==='svg'){
              const mapped='mdfig-svg-'+name.name;
              path.node.openingElement.name=t.jsxIdentifier(mapped);
              if(path.node.closingElement)path.node.closingElement.name=t.jsxIdentifier(mapped);
              break;
            }
          }
          parent=parent.parentPath;
        }
      },
      JSXText(path){
        path.replaceWith(t.jsxExpressionContainer(t.callExpression(t.memberExpression(t.identifier('DIL'),t.identifier('literal')),[t.stringLiteral(path.node.value)])));
      }
    }});
    const output=Babel.transform(source,{plugins:[plugin,['transform-react-jsx',{pragma:'DIL.h',pragmaFrag:'DIL.Fragment',throwIfNamespace:false}]],sourceType:'script',compact:true}).code;
    (0,eval)(output);
  };
})();
