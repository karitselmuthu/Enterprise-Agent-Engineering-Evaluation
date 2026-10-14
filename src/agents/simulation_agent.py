"""Baseline investigator that only knows the standard tool executor."""

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
        evidence = []
        if metrics.ok and metrics.content["samples"]:
            sample = metrics.content["samples"][-1]
            values = ", ".join(f"{key}={value}" for key, value in sample.items()
                               if key != "minute")
            evidence.append(f"metrics at minute {sample['minute']}: {values}")
        if logs.ok:
            errors = [entry for entry in logs.content["entries"]
                      if entry["severity"] in {"ERROR", "WARN"}]
            if errors:
                evidence.append(f"latest log: {errors[-1]['message']}")
        if info["status"] == "healthy":
            state.answer = (f"No active incident for {incident_id}; current observations "
                            "show healthy service status.")
        elif not evidence:
            state.answer = f"Insufficient evidence for {incident_id}; verify monitoring and logs."
        else:
            state.answer = (f"Incident {incident_id} ({info['status']}): "
                            + "; ".join(evidence) + ". Investigate the observed symptoms.")
        if not metrics.ok or not logs.ok:
            state.answer += " Some observations were unavailable."
        return state

    def _call(self, state: AgentState, name: str, arguments: dict[str, str]) -> ToolResult:
        state.trace.append({"stage": "selection", "tool": name, "arguments": arguments})
        result = self.tools.execute(name, arguments)
        state.tool_results.append(result)
        state.trace.append({"stage": "execution", "tool": name, "ok": result.ok,
                            "error_code": result.error_code})
        return result
