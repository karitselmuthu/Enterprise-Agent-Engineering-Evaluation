"""Generate, validate, and test a log analysis script in Docker."""

from dataclasses import dataclass
import json
from typing import Protocol
from urllib.request import Request, urlopen

from .sandbox import DockerSandbox, SandboxResult
from .validator import CodeValidationError, validate_python


class CodeGenerator(Protocol):
    def generate(self, request: str) -> str: ...


class TemplateLogGenerator:
    def generate(self, request: str) -> str:
        if "log" not in request.casefold():
            raise ValueError("Request must ask to analyze logs")
        return '''import json
import sys

LEVELS = ("ERROR", "WARN", "INFO")

def analyze(lines):
    counts = {level: 0 for level in LEVELS}
    for line in lines:
        words = line.upper().split()
        for level in LEVELS:
            if level in words:
                counts[level] += 1
                break
    return counts

if __name__ == "__main__":
    print(json.dumps(analyze(sys.stdin.read().splitlines()), sort_keys=True))
'''


class OllamaCodeGenerator:
    """Optional local-model generator; all output still passes validation."""

    def __init__(self, model: str, url: str = "http://127.0.0.1:11434/api/chat"):
        if not model:
            raise ValueError("model is required")
        self.model, self.url = model, url

    def generate(self, request: str) -> str:
        payload = {
            "model": self.model, "stream": False,
            "messages": [
                {"role": "system", "content": (
                    "Write only Python source for a stdin-to-stdout JSON log analyzer. "
                    "Use only json and sys imports. Count ERROR, WARN, and INFO lines. "
                    "Do not read files, access the network, or add markdown fences.")},
                {"role": "user", "content": request},
            ],
        }
        http_request = Request(
            self.url, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(http_request, timeout=30) as response:
            source = json.load(response).get("message", {}).get("content", "")
        if not isinstance(source, str) or not source.strip():
            raise ValueError("Model returned no source code")
        source = source.strip()
        if source.startswith("```"):
            lines = source.splitlines()
            if lines[-1].strip() == "```":
                source = "\n".join(lines[1:-1])
        return source


@dataclass(frozen=True)
class CodeAgentReport:
    ok: bool
    source: str
    sample_result: dict | None = None
    tests_passed: bool = False
    error: str | None = None


class LogAnalysisCodeAgent:
    def __init__(self, generator: CodeGenerator | None = None,
                 sandbox: DockerSandbox | None = None):
        self.generator = generator or TemplateLogGenerator()
        self.sandbox = sandbox or DockerSandbox()

    @staticmethod
    def _parse(result: SandboxResult) -> dict:
        if result.exit_code:
            raise RuntimeError(result.stderr.strip() or
                               f"Script exited with status {result.exit_code}")
        try:
            output = json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Script did not return JSON") from exc
        if not isinstance(output, dict):
            raise RuntimeError("Script output must be a JSON object")
        return output

    def run(self, request: str, application_logs: str) -> CodeAgentReport:
        source = ""
        try:
            source = self.generator.generate(request)
            validate_python(source)
            sample = self._parse(self.sandbox.run(source, application_logs))
            expected = {"ERROR": 2, "WARN": 1, "INFO": 0}
            fixture = "ERROR failed\nWARN slow\nERROR retry failed\n"
            observed = self._parse(self.sandbox.run(source, fixture))
            if observed != expected:
                raise RuntimeError(f"Sandbox test failed: expected {expected}, got {observed}")
            return CodeAgentReport(True, source, sample, tests_passed=True)
        except (ValueError, CodeValidationError, RuntimeError) as exc:
            return CodeAgentReport(False, source, error=str(exc))
