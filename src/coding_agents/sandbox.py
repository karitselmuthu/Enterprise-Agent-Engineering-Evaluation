"""Run generated code only in a resource-limited Docker container."""

from dataclasses import dataclass
import os
from pathlib import Path
import selectors
import subprocess
from tempfile import TemporaryDirectory
from time import monotonic
from uuid import uuid4


class SandboxUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int


class DockerSandbox:
    def __init__(self, image: str = "python:3.12-alpine", timeout_seconds: int = 15):
        if timeout_seconds < 1:
            raise ValueError("timeout_seconds must be positive")
        self.image = image
        self.timeout_seconds = timeout_seconds

    def build_command(self, script: Path, name: str) -> list[str]:
        return [
                "docker", "run", "--rm", "-i", "--name", name, "--pull", "never",
                "--network", "none", "--read-only", "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges", "--user", "65534:65534",
                "--memory", "128m", "--memory-swap", "128m", "--cpus", "0.5",
                "--pids-limit", "32", "--ulimit", "nofile=64:64",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
                "--mount", f"type=bind,src={script},dst=/work/analyze.py,readonly",
                "--workdir", "/work", self.image,
                "python", "-I", "-B", "/work/analyze.py",
        ]

    def run(self, source: str, input_text: str) -> SandboxResult:
        input_bytes = input_text.encode("utf-8")
        if len(input_bytes) > 1_048_576:
            raise ValueError("Log input exceeds 1 MiB")
        with TemporaryDirectory(prefix="eae-code-") as directory:
            script = Path(directory) / "analyze.py"
            script.write_text(source, encoding="utf-8")
            script.chmod(0o444)
            name = f"eae-code-{uuid4().hex}"
            command = self.build_command(script, name)
            input_file = Path(directory) / "input.log"
            input_file.write_bytes(input_bytes)
            deadline = monotonic() + self.timeout_seconds
            try:
                with input_file.open("rb") as input_stream:
                    process = subprocess.Popen(
                        command, stdin=input_stream, stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE)
                    try:
                        outputs = {"stdout": bytearray(), "stderr": bytearray()}
                        with selectors.DefaultSelector() as selector:
                            selector.register(process.stdout, selectors.EVENT_READ, "stdout")
                            selector.register(process.stderr, selectors.EVENT_READ, "stderr")
                            while selector.get_map():
                                remaining = deadline - monotonic()
                                if remaining <= 0:
                                    raise SandboxUnavailable("Sandbox execution timed out")
                                for key, _ in selector.select(timeout=remaining):
                                    chunk = os.read(key.fileobj.fileno(), 4096)
                                    if not chunk:
                                        selector.unregister(key.fileobj)
                                        continue
                                    output = outputs[key.data]
                                    output.extend(chunk)
                                    if len(output) > 65_536:
                                        raise SandboxUnavailable("Sandbox output exceeded 64 KiB")
                        process.wait(timeout=max(0.1, deadline - monotonic()))
                    except (SandboxUnavailable, subprocess.TimeoutExpired) as exc:
                        process.kill()
                        process.wait(timeout=5)
                        self._remove_container(name)
                        raise SandboxUnavailable(str(exc)) from exc
            except FileNotFoundError as exc:
                raise SandboxUnavailable("Docker CLI is not installed") from exc
            stdout = outputs["stdout"].decode("utf-8", errors="replace")
            stderr = outputs["stderr"].decode("utf-8", errors="replace")
            if process.returncode in {125, 126, 127}:
                raise SandboxUnavailable(stderr.strip() or "Docker unavailable")
            return SandboxResult(stdout, stderr, process.returncode)

    @staticmethod
    def _remove_container(name: str) -> None:
        try:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True,
                           timeout=5, check=False)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
