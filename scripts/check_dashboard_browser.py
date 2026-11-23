"""Optional UI regression check. Requires Playwright and a Chromium installation."""
import argparse
import json
import shutil
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from sentinel_x.dashboard.__main__ import serve


def check(project, binary, output):
    with tempfile.TemporaryDirectory() as local:
        local=Path(local)
        detection=project/"results/v02"
        name="research" if (detection/"research").exists() else "smoke"
        dest=local/"results/v02"/name
        dest.mkdir(parents=True)
        for f in (detection/name).iterdir():
            if f.suffix in {".csv",".json"}:
                shutil.copy(f,dest/f.name)
        shutil.copytree(project/"data/fixtures",local/"data/fixtures")
        if (project/"results/v03").exists():
            shutil.copytree(project/"results/v03",local/"results/v03")
        for component in ["results/v03_fusion",f"results/v10/{name}/triage"]:
            path=project/component/"summary.json"
            if path.is_file():
                target=local/component
                target.mkdir(parents=True,exist_ok=True)
                shutil.copy(path,target)
        with serve(local,0) as server, sync_playwright() as play:
            thread=threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            browser=play.chromium.launch(executable_path=binary)
            page=browser.new_page(viewport={"width":1380,"height":980})
            errors=[]
            page.on("pageerror",lambda e:errors.append(str(e)))
            try:
                page.goto(f"http://127.0.0.1:{server.server_port}")
                expect(page.locator("#models tbody tr").first).to_be_visible()
                expect(page.locator("#status")).to_be_empty()
                output.mkdir(parents=True,exist_ok=True)
                page.screenshot(path=str(output/"overview.png"))
                page.get_by_role("button",name="Model reliability").click()
                expect(page.locator("#calplot svg circle").first).to_be_visible()
                expect(page.locator("#riskplot svg circle").first).to_be_visible()
                expect(page.locator("#importance tbody tr").first).to_be_visible()
                page.get_by_role("button",name="Alert triage").click()
                page.locator("#queue button").first.click()
                expect(page.locator("#case")).to_contain_text("reported")
                if (local/f"results/v10/{name}/triage/summary.json").exists():
                    expect(page.locator("#policies")).to_contain_text("cal_85")
                expect(page.locator("#fixture-report")).to_contain_text("2026-01-02")
                page.locator("#decision").select_option("benign")
                page.locator("#note").fill("Browser verification")
                page.get_by_role("button",name="Save feedback").click()
                expect(page.locator("#status")).to_have_text("Feedback saved.")
                page.locator("#state").select_option("benign")
                expect(page.locator("#queue button")).to_have_count(1)
                page.locator("#queue button").click()
                expect(page.locator("#note")).to_have_value("Browser verification")
                page.get_by_role("button",name="Event sequences").click()
                if (local/"results/v03/transitions.csv").exists():
                    expect(page.locator("#edges svg rect").first).to_be_visible()
                if (local/"results/v03_fusion/summary.json").exists():
                    expect(page.locator("#fusion")).to_contain_text("frequencies_markov")
                page.get_by_role("button",name="Reproducibility").click()
                expect(page.locator("#registry")).to_contain_text("experiment_id")
                page.set_viewport_size({"width":390,"height":844})
                page.get_by_role("button",name="Overview",exact=True).click()
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
                assert not errors,errors
                state=dict(status="passed",chromium=browser.version,dataset_run=name,
                           sequence_graph_checked=(local/"results/v03/transitions.csv").exists(),
                           viewport_widths=[1380,390],console_page_errors=errors,
                           feedback_store="temporary isolated copy")
                (output/"browser-check.json").write_text(json.dumps(state,indent=2))
                print(json.dumps(state))
            finally:
                browser.close()
                server.shutdown()
                thread.join()


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chromium",default=shutil.which("chromium"))
    parser.add_argument("--root",type=Path,default=Path.cwd())
    parser.add_argument("--output",type=Path,default=Path("results/v05"))
    args=parser.parse_args()
    check(args.root,args.chromium,args.output)
