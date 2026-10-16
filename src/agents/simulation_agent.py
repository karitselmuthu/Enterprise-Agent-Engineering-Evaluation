"""Baseline investigator that only knows the standard tool executor."""

from math import isfinite

from src.tools.executor import ToolExecutor, ToolResult

from .state import AgentState


class SimulationInvestigator:
    def __init__(self, tools: ToolExecutor):
        self.tools = tools

    def run(self, incident_id: str) -> AgentState:
        state = AgentState(f"Investigate {incident_id}")
        alert = self._call(state, "get_incident_record", {"incident_id": incident_id})
        if not alert.ok:
            state.answer = f"Investigation incomplete: {alert.error_code}: {alert.error}"
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
        if metrics.ok and metrics.content["samples"]:
            samples = metrics.content["samples"]
            sample = samples[-1]
            values = ", ".join(f"{key}={value}" for key, value in sample.items()
                               if key not in {"minute", "timestamp"})
            evidence.append(f"metrics at {sample['timestamp']}: {values}")
            if len(samples) >= 2 and all(item["cpu_percent"] >= 90 for item in samples[-2:]):
                evidence.append("CPU remained above 90% across two samples")
            if (len(samples) >= 3
                    and all(left["memory_percent"] < right["memory_percent"]
                            for left, right in zip(samples[-3:-1], samples[-2:]))
                    and sample["memory_percent"] >= 90):
                evidence.append(f"memory rose from {samples[-3]['memory_percent']}% "
                                f"to {sample['memory_percent']}%")
            if sample["disk_percent"] >= 95:
                evidence.append(f"disk is {sample['disk_percent']}% used")
        latest_log = None
        if logs.ok:
            entries = logs.content["entries"]
            latest_log = entries[-1] if entries else None
            if latest_log and (latest_log["severity"] in {"ERROR", "WARN"}
                               or info["status"] in {"recovering", "resolved"}):
                evidence.append(f"latest log: {latest_log['message']}")
            if latest_log and latest_log["severity"] == "ERROR":
                releases = [entry for entry in entries[:-1]
                            if "release deployed" in entry["message"].casefold()]
                if releases:
                    evidence.append(f"errors followed release at {releases[-1]['timestamp']}")
        if pod_events and pod_events.ok and pod_events.content["entries"]:
            latest_pod = pod_events.content["entries"][-1]
            evidence.append(f"pod {latest_pod['pod']} event: {latest_pod['reason']}: "
                            f"{latest_pod['message']}")
        if peer_metrics and peer_metrics.ok and peer_metrics.content["samples"]:
            latest_by_service = {}
            for sample in peer_metrics.content["samples"]:
                latest_by_service[sample["service"]] = sample["latency_ms"]
            evidence.append("peer latency: " + ", ".join(
                f"{service}={latency}ms" for service, latency in sorted(latest_by_service.items())))
        for item, alert_result, log_result in related:
            if alert_result.ok:
                detail = (log_result.content["entries"][-1]["message"]
                          if log_result.ok and log_result.content["entries"] else "no log evidence")
                evidence.append(f"separate incident {item['id']} ({item['service']}): {detail}")
        if info["status"] == "healthy":
            state.answer = (f"No active incident for {incident_id}; current observations "
                            "show healthy service status.")
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
        result = self.tools.execute(name, arguments)
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
