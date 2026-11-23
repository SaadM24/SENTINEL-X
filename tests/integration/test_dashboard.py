"""HTTP-level tests using a synthetic result directory and temporary feedback store."""
import json
import sqlite3
import tempfile
import threading
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sentinel_x.dashboard.__main__ import Conflict, Store, serve


class DashboardTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name)
        run = cls.root / "results/v02/example"
        run.mkdir(parents=True)
        (run/"comparison.csv").write_text("model,calibration,tn,fp,fn,tp\nline,raw,1,1,0,1\n")
        (run/"predictions.csv").write_text(
            "event_id,y_true,probability,raw_probability,model,dataset,category\n"
            "a,1,0.99,0.95,line,fixture,attack\nb,0,0.51,0.52,line,fixture,normal\n")
        cls.server = serve(cls.root, 0)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def get(self, path):
        with urlopen(self.base+path, timeout=5) as response:
            return json.load(response)

    def test_static_and_overview(self):
        with urlopen(self.base) as response:
            self.assertIn(b"Alert triage",response.read())
        self.assertEqual(self.get("/api/runs"),["example"])
        summary=self.get("/api/overview?run=example")
        self.assertEqual(summary["counts"],{"0":1,"1":1})
        self.assertEqual(summary["comparison"][0]["model"],"line")
        self.assertEqual(self.get("/api/behaviour")["transitions"],[])

    def test_queue_and_grounding(self):
        queue=self.get("/api/queue?run=example")["records"]
        self.assertEqual([e["event_id"] for e in queue],["b","a"])
        self.assertNotIn("y_true",queue[0])
        evidence=self.get("/api/evidence?run=example&event=a")
        self.assertEqual(evidence["report"]["status"],"reported")
        self.assertTrue(all(claim["citations"]==["a"] for claim in evidence["report"]["observations"]))
        self.assertNotIn("category",evidence["evidence"][0])

    def test_feedback_version_conflict(self):
        payload=dict(run="example",event_id="a",decision="needs_review",note="<script>literal</script>",version=0)
        req=Request(self.base+"/api/feedback?",data=json.dumps(payload).encode(),headers={"Content-Type":"application/json"})
        with urlopen(req) as response:
            self.assertEqual(json.load(response),{"version":1})
        with self.assertRaises(HTTPError) as rejected:
            urlopen(req)
        self.assertEqual(rejected.exception.code,409)
        filtered=self.get("/api/queue?run=example&decision=needs_review")["records"]
        self.assertEqual(filtered[0]["feedback"]["note"],payload["note"])

    def test_unknown_run_and_cross_origin(self):
        with self.assertRaises(HTTPError) as bad:
            self.get("/api/overview?run=../")
        self.assertEqual(bad.exception.code,404)
        req=Request(self.base+"/api/runs",headers={"Origin":"http://outside.invalid"})
        with self.assertRaises(HTTPError) as bad:
            urlopen(req)
        self.assertEqual(bad.exception.code,403)


class FeedbackConnectionTest(unittest.TestCase):
    def test_feedback_transactions_release_database(self):
        connect = sqlite3.connect
        handles = []
        statements = []

        def track(*args, **kwargs):
            conn = connect(*args, **kwargs)
            cleanup.callback(conn.close)
            handles.append(conn)  # Keep it alive so GC cannot hide a missing close.
            conn.set_trace_callback(statements.append)
            return conn

        def assert_closed():
            with self.assertRaises(sqlite3.ProgrammingError):
                handles[-1].execute("SELECT 1")

        with tempfile.TemporaryDirectory() as tmp, ExitStack() as cleanup:
            store = Store(tmp)
            run = store.root / "results/v02/example"
            run.mkdir(parents=True)
            (run / "comparison.csv").touch()
            (run / "predictions.csv").write_text("event_id\na\n")
            payload = dict(run="example", event_id="a", decision="benign", note="", version=0)
            with patch("sentinel_x.dashboard.__main__.sqlite3.connect", side_effect=track):
                store.save(payload)
                assert_closed()
                self.assertIn("COMMIT", statements)
                self.assertEqual(store.latest("example")["a"]["version"], 1)
                assert_closed()

                statements.clear()
                with self.assertRaises(Conflict):
                    store.save(payload)
                assert_closed()
                self.assertIn("ROLLBACK", statements)
                self.assertEqual(store.latest("example")["a"]["decision"], "benign")
                assert_closed()
                store.db.unlink()  # Windows rejects unlink while a handle is open.

                store.db.write_bytes(b"invalid SQLite file")
                with self.assertRaises(sqlite3.DatabaseError):
                    store.latest("example")
                assert_closed()  # Schema initialization failed before the query.
                store.db.unlink()
