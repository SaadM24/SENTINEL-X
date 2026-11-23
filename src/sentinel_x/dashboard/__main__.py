"""Local read-only artifact API plus an append-only analyst feedback store."""
import argparse
import csv
import heapq
import json
import math
import mimetypes
import sqlite3
from collections import Counter
from contextlib import closing, contextmanager
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from sentinel_x.evidence.investigator import clean_record, investigate

ASSETS = Path(__file__).with_name("static")
DECISIONS = {"benign", "attack", "needs_review"}


class Conflict(ValueError):
    pass


def rows(path):
    if path.is_file():
        with path.open(encoding="utf-8-sig", newline="") as stream:
            yield from csv.DictReader(stream)


def event_record(row):
    return {"event_id": row["event_id"], "probability": float(row["probability"]),
            "model": row["model"]}


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.db = self.root / "outputs" / "feedback.sqlite3"

    def runs(self):
        path = self.root / "results/v02"
        return sorted(p.name for p in path.glob("*") if
                      (p / "comparison.csv").is_file() and (p / "predictions.csv").is_file())

    def run_dir(self, run):
        if run not in self.runs():
            raise KeyError("Unknown experiment run")
        return self.root / "results/v02" / run

    @contextmanager
    def connection(self):
        self.db.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.db, timeout=5)) as conn, conn:
            conn.execute("""CREATE TABLE IF NOT EXISTS feedback
                (run TEXT, event TEXT, version INTEGER, decision TEXT, note TEXT,
                 recorded_utc TEXT DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                 PRIMARY KEY (run,event,version))""")
            yield conn

    def latest(self, run):
        if not self.db.exists():
            return {}
        with self.connection() as conn:
            records = conn.execute("""SELECT event,decision,note,version,recorded_utc
                FROM feedback a WHERE run=? AND version=(
                SELECT max(version) FROM feedback b WHERE b.run=a.run AND b.event=a.event)""", (run,))
            return {event: dict(decision=d,note=n,version=v,recorded_utc=t)
                    for event,d,n,v,t in records}

    def overview(self, run):
        path = self.run_dir(run)
        counts = Counter()
        categories = Counter()
        for row in rows(path / "predictions.csv"):
            counts[str(row["y_true"])] += 1
            categories[row.get("category") or "Unspecified"] += 1
        registry = path / "registry.json"
        integrated = self.root / "results/v10" / run / "triage/summary.json"
        return dict(run=run, comparison=list(rows(path/"comparison.csv")),
                    reliability=list(rows(path/"reliability.csv")), coverage=list(rows(path/"coverage.csv")),
                    counts=counts, categories=categories,
                    importance=list(rows(path/"importance.csv")),
                    errors=list(rows(path/"categories.csv")),
                    policies=json.loads(integrated.read_text(encoding="utf-8")).get("policies", {}) if integrated.exists() else {},
                    reviewed=len(self.latest(run)),
                    registry=json.loads(registry.read_text(encoding="utf-8")) if registry.exists() else None)

    def queue(self, run, query, decision, offset):
        if offset < 0 or offset > 100000:
            raise ValueError("Invalid offset")
        feedback = self.latest(run)
        def candidates():
            for r in rows(self.run_dir(run)/"predictions.csv"):
                entry = feedback.get(r["event_id"], {})
                if decision and entry.get("decision", "unreviewed") != decision:
                    continue
                if query.casefold() not in r["event_id"].casefold():
                    continue
                p = float(r["probability"])
                if math.isfinite(p):
                    yield (abs(p-.5), r["event_id"], dict(**event_record(r), feedback=entry))
        subset = heapq.nsmallest(offset+26,candidates(),key=lambda x:x[:2])
        return dict(records=[x[2] for x in subset[offset:offset+25]], more=len(subset)>offset+25)

    def evidence(self, run, event):
        if run == "@fixture":
            path = self.root / "data/fixtures/evidence_records.json"
            records = json.loads(path.read_text(encoding="utf-8"))
        else:
            records = [event_record(r) for r in rows(self.run_dir(run)/"predictions.csv")
                       if r["event_id"] == event]
        report = investigate(records,event)
        return dict(report=report, evidence=[clean_record(r) for r in records if
                    r["event_id"] in set(report.get("related_event_ids", [])) | {event}])

    def save(self, payload):
        run,event = payload["run"],payload["event_id"]
        decision,note,version = payload["decision"],payload["note"],payload["version"]
        if decision not in DECISIONS or not isinstance(note,str) or len(note)>2000 or type(version) is not int or version<0:
            raise ValueError("Invalid decision, note or version")
        if not any(r["event_id"] == event for r in rows(self.run_dir(run)/"predictions.csv")):
            raise KeyError("Unknown event")
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE")
            current, = conn.execute("SELECT coalesce(max(version),0) FROM feedback WHERE run=? AND event=?",(run,event)).fetchone()
            if current != version:
                raise Conflict("Feedback changed. Refresh before saving again.")
            conn.execute("INSERT INTO feedback(run,event,version,decision,note) VALUES(?,?,?,?,?)",
                         (run,event,version+1,decision,note))
        return {"version":version+1}


