import ast
import json
from pathlib import Path

import requests

from friday_config import OLLAMA_URL, LLM_MODEL, PROJECT_DIR
from friday_evolution_engine import FridayEvolutionEngine


class FridaySelfUpgrade:
    """Generate and validate code-improvement proposals for Friday."""

    def __init__(self):
        self.project_dir = Path(PROJECT_DIR).resolve()
        self.engine = FridayEvolutionEngine(self.project_dir)

    def generate_proposal(self, filename, improvement_request):
        """Ask Ollama to improve a project file without changing it."""

        name = Path(filename)

        if (
            name.is_absolute()
            or len(name.parts) != 1
            or name.suffix.lower() != ".py"
        ):
            raise ValueError(
                "Specify a Python filename in the project root."
            )

        source_path = (self.project_dir / name.name).resolve()

        if source_path.parent != self.project_dir:
            raise ValueError("File must remain inside the project root.")

        if source_path.is_symlink() or not source_path.is_file():
            raise ValueError("A regular project Python file is required.")

        if name.name == Path(__file__).name:
            raise ValueError(
                "Friday cannot upgrade the active upgrade generator."
            )

        source_bytes = source_path.read_bytes()
        has_utf8_bom = source_bytes.startswith(b"\xef\xbb\xbf")

        source_code = source_bytes.decode("utf-8-sig")

        if len(source_code) > 24000:
            raise ValueError(
                "File is too large for this first upgrade workflow."
            )

        if not isinstance(improvement_request, str):
            raise ValueError("Describe the requested improvement.")

        improvement_request = improvement_request.strip()

        if not improvement_request or len(improvement_request) > 1000:
            raise ValueError(
                "The improvement request must contain 1–1000 characters."
            )

        system_prompt = """
You are Friday's Python code-improvement assistant.

Return one complete replacement Python file as plain text.
Do not use Markdown fences or explanations.
Preserve existing functionality unless the requested improvement
requires a change.
Do not remove unrelated features.
Do not add destructive commands, credential collection,
security bypasses, or hidden network activity.
If the requested change cannot be implemented safely,
return the original code unchanged.
"""

        user_prompt = (
            "Requested improvement:\n"
            f"{improvement_request}\n\n"
            f"Filename: {name.name}\n\n"
            "Current source code follows:\n"
            "<source_code>\n"
            f"{source_code}\n"
            "</source_code>\n\n"
            "Return the complete proposed replacement file."
        )

        payload = {
            "model": LLM_MODEL,
            "stream": False,
            "think": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "options": {"temperature": 0.2},
        }

        response = requests.post(
            OLLAMA_URL,
            json=payload,
            timeout=180,
        )
        response.raise_for_status()

        result = response.json()
        proposed_code = result.get("message", {}).get("content", "")

        if not isinstance(proposed_code, str) or not proposed_code.strip():
            raise ValueError("Ollama returned an empty proposal.")

        # Normalize BOMs before extracting Markdown fences.
        proposed_code = proposed_code.lstrip("\ufeff").strip()

        # Extract Python code if Ollama adds Markdown fences.
        import re

        matches = re.findall(
            r"```(?:python|py)?[ \t]*\r?\n(.*?)```",
            proposed_code,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if matches:
            proposed_code = max(matches, key=len).strip()
        else:
            # Remove common model-generated filename/title headers.
            lines = proposed_code.splitlines()

            if (
                len(lines) >= 2
                and lines[0].strip().lower().endswith(".py")
                and lines[1].strip()
                and set(lines[1].strip()) <= {"="}
            ):
                proposed_code = "\n".join(lines[2:]).strip()

        # Remove any BOM exposed by extraction before parsing.
        proposed_code = proposed_code.lstrip("\ufeff").strip()

        if not proposed_code:
            raise ValueError("Ollama returned an empty proposal.")

        # Reject proposals that remove existing top-level definitions.
        original_tree = ast.parse(source_code, filename=name.name)
        proposed_tree = ast.parse(proposed_code, filename=name.name)

        def top_level_names(tree):
            names = set()

            def collect_target(target):
                if isinstance(target, ast.Name):
                    names.add(target.id)
                elif isinstance(target, (ast.Tuple, ast.List)):
                    for element in target.elts:
                        collect_target(element)

            for node in tree.body:
                if isinstance(
                    node,
                    (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
                ):
                    names.add(node.name)

                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        collect_target(target)

                elif isinstance(node, ast.AnnAssign):
                    collect_target(node.target)

                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        names.add(alias.asname or alias.name.split(".")[0])

            return names

        missing_names = sorted(
            top_level_names(original_tree) - top_level_names(proposed_tree)
        )

        if missing_names:
            raise ValueError(
                "Proposal removes existing top-level names: "
                + ", ".join(missing_names)
            )

        if proposed_code == source_code.strip():
            return {
                "ok": False,
                "message": "No code changes were proposed.",
            }

        # Basic syntax check before saving a proposal.
        ast.parse(proposed_code, filename=name.name)

        validation = self.engine.prepare_proposal(
            name.name,
            proposed_code,
        )

        return {
            **validation,
            "model": LLM_MODEL,
            "original": str(source_path),
            "message": (
                "Proposal generated and syntax-checked. "
                "The original file remains unchanged."
                if validation.get("ok")
                else validation.get("message", "Validation failed.")
            ),
        }


def main():
    upgrader = FridaySelfUpgrade()

    print("=" * 55)
    print("FRIDAY SELF-UPGRADE")
    print("=" * 55)
    print("Local model:", LLM_MODEL)
    print("Original files will not be modified.")
    print()

    filename = input("Python filename to improve: ").strip()
    request = input("What should Friday improve? ").strip()

    try:
        result = upgrader.generate_proposal(filename, request)
        print(json.dumps(result, indent=2))

        if result.get("ok"):
            print()
            print("Review the proposal before approving any upgrade.")

    except (ValueError, SyntaxError, requests.RequestException) as exc:
        print("Upgrade proposal failed:", exc)


if __name__ == "__main__":
    main()
