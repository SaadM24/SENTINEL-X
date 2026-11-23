"use strict";
const $ = id => document.getElementById(id);
const make = (tag, value, cls) => {
  const element = document.createElement(tag);
  if (value !== undefined) element.textContent = value;
  if (cls) element.className = cls;
  return element;
};
const svg = (tag, attrs) => {
  const element = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [key, value] of Object.entries(attrs)) element.setAttribute(key, value);
  return element;
};
const svgText = (parent, x, y, text, size=12, anchor="start") => {
  const t = svg("text", {x,y,"font-size":size,"text-anchor":anchor});
  t.textContent = text; parent.append(t);
};
const fmt = x => x === "" || x == null || !Number.isFinite(Number(x)) ? "—" : Number(x).toLocaleString(undefined,{maximumFractionDigits:3});
const opt = (label, value) => new Option(label,value);
let data = null, offset = 0, selected = null, pageRequest = 0, caseRequest = 0, runRequest = 0;
async function api(route, query={}, options={}) {
  const response = await fetch("/api/" + route + "?" + new URLSearchParams(query),options);
  const result = await response.json();
  if (!response.ok) throw Error(result.error || response.statusText);
  return result;
}
function guard(action) {
  return async (...args) => {
    try { $("status").textContent=""; await action(...args); }
    catch (e) { $("status").textContent=e.message; }
  };
}
function table(labels, records) {
  if (!records.length) return make("p","No measurements available.");
  const t=make("table"), head=t.createTHead().insertRow(), body=t.createTBody();
  for (const label of labels) head.append(make("th",label));
  for (const row of records) {
    const tr=body.insertRow();
    for (const value of row) tr.append(make("td",value));
  }
  return t;
}
function plot(container, pairs, xlabel, ylabel, diagonal=false) {
  const valid=pairs.filter(([x,y])=> x!=="" && y!=="" && x!=null && y!=null &&
    [x,y].every(v=>Number.isFinite(+v) && +v>=0 && +v<=1)).map(([x,y])=>[+x,+y]).sort((a,b)=>a[0]-b[0]);
  if (!valid.length) return container.replaceChildren(make("p","No measurements available."));
  const graph=svg("svg",{viewBox:"0 0 350 230",class:"chart",role:"img","aria-label":ylabel+" against "+xlabel});
  const xp=x=>50+275*x, yp=y=>180-155*y;
  for(const p of [0,0.25,0.5,0.75,1]){
    graph.append(svg("line",{x1:50,x2:325,y1:yp(p),y2:yp(p),class:"axis"}));
    svgText(graph,42,yp(p)+4,p,11,"end"); svgText(graph,xp(p),196,p,11,"middle");
  }
  if(diagonal) graph.append(svg("line",{x1:50,x2:325,y1:180,y2:25,class:"diag"}));
  graph.append(svg("polyline",{points:valid.map(([x,y])=>xp(x)+","+yp(y)).join(" "),class:"curve"}));
  for(const [x,y] of valid) {
    const circle=svg("circle",{cx:xp(x),cy:yp(y),r:3.5,class:"point"});
    const title=svg("title",{}); title.textContent=fmt(x)+", "+fmt(y);circle.append(title);graph.append(circle);
  }
  svgText(graph,50,14,ylabel);svgText(graph,185,220,xlabel,12,"middle");
  container.replaceChildren(graph);
}
function reliability() {
  const variant=$("variant").value;
  const match=r=>r.model+" / "+r.calibration===variant;
  const rel=(data?.reliability||[]).filter(r=>match(r)&&+r.count>0);
  const cov=(data?.coverage||[]).filter(match);
  plot($("calplot"),rel.map(r=>[r.mean_probability,r.observed_rate]),"Mean predicted probability","Observed attack fraction",true);
  plot($("riskplot"),cov.map(r=>[r.coverage,r.risk]),"Automatic decision coverage","Error fraction");
  $("budgets").replaceChildren(table(["Target review fraction","Confidence cutoff","Coverage","Error fraction","Review count"],
    cov.map(r=>[r.target_review,r.threshold,r.coverage,r.risk,r.review_count].map(fmt))));
}
function matrix(){
  const m=data?.comparison.find(r=>r.model===$("conf-model").value && r.calibration===$("overview-cal").value);
  $("confusion").replaceChildren(table(["Actual / Predicted","Benign","Attack"],m?[["Benign",fmt(m.tn),fmt(m.fp)],["Attack",fmt(m.fn),fmt(m.tp)]]:[]));
  $("confusion").firstChild.classList.add("matrix");
}
function compareModels(){
  const filtered=(data?.comparison||[]).filter(r=>r.calibration===$("overview-cal").value);
  const selectedModel=$("conf-model").value;
  $("conf-model").replaceChildren(...filtered.map(r=>opt(r.model,r.model)));
  if(filtered.some(r=>r.model===selectedModel))$("conf-model").value=selectedModel;
  matrix();
  $("models").replaceChildren(table(["Model","Calibration","Macro F1","PR AUC","False alarms / 1k","Brier"],filtered.map(r=>[r.model,r.calibration,...[r.macro_f1,r.pr_auc,r.false_alarms_per_1000,r.brier].map(fmt)])));
}
async function overview(){
  const run=$("run").value, ticket=++runRequest; ++caseRequest;
  data=null; selected=null; offset=0; $("review").hidden=true;
  $("case").textContent="Select an event to inspect its evidence.";
  const result=run?await api("overview",{run}):null;
  if(ticket!==runRequest)return;
  data=result;
  const counts=data?.counts||{}, total=Object.values(counts).reduce((a,b)=>a+b,0);
  $("scope").textContent=run?(data?.registry?.data_manifest?.synthetic_fixture?"Synthetic fixture · ":"")+ (data?.registry?.data_manifest?.dataset||"Stored test predictions")+" · "+run:"No completed detection run found. Run the smoke or research pipeline to populate this view.";
  const cards=[["Test events",total],["Labelled attacks",counts["1"]??counts["1.0"]??0],["Detection models",new Set(data?.comparison.map(r=>r.model)).size],["Cases with feedback",data?.reviewed??0]];
  $("metrics").replaceChildren(...cards.map(([label,v])=>{const card=make("div",undefined,"card");card.append(make("div",label,"small"),make("div",fmt(v),"value"));return card;}));
  const metrics=data?.comparison||[];
  const cals=[...new Set(metrics.map(r=>r.calibration))];
  $("overview-cal").replaceChildren(...cals.map(c=>opt(c,c)));
  compareModels();
  const categories=Object.entries(data?.categories||{}).sort((a,b)=>b[1]-a[1]);
  $("categories").replaceChildren(...categories.map(([k,v])=>{const row=make("div",undefined,"categories");row.append(make("span",k),make("strong",fmt(v)));return row;}));
  $("variant").replaceChildren(...metrics.map(r=>{const label=r.model+" / "+r.calibration;return opt(label,label);}));
  const importance=(data?.importance||[]).slice().sort((a,b)=>+b.ap_drop-+a.ap_drop);
  $("importance").replaceChildren(table(["Feature","AP decrease"],importance.map(r=>[r.feature,fmt(r.ap_drop)])));
  $("errors").replaceChildren(table(["Category","Count","FP","FN"],(data?.errors||[]).map(r=>[r.category,fmt(r.count),fmt(r.fp),fmt(r.fn)])));
  $("policies").replaceChildren(table(["Policy","Escalated","Coverage","Automatic errors","Residual risk"],Object.entries(data?.policies||{}).map(([key,r])=>[key,fmt(r.escalated),fmt(r.coverage),fmt(r.automatic_errors),fmt(r.automatic_risk)])));
  reliability(); await loadQueue();
}
function inspect(report, records){
  const frag=document.createDocumentFragment();
  frag.append(make("h3","Investigation status"),make("p",report.status));
  for(const [heading,key] of [["Observations","observations"],["Hypotheses","hypotheses"],["Reasons","reasons"],["Uncertainty","uncertainty"],["Timeline","timeline"]]){
    frag.append(make("h3",heading));
    const values=report[key]||[];
    if(!values.length){frag.append(make("p",key==="timeline"?"No timestamped evidence.":"None recorded.","small"));continue;}
    for(const row of values) {
      let text=typeof row==="string"?row:JSON.stringify(row);
      if(key==="observations" && row.field)text=row.field+" = "+row.value+"  ["+(row.citations||[]).join(", ")+"]";
      if(key==="timeline")text=row.timestamp+" · "+row.event_id;
      frag.append(make("p",text));
    }
  }
  const details=make("details");details.append(make("summary","Cited records"),make("pre",JSON.stringify(records,null,2)));frag.append(details);
  return frag;
}
async function showCase(row){
  const id=++caseRequest, run=$("run").value; selected=null; $("review").hidden=true;
  const r=await api("evidence",{run,event:row.event_id}); if(id!==caseRequest)return;
  selected=row;
  $("case").replaceChildren(make("h3",row.event_id),inspect(r.report,r.evidence));$("decision").value=row.feedback.decision||"needs_review";$("note").value=row.feedback.note||"";$("review").hidden=false;
  for(const button of $("queue").children)button.setAttribute("aria-pressed",String(button.dataset.event===row.event_id));
}
async function loadQueue(){
  const ticket=++pageRequest,run=$("run").value;
  const response=run?await api("queue",{run,q:$("search").value,decision:$("state").value,offset}):{records:[],more:false};
  if(ticket!==pageRequest || run!==$("run").value)return;
  $("prev").disabled=offset===0;$("next").disabled=!response.more;
  const buttons=response.records.map(row=>{
    const b=make("button",undefined,"queueitem");b.type="button";b.dataset.event=row.event_id;b.append(make("span",row.event_id),make("span",fmt(row.probability)+" · "+(row.feedback.decision||"unreviewed")));b.onclick=guard(()=>showCase(row));return b;
  });
  $("queue").replaceChildren(...(buttons.length?buttons:[make("p","No matching events.")]));
}
async function behaviour(){
  const result=await api("behaviour"), metrics=result.summary?.metrics||{};
  $("seq-scope").textContent=result.summary?"Sequence dataset · "+(typeof result.summary.dataset==="string"?result.summary.dataset:JSON.stringify(result.summary.dataset)):"No sequence experiment available.";
  const best=result.transitions.sort((a,b)=>+b.count-+a.count).slice(0,12);
  const graph=svg("svg",{viewBox:"0 0 430 "+Math.max(50,24+best.length*36),class:"chart",role:"img","aria-label":"Directed state-transition graph"});
  for(const [i,r] of best.entries()){
    const y=22+i*36;graph.append(svg("path",{d:"M125 "+y+" H303 m-7 -4 7 4 -7 4",class:"graphline"}));
    for(const [x,state] of [[64,r.source],[365,r.target]]) {
      graph.append(svg("rect",{x:x-57,y:y-13,width:114,height:26,rx:6,class:"node"}));
      const title=String(state);svgText(graph,x,y+4,title.length>17?title.slice(0,15)+"…":title,11,"middle");
    }
    svgText(graph,215,y-4,fmt(r.count),10,"middle");
  }
  $("edges").replaceChildren(...(best.length?[graph,table(["From","To","Count","Transition probability"],best.map(r=>[r.source,r.target,fmt(r.count),fmt(r.probability)]))]:[make("p","No transition counts available.")]));
  $("fusion").replaceChildren(table(["Features","Average precision","ROC AUC","Calibrated Brier","Coverage","Accepted risk"],
    Object.entries(result.fusion?.metrics||{}).map(([key,r])=>[key,fmt(r.ap),fmt(r.roc_auc),fmt(r.calibrated?.brier),fmt(r.development_cutoff?.coverage),fmt(r.development_cutoff?.accepted_error_rate)])));
  $("seq-table").replaceChildren(table(["Model","ROC AUC","Average precision"],Object.entries(metrics).map(([model,r])=>[model,fmt(r.roc_auc),fmt(r.average_precision)])));
}
async function fixture(){
  const event=$("fixture").value;if(!event)return;
  const r=await api("evidence",{run:"@fixture",event});if(event===$("fixture").value)$("fixture-report").replaceChildren(inspect(r.report,r.evidence));
}
function tab(id){
  for(const section of document.querySelectorAll("main section"))section.hidden=section.id!==id;
  for(const button of document.querySelectorAll("nav button"))button.setAttribute("aria-current",button.dataset.tab===id?"page":"false");
  if(id==="provenance")$("registry").textContent=data?.registry?JSON.stringify(data.registry,null,2):"No registry recorded for this run.";
}
for(const button of document.querySelectorAll("nav button"))button.onclick=()=>tab(button.dataset.tab);
$("overview-cal").onchange=compareModels;$("conf-model").onchange=matrix;$("variant").onchange=reliability;$("run").onchange=guard(async()=>{await overview();tab("overview");});
$("fixture").onchange=guard(fixture);
for(const id of ["search","state"])$(id).oninput=guard(async()=>{offset=0;await loadQueue();});
$("prev").onclick=guard(async()=>{offset=Math.max(0,offset-25);await loadQueue();});
$("next").onclick=guard(async()=>{offset+=25;await loadQueue();});
$("review").onsubmit=guard(async e=>{
  e.preventDefault();if(!selected)return;
  const body=JSON.stringify({run:$("run").value,event_id:selected.event_id,decision:$("decision").value,note:$("note").value,version:selected.feedback.version||0});
  const r=await api("feedback",{}, {method:"POST",headers:{"Content-Type":"application/json"},body});
  selected.feedback={version:r.version,note:$("note").value,decision:$("decision").value};
  await loadQueue();const fresh=await api("overview",{run:$("run").value});
  $("metrics").lastChild.lastChild.textContent=fmt(fresh.reviewed);$("status").textContent="Feedback saved.";
});
guard(async()=>{
  tab("overview");const [runs,ids]=await Promise.all([api("runs"),api("fixture-ids")]);
  $("run").replaceChildren(...runs.map(r=>opt(r,r)));$("fixture").replaceChildren(...ids.map(i=>opt(i,i)));
  await Promise.all([overview(),behaviour(),fixture()]);
})();