class Handler(BaseHTTPRequestHandler):
    server_version = "SentinelX/1.0"

    def __init__(self,*args,store,**kwargs):
        self.store = store
        super().__init__(*args,**kwargs)

    def reply(self, data, code=200, mime="application/json"):
        if mime=="application/json":
            data=json.dumps(data,allow_nan=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'")
        self.send_header("Cache-Control","no-store")
        self.end_headers()
        self.wfile.write(data)

    def access(self):
        hosts = {f"localhost:{self.server.server_port}", f"127.0.0.1:{self.server.server_port}"}
        host = self.headers.get("Host","")
        if host not in hosts or self.headers.get("Origin", f"http://{host}") != f"http://{host}":
            self.reply({"error":"Local access only"},403)
            return False
        return True

    def do_GET(self):
        if not self.access():
            return
        route=urlparse(self.path)
        params={k:v[0] for k,v in parse_qs(route.query).items()}
        run=params.get("run","")
        try:
            if route.path in {"/","/app.js","/app.css"}:
                asset=ASSETS/("index.html" if route.path=="/" else route.path[1:])
                return self.reply(asset.read_bytes(),mime=mimetypes.guess_type(asset.name)[0])
            if route.path=="/api/runs":
                result=self.store.runs()
            elif route.path=="/api/overview":
                result=self.store.overview(run)
            elif route.path=="/api/queue":
                result=self.store.queue(run,params.get("q",""),params.get("decision",""),int(params.get("offset",0)))
            elif route.path=="/api/evidence":
                result=self.store.evidence(run,params.get("event",""))
            elif route.path=="/api/behaviour":
                result=behaviour(self.store.root)
            elif route.path=="/api/fixture-ids":
                path=self.store.root/"data/fixtures/evidence_records.json"
                result=[r["event_id"] for r in json.loads(path.read_text(encoding="utf-8"))] if path.exists() else []
            else:
                return self.reply({"error":"Unknown endpoint"},404)
            self.reply(result)
        except KeyError as exc:
            self.reply({"error":str(exc)},404)
        except (ValueError,TypeError) as exc:
            self.reply({"error":str(exc)},400)

    def do_POST(self):
        if not self.access():
            return
        if urlparse(self.path).path!="/api/feedback":
            return self.reply({"error":"Unknown endpoint"},404)
        try:
            size=int(self.headers.get("Content-Length","0"))
            if self.headers.get_content_type()!="application/json" or not 0<size<=8192:
                return self.reply({"error":"Expected a small JSON record"},400)
            self.reply(self.store.save(json.loads(self.rfile.read(size))),201)
        except Conflict as exc:
            self.reply({"error":str(exc)},409)
        except (ValueError,KeyError,TypeError) as exc:
            self.reply({"error":str(exc)},400)


def behaviour(root):
    path=root/"results/v03"
    summary = path / "summary.json"
    fusion = root / "results/v03_fusion/summary.json"
    return {"fusion": json.loads(fusion.read_text(encoding="utf-8")) if fusion.exists() else None,
            "summary": json.loads(summary.read_text(encoding="utf-8")) if summary.exists() else None,
            "transitions": list(rows(path/"transitions.csv"))}


def serve(root,port):
    return ThreadingHTTPServer(("127.0.0.1",port),partial(Handler,store=Store(root)))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,default=Path.cwd())
    parser.add_argument("--port",type=int,default=8765)
    args=parser.parse_args()
    with serve(args.root.resolve(),args.port) as http:
        print(f"SENTINEL-X listening on http://127.0.0.1:{http.server_port}",flush=True)
        try:
            http.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
