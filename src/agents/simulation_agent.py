"""Baseline investigator that only knows the standard tool executor."""

from math import isfinite
from uuid import uuid4

from src.tools.executor import ToolExecutor, ToolResult
from src.evidence.store import EvidenceStore

from .investigation import InvestigationBudget, InvestigationRecord
from .state import AgentState


class SimulationInvestigator:
    def __init__(self, tools: ToolExecutor, budget: InvestigationBudget | None = None):
        self.tools = tools
        self.budget = budget or InvestigationBudget()

    def run(self, incident_id: str) -> AgentState:
        state = AgentState(f"Investigate {incident_id}")
        state.investigation = InvestigationRecord(uuid4().hex, self.budget)
        state.investigation.record("incident_identified", incident_id=incident_id)
        state.investigation.transition("observe")
        alert = self._call(state, "get_incident_record", {"incident_id": incident_id})
        if not alert.ok:
            state.answer = f"Investigation incomplete: {alert.error_code}: {alert.error}"
            state.investigation.transition("final_diagnosis")
            state.investigation.record("diagnosis_produced", evidence_ids=[])
            state.investigation.transition("completed")
            return state
        info = alert.content
        metrics = self._call(state, "get_server_metrics", {"server_id": info["server_id"]})
        logs = self._call(state, "get_application_logs", {"service": info["service"]})
        pod_events = (self._call(state, "get_pod_events", {"pod": info["pod_name"]})
                      if info.get("pod_name") else None)
        peer_metrics = (self._call(state, "get_service_network_metrics",
                                   {"service": info["service"]})
                        if info.get("network_scope") else None)
        related = []
        for item in info.get("related_incidents", []):
            alert_result = self._call(state, "get_incident_record", {"incident_id": item["id"]})
            log_result = self._call(state, "get_application_logs", {"service": item["service"]})
            related.append((item, alert_result, log_result))
        evidence = []
        run_id = state.investigation.investigation_id
        store = EvidenceStore(run_id)
        state.investigation.transition("normalize_evidence")

        def add(observation: str, result: ToolResult, source_type: str,
                signal: str, service: str, item: dict | None = None,
                start_item: dict | None = None) -> None:
            timestamp = item.get("timestamp") if item else None
            start_timestamp = start_item.get("timestamp") if start_item else timestamp
            card = store.add(source_type=source_type, source=result.name, service=service,
                             signal=signal, observation=observation,
                             raw_reference=f"tool-result://{run_id}/{next(i for i, value in enumerate(state.tool_results, 1) if value is result)}",
                             time_start=start_timestamp, time_end=timestamp)
            evidence.append(f"{observation} [{card.evidence_id}]")

        store.add(source_type="incident", source=alert.name, service=info["service"],
                  signal="incident_status", observation=f"status: {info['status']}",
                  raw_reference=f"tool-result://{run_id}/1",
                  time_start=info.get("observed_at"), time_end=info.get("observed_at"))
        if metrics.ok and metrics.content["samples"]:
            samples = metrics.content["samples"]
            sample = samples[-1]
            values = ", ".join(f"{key}={value}" for key, value in sample.items()
                               if key not in {"minute", "timestamp"})
            add(f"metrics at {sample['timestamp']}: {values}", metrics, "metric",
                "server_metrics", info["service"], sample)
            if len(samples) >= 2 and all(item["cpu_percent"] >= 90 for item in samples[-2:]):
                add("CPU remained above 90% across two samples", metrics, "metric",
                    "cpu_percent", info["service"], sample, samples[-2])
            if (len(samples) >= 3
                    and all(left["memory_percent"] < right["memory_percent"]
                            for left, right in zip(samples[-3:-1], samples[-2:]))
                    and sample["memory_percent"] >= 90):
                add(f"memory rose from {samples[-3]['memory_percent']}% "
                    f"to {sample['memory_percent']}%", metrics, "metric",
                    "memory_percent", info["service"], sample, samples[-3])
            if sample["disk_percent"] >= 95:
                add(f"disk is {sample['disk_percent']}% used", metrics, "metric",
                    "disk_percent", info["service"], sample)
        latest_log = None
        if logs.ok:
            entries = logs.content["entries"]
            latest_log = entries[-1] if entries else None
            if latest_log and (latest_log["severity"] in {"ERROR", "WARN"}
                               or info["status"] in {"recovering", "resolved"}):
                add(f"latest log: {latest_log['message']}", logs, "log",
                    "application_log", info["service"], latest_log)
            if latest_log and latest_log["severity"] == "ERROR":
                releases = [entry for entry in entries[:-1]
                            if "release deployed" in entry["message"].casefold()]
                if releases:
                    add(f"errors followed release at {releases[-1]['timestamp']}", logs,
                        "log", "release_then_error", info["service"], latest_log,
                        releases[-1])
        if pod_events and pod_events.ok and pod_events.content["entries"]:
            latest_pod = pod_events.content["entries"][-1]
            add(f"pod {latest_pod['pod']} event: {latest_pod['reason']}: "
                f"{latest_pod['message']}", pod_events, "event", "pod_event",
                info["service"], latest_pod)
        if peer_metrics and peer_metrics.ok and peer_metrics.content["samples"]:
            latest_by_service = {}
            for sample in peer_metrics.content["samples"]:
                latest_by_service[sample["service"]] = sample["latency_ms"]
            add("peer latency: " + ", ".join(
                f"{service}={latency}ms" for service, latency in sorted(latest_by_service.items())),
                peer_metrics, "metric", "peer_latency", info["service"],
                peer_metrics.content["samples"][-1])
        for item, alert_result, log_result in related:
            if alert_result.ok:
                detail = (log_result.content["entries"][-1]["message"]
                          if log_result.ok and log_result.content["entries"] else "no log evidence")
                add(f"separate incident {item['id']} ({item['service']}): {detail}",
                    log_result if log_result.ok and log_result.content["entries"] else alert_result,
                    "log" if log_result.ok and log_result.content["entries"] else "incident",
                    "related_incident", item["service"],
                    log_result.content["entries"][-1]
                    if log_result.ok and log_result.content["entries"] else None)
        state.evidence_cards = store.cards
        state.investigation.record("evidence_created", evidence_ids=[
            card.evidence_id for card in store.cards])
        state.investigation.transition("verify")
        if info["status"] == "healthy":
            state.answer = (f"No active incident for {incident_id}; current observations "
                            "show healthy service status "
                            + " ".join(f"[{card.evidence_id}]" for card in store.cards) + ".")
        elif not evidence:
            state.answer = f"Insufficient evidence for {incident_id}; verify monitoring and logs."
        else:
            conflict = (metrics.ok and metrics.content["samples"] and latest_log
                        and metrics.content["samples"][-1]["cpu_percent"] < 50
                        and "cpu saturation" in latest_log["message"].casefold())
            recommendation = ("CPU measurements conflict with the application log; "
                              "verify monitoring and gather another measurement."
                              if conflict else self._recommendation(info["status"], latest_log))
            state.answer = (f"Incident {incident_id} ({info['status']}): "
                            + "; ".join(evidence) + ". "
                            + recommendation)
        if (not metrics.ok or not logs.ok
                or pod_events and not pod_events.ok
                or peer_metrics and not peer_metrics.ok
                or any(not alert.ok or not log.ok for _, alert, log in related)):
            state.answer += " Some observations were unavailable."
        state.investigation.transition("final_diagnosis")
        state.investigation.record("diagnosis_produced", evidence_ids=[
            card.evidence_id for card in store.cards])
        state.investigation.transition("completed")
        return state

    @staticmethod
    def _recommendation(status: str, latest_log: dict | None) -> str:
        if status == "resolved":
            return "Confirm sustained recovery and monitor request errors."
        if status == "recovering":
            return "Monitor recovery and verify that request failures continue to fall."
        if latest_log and latest_log["severity"] == "ERROR":
            return "Escalate active failures and inspect the failing dependency."
        if latest_log and latest_log["severity"] == "WARN":
            return "Check the warning trend and gather more evidence before changes."
        return "Investigate the observed symptoms."

    def _call(self, state: AgentState, name: str, arguments: dict[str, str]) -> ToolResult:
        state.trace.append({"stage": "selection", "tool": name, "arguments": arguments})
        record = state.investigation
        record.transition("policy_check")
        record.record("tool_proposed", tool=name)
        if not record.reserve_tool_call():
            result = ToolResult(name, False, error="Investigation budget exceeded",
                                error_code="budget_exceeded")
            record.record("policy_denied", tool=name, reason="budget_exceeded")
            record.transition("observe")
        else:
            preflight = getattr(self.tools, "preflight", None)
            rejection = preflight(name, arguments) if callable(preflight) else None
            record.record("policy_checked", tool=name, allowed=rejection is None,
                          error_code=rejection.error_code if rejection else None)
            if rejection is not None:
                result = rejection
            else:
                record.transition("execute_read_action")
                result = self.tools.execute(name, arguments)
                record.record("tool_completed", tool=name, ok=result.ok,
                              error_code=result.error_code,
                              observed_minute=(result.content.get("observed_minute")
                                               if result.ok and isinstance(result.content, dict)
                                               else None))
            record.transition("observe")
        if result.ok and not self._valid_content(name, result.content):
            result = ToolResult(name, False, error="Malformed tool response",
                                error_code="malformed_tool_response")
        state.tool_results.append(result)
        state.trace.append({"stage": "execution", "tool": name, "ok": result.ok,
                            "error_code": result.error_code})
        return result

    @staticmethod
    def _valid_content(name: str, content: object) -> bool:
        if (not isinstance(content, dict)
                or not isinstance(content.get("observed_minute"), int)
                or isinstance(content["observed_minute"], bool)):
            return False
        if name == "get_incident_record":
            return all(isinstance(content.get(key), str) and content[key]
                       for key in ("id", "service", "server_id", "status")) \
                and isinstance(content.get("related_incidents", []), list) \
                and all(isinstance(item, dict) and
                        all(isinstance(item.get(key), str) and item[key]
                            for key in ("id", "service"))
                        for item in content.get("related_incidents", []))
        field = "samples" if name in {"get_server_metrics", "get_service_network_metrics"} \
            else "entries"
        values = content.get(field)
        if not isinstance(values, list) or not all(isinstance(item, dict) for item in values):
            return False
        required = {
            "get_server_metrics": ("minute", "timestamp", "cpu_percent",
                                   "memory_percent", "disk_percent"),
            "get_application_logs": ("minute", "timestamp", "severity", "message"),
            "get_pod_events": ("minute", "timestamp", "pod", "reason", "message"),
            "get_service_network_metrics": ("minute", "timestamp", "service", "latency_ms"),
        }.get(name)
        if required is None or not all(all(key in item for key in required)
                                       for item in values):
            return False
        if any(not isinstance(item["minute"], int) or isinstance(item["minute"], bool)
               or not isinstance(item["timestamp"], str) for item in values):
            return False
        if name == "get_server_metrics":
            return all(all(isinstance(item[key], (int, float))
                           and not isinstance(item[key], bool)
                           and isfinite(item[key])
                           for key in ("cpu_percent", "memory_percent", "disk_percent"))
                       for item in values)
        if name == "get_service_network_metrics":
            return all(isinstance(item["service"], str)
                       and isinstance(item["latency_ms"], (int, float))
                       and not isinstance(item["latency_ms"], bool)
                       and isfinite(item["latency_ms"])
                       for item in values)
        fields = ("severity", "message") if name == "get_application_logs" \
            else ("pod", "reason", "message")
        return all(all(isinstance(item[key], str) for key in fields) for item in values)
