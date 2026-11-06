from datetime import datetime
from pathlib import Path
import ast
import py_compile
import shutil
import tempfile


class FridayEvolutionEngine:
    """Safely prepare, validate, and manage Friday code proposals."""

    def __init__(self, project_dir):
        self.project_dir = Path(project_dir).resolve()
        self.evolution_dir = self.project_dir / "friday_evolution"
        self.proposals_dir = self.evolution_dir / "proposals"
        self.backups_dir = self.evolution_dir / "backups"

        for directory in (
            self.proposals_dir,
            self.backups_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)

    def _project_file(self, filename):
        """Allow only existing Python files inside the project root."""
        name = Path(filename)

        if name.is_absolute() or len(name.parts) != 1:
            raise ValueError("Only filenames in the project root are allowed.")

        if name.suffix.lower() != ".py":
            raise ValueError("Only Python files are allowed.")

        target = (self.project_dir / name.name).resolve()

        if target.parent != self.project_dir:
            raise ValueError("The target must remain inside the project root.")

        if target.is_symlink():
            raise ValueError("Symbolic-link targets are not allowed.")

        if not target.is_file():
            raise FileNotFoundError(f"Project file not found: {name.name}")

        return target

    def prepare_proposal(self, filename, proposed_code):
        """Save a proposal separately and check its Python syntax."""
        target = self._project_file(filename)

        if not isinstance(proposed_code, str) or not proposed_code.strip():
            raise ValueError("The proposed code is empty.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        proposal = self.proposals_dir / (
            f"{target.stem}_proposal_{timestamp}.py"
        )

        proposal.write_text(proposed_code, encoding="utf-8")

        try:
            ast.parse(proposed_code, filename=str(proposal))

            with tempfile.TemporaryDirectory() as temp_dir:
                py_compile.compile(
                    str(proposal),
                    cfile=str(Path(temp_dir) / "proposal.pyc"),
                    doraise=True,
                )

        except (SyntaxError, py_compile.PyCompileError) as exc:
            return {
                "ok": False,
                "proposal": str(proposal),
                "error": str(exc),
                "message": "Proposal saved, but syntax validation failed.",
            }

        return {
            "ok": True,
            "proposal": str(proposal),
            "target": target.name,
            "message": "Syntax passed. The live file has not been changed.",
        }

    def apply_proposal(self, proposal_path, approved=False):
        """Apply a validated proposal only after explicit approval."""
        if approved is not True:
            raise PermissionError("Explicit approval is required.")

        proposal = Path(proposal_path).resolve()

        if proposal.parent != self.proposals_dir.resolve():
            raise ValueError("Proposal must be inside the proposals directory.")

        if not proposal.is_file() or proposal.suffix.lower() != ".py":
            raise FileNotFoundError("Valid Python proposal not found.")

        stem = proposal.stem
        marker = "_proposal_"

        if marker not in stem:
            raise ValueError("Proposal filename is not recognized.")

        target_name = stem.split(marker, 1)[0] + ".py"
        target = self._project_file(target_name)
        code = proposal.read_text(encoding="utf-8")

        ast.parse(code, filename=str(proposal))

        with tempfile.TemporaryDirectory() as temp_dir:
            py_compile.compile(
                str(proposal),
                cfile=str(Path(temp_dir) / "proposal.pyc"),
                doraise=True,
            )

        original_bytes = target.read_bytes()
        original_text = original_bytes.decode("utf-8")

        # Preserve the original file before touching it.
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup = self.backups_dir / f"{target.stem}_{timestamp}.py"
        shutil.copy2(target, backup)

        # Write and validate a staged copy in the target directory.
        staged = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".py",
                prefix=".friday_stage_",
                dir=self.project_dir,
                delete=False,
            ) as temp_file:
                staged = Path(temp_file.name)
                temp_file.write(code)

            with tempfile.TemporaryDirectory() as temp_dir:
                py_compile.compile(
                    str(staged),
                    cfile=str(Path(temp_dir) / "staged.pyc"),
                    doraise=True,
                )

            # Detect edits made to the live file since approval preparation.
            if target.read_bytes() != original_bytes:
                raise RuntimeError(
                    "Target changed during validation. No replacement made."
                )

            # Atomic replacement after backup and validation.
            staged.replace(target)
            staged = None

            return {
                "ok": True,
                "target": str(target),
                "backup": str(backup),
                "message": "Approved proposal applied successfully.",
            }

        except Exception:
            # If replacement occurred before an error, restore the original.
            if target.exists() and target.read_bytes() != original_bytes:
                with tempfile.NamedTemporaryFile(
                    mode="wb",
                    prefix=".friday_restore_",
                    dir=self.project_dir,
                    delete=False,
                ) as restore_file:
                    restore_path = Path(restore_file.name)
                    restore_file.write(original_bytes)

                restore_path.replace(target)

            raise

        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)

    def rollback(self, filename, backup_path, approved=False):
        """Restore a project-root Python file from its own backup."""
        if approved is not True:
            raise PermissionError("Explicit approval is required.")

        target = self._project_file(filename)
        backup = Path(backup_path).resolve()

        if backup.parent != self.backups_dir.resolve():
            raise ValueError("Backup must belong to Friday's backup directory.")

        if not backup.is_file() or not backup.name.startswith(target.stem + "_"):
            raise ValueError("Backup does not match the requested target.")

        backup_code = backup.read_text(encoding="utf-8")
        ast.parse(backup_code, filename=str(backup))

        with tempfile.TemporaryDirectory() as temp_dir:
            py_compile.compile(
                str(backup),
                cfile=str(Path(temp_dir) / "rollback.pyc"),
                doraise=True,
            )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safety_copy = self.backups_dir / (
            f"{target.stem}_{timestamp}.py"
        )
        shutil.copy2(target, safety_copy)

        with tempfile.NamedTemporaryFile(
            mode="wb",
            prefix=".friday_rollback_",
            dir=self.project_dir,
            delete=False,
        ) as temp_file:
            staged = Path(temp_file.name)
            staged.write_bytes(backup.read_bytes())

        try:
            staged.replace(target)
        finally:
            staged.unlink(missing_ok=True)

        return {
            "ok": True,
            "target": str(target),
            "pre_rollback_backup": str(safety_copy),
            "message": "Rollback completed.",
        }
