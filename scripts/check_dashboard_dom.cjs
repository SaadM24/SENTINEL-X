/* Optional browser-independent integration check. Install jsdom@26 in Node's module path. */
const {JSDOM, VirtualConsole} = require("jsdom");
const assert = require("node:assert/strict");
const base = process.argv[2] || "http://127.0.0.1:8765";
const failures = [];
const consoleLog = new VirtualConsole();
consoleLog.on("jsdomError", e=>failures.push(String(e)));
async function waitFor(check) {
  const until=Date.now()+10000;
  while(Date.now()<until){if(check())return;await new Promise(r=>setTimeout(r,40));}
  throw Error("Timed out waiting for "+check);
}
(async()=>{
  const dom=await JSDOM.fromURL(base,{resources:"usable",runScripts:"dangerously",virtualConsole:consoleLog,
    beforeParse(w){w.fetch=(url,opts)=>fetch(new URL(url,base),opts);}});
  try{
    const d=dom.window.document, by=id=>d.getElementById(id);
    await waitFor(()=>d.querySelector("#models tbody tr"));
    await waitFor(()=>d.querySelector("#queue button"));
    assert.equal(by("status").textContent,"");
    assert(+by("metrics").querySelector(".value").textContent.replaceAll(",","")>0);
    d.querySelector('[data-tab="trust"]').click();
    assert(d.querySelector("#calplot circle"));assert(d.querySelector("#riskplot circle"));
    d.querySelector('[data-tab="triage"]').click();d.querySelector("#queue button").click();
    await waitFor(()=>!by("review").hidden);assert(by("case").textContent.includes("reported"));
    assert(by("case").textContent.includes("Uncertainty"));assert(by("fixture-report").textContent.includes("2026-01-02"));
    d.querySelector('[data-tab="provenance"]').click();
    assert(by("registry").textContent.includes("experiment_id"));
    d.querySelector('[data-tab="behaviour"]').click();
    const sequenceGraphChecked=!!d.querySelector("#edges svg rect");
    assert.deepEqual(failures,[]);
    console.log(JSON.stringify({status:"passed",engine:"jsdom 26",sequenceGraphChecked,
        tests:["load stored results","model plots","queue","case report","fixture timeline","registry","navigation"]},null,2));
  } finally {dom.window.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
