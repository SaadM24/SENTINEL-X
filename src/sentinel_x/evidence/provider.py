"""Optional local Ollama reranker. Free-form output can never become a finding."""
import json
from urllib import request

ENDPOINT = "http://127.0.0.1:11434/api/generate"


class NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def reorder(report, ranking):
    facts = report["observations"]
    if (not isinstance(ranking, list) or not all(type(i) is int for i in ranking)
            or sorted(ranking) != list(range(len(facts)))):
        raise ValueError("Provider must return a permutation of observation indices")
    return {**report, "observations": [facts[i] for i in ranking]}


def local_rerank(report, model, *, timeout=15, send=None):
    """Reorder validated fields only. Fall back to deterministic report on any failure."""
    if not report["observations"]:
        return report
    # Supply only field names. No event text, identifiers or probabilities leave the process.
    names = [fact["field"] for fact in report["observations"]]
    prompt = ("Order these field names for an analyst. Return only a JSON object with an "
              "order array of every zero-based index exactly once. Fields: " + json.dumps(names))
    payload = json.dumps(dict(model=model, prompt=prompt, stream=False, format="json")).encode()
    try:
        if send is None:
            req = request.Request(ENDPOINT, data=payload, headers={"Content-Type": "application/json"})
            opener = request.build_opener(request.ProxyHandler({}), NoRedirect())
            with opener.open(req, timeout=timeout) as response:
                answer = json.loads(response.read(65537))
        else:
            answer = send(payload)
        result = reorder(report, json.loads(answer["response"])["order"])
        return {**result, "provider_status": "reranked"}
    except (OSError, ValueError, KeyError, TypeError):
        return {**report, "provider_status": "offline_fallback"}
