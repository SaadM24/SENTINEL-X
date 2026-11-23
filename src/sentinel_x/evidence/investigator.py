"""Project untrusted records onto a narrow, citable investigation schema."""
from collections import defaultdict
from datetime import datetime, timezone
from math import isfinite

FIELDS = ("signal", "model", "probability")


def instant(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        pass
    return None


def clean_record(raw):
    event_id = raw.get("event_id")
    if not isinstance(event_id, str) or not event_id.strip():
        raise ValueError("Each evidence record needs a nonempty text event_id")
    record = {"event_id": event_id}
    for field in ("signal", "model", "session_id"):
        value = raw.get(field)
        if isinstance(value, str) and value.strip():
            record[field] = value
    probability = raw.get("probability")
    if (isinstance(probability, (int, float)) and not isinstance(probability, bool)
            and isfinite(probability) and 0 <= probability <= 1):
        record["probability"] = probability
    if instant(raw.get("timestamp")) is not None:
        record["timestamp"] = raw["timestamp"]
    return record


class EvidenceIndex:
    def __init__(self, records):
        self.by_id = {}
        self.by_session = defaultdict(list)
        for raw in records:
            record = clean_record(raw)
            event_id = record["event_id"]
            if event_id in self.by_id:
                raise ValueError(f"Duplicate evidence identifier {event_id!r}")
            self.by_id[event_id] = record
            if "session_id" in record:
                self.by_session[record["session_id"]].append(record)

    def report(self, event_id, *, correlate=True):
        result = dict(event_id=event_id, status="abstained", observations=[], hypotheses=[],
                      timeline=[], reasons=[], related_event_ids=[], uncertainty=[])
        anchor = self.by_id.get(event_id)
        if anchor is None:
            result["reasons"].append("No matching event identifier.")
            return result
        related = [anchor]
        if correlate and "session_id" in anchor:
            related = self.by_session[anchor["session_id"]]
        result["related_event_ids"] = sorted(row["event_id"] for row in related)
        dated = sorted((row for row in related if "timestamp" in row),
                       key=lambda row: (instant(row["timestamp"]), row["event_id"]))
        result["timeline"] = [{key: row[key] for key in ("event_id", "timestamp")} for row in dated]
        if len(dated) < len(related):
            result["uncertainty"].append("One or more records lack a usable time with UTC offset.")
        if "session_id" not in anchor:
            result["uncertainty"].append("Cross-record association unavailable.")
        if "probability" not in anchor and "signal" not in anchor:
            result["reasons"].append("The anchor has neither an admissible score nor a recorded signal.")
            return result
        result["status"] = "reported"
        result["observations"] = [
            dict(field=field, value=anchor[field], citations=[event_id])
            for field in FIELDS if field in anchor
        ]
        result["uncertainty"].append("A recorded alert alone cannot establish intent, attack outcome or root cause.")
        return result


def investigate(records, event_id):
    return EvidenceIndex(records).report(event_id)


def check_citation(index, observation, citation):
    row = index.by_id.get(citation, {})
    field = observation.get("field")
    return field in FIELDS and field in row and row[field] == observation.get("value")
