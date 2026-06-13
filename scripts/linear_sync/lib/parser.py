from dataclasses import dataclass, field
from pathlib import Path
import re
import fcntl
from typing import List, Optional, Union


@dataclass
class Task:
    id: str
    title: str
    linear_id: Optional[str] = None
    status: str = "todo"
    priority: Optional[int] = None
    labels: List[str] = field(default_factory=list)
    conclusion: str = ""

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "linear_id": self.linear_id,
            "status": self.status,
            "priority": self.priority,
            "labels": self.labels,
            "conclusion": self.conclusion,
        }


class PlanParser:
    """
    Parses Markdown Blueprint files to extract Task information.
    """

    TASK_HEADING_RE = re.compile(r"####\s+(?P<title>.*)", re.IGNORECASE)
    CONCLUSION_RE = re.compile(r"\*\*Conclusion\*\*:\s*(?P<conclusion>.*)", re.IGNORECASE)

    def parse(self, file_path: Union[str, Path]) -> List[Task]:
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Blueprint file not found: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        tasks = []

        # Split content into blocks based on task headings
        blocks = re.split(r"(?=^####\s+Task)", content, flags=re.MULTILINE)

        for block in blocks:
            if not block.strip() or not block.strip().startswith("#### Task"):
                continue

            task = self._parse_block(block)
            if task:
                tasks.append(task)
            else:
                # print(f"DEBUG: Failed to parse block: {block[:50]}...")
                pass

        return tasks

    def _parse_block(self, block: str) -> Optional[Task]:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            return None

        # 1. Extract Title from the first line
        title_match = self.TASK_HEADING_RE.search(lines[0])
        if not title_match:
            return None
        title = title_match.group("title").strip()

        task_id = ""
        linear_id = None
        status = "todo"
        priority = None
        labels = []
        conclusion = ""

        # 2. Parse metadata and conclusion from subsequent lines
        for line in lines[1:]:
            # Check for Conclusion Line first (more specific)
            conclusion_match = self.CONCLUSION_RE.search(line)
            if conclusion_match:
                conclusion = conclusion_match.group("conclusion").strip()
                continue

            # Parse potential metadata line
            # Metadata lines usually look like "- **Key**: Value" or "Key: Value"
            if ":" in line:
                parts = [p.strip() for p in line.split("|")]
                is_metadata_line = False
                for part in parts:
                    if ":" in part:
                        k, v = part.split(":", 1)
                        k, v = k.strip(), v.strip()
                        # Clean up prefix like '- ' or '|-' and markdown bold markers
                        k = re.sub(r"^[|\-]\s*", "", k)
                        k = re.sub(r"\*\*", "", k)  # Remove ** bold markers
                        v = re.sub(r"^[\[\(](.*?)[\]\)]$", r"\1", v)

                        if k == "Task-ID":
                            task_id = v
                            is_metadata_line = True
                        elif k == "Linear-Issue":
                            if v.lower() in ["none", "n/a", "null"] or "minor plan" in v.lower():
                                linear_id = None
                            else:
                                linear_id = v
                            is_metadata_line = True
                        elif k == "Status":
                            status = v.lower()
                            is_metadata_line = True
                        elif k == "Priority":
                            try:
                                priority = int(v)
                            except ValueError:
                                priority = None
                            is_metadata_line = True
                        elif k == "Labels":
                            # Split by comma or pipe, clean whitespace
                            labels = [l.strip() for l in re.split(r"[,|]", v) if l.strip()]
                            is_metadata_line = True
                
                if is_metadata_line:
                    continue

        if not task_id:
            return None

        return Task(
            id=task_id,
            title=title,
            linear_id=linear_id,
            status=status,
            priority=priority,
            labels=labels,
            conclusion=conclusion
        )

    def update_task_metadata_in_file(self, file_path: Union[str, Path], task_id: str, **updates) -> bool:
        """
        마크다운 파일 내에서 특정 Task-ID의 메타데이터(Status, Priority, Labels)를 안전하게 교체합니다.
        
        updates: {"status": "in_progress", "priority": 2, "labels": ["infra", "api"]}
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Blueprint file not found: {file_path}")

        # File locking for concurrent access safety
        lock_path = file_path.with_suffix(file_path.suffix + ".lock")
        lock_fd = open(lock_path, "w")
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines(keepends=True)

            target_positions = []
            for i, line in enumerate(lines):
                if f"Task-ID: {task_id}" in line:
                    target_positions.append(i)

            if not target_positions:
                print(f"  ⚠️ No metadata line found for task '{task_id}' in {file_path.name}")
                return False

            updated_count = 0
            for i in reversed(target_positions):
                old_line = lines[i]
                new_line = old_line
                
                for key, value in updates.items():
                    field_name = key.capitalize()
                    if key == "status": field_name = "Status"
                    
                    # Regex to match | Key: Value | or | Key: Value
                    # This is a bit complex because of the pipe separator and potential bold markers
                    pattern = rf"(?P<prefix>\|\s*|\-\s*)?(?P<bold>\*\*)?{field_name}(?P<bold_end>\*\*)?:\s*(?P<old_value>[^|]+)"
                    
                    def replacement(m):
                        prefix = m.group("prefix") or ""
                        bold = m.group("bold") or ""
                        bold_end = m.group("bold_end") or ""
                        
                        new_val_str = str(value)
                        if key == "labels" and isinstance(value, list):
                            new_val_str = ", ".join(value)
                        
                        return f"{prefix}{bold}{field_name}{bold_end}: {new_val_str}"

                    new_line = re.sub(pattern, replacement, new_line)

                if new_line != old_line:
                    lines[i] = new_line
                    updated_count += 1

            if updated_count == 0:
                return False

            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            try:
                backup_path.write_text(content, encoding="utf-8")
            except OSError:
                pass

            file_path.write_text("".join(lines), encoding="utf-8")
            print(f"  ✅ Updated {updated_count} metadata fields for task '{task_id}' in {file_path.name}")
            return True
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
            if lock_path.exists():
                try:
                    lock_path.unlink()
                except OSError:
                    pass

    def update_task_conclusion_in_file(self, file_path: Union[str, Path], task_id: str, conclusion: str) -> bool:
        """
        마크다운 파일 내에서 특정 Task-ID의 Conclusion 필드를 교체합니다.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Blueprint file not found: {file_path}")

        # File locking for concurrent access safety
        lock_path = file_path.with_suffix(file_path.suffix + ".lock")
        lock_fd = open(lock_path, "w")
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            
            content = file_path.read_text(encoding="utf-8")
            lines = content.splitlines(keepends=True)

            target_idx = -1
            for i, line in enumerate(lines):
                if f"Task-ID: {task_id}" in line or f"Task-ID: [{task_id}]" in line:
                    target_idx = i
                    break

            if target_idx == -1:
                print(f"  ⚠️ No Task-ID found for task '{task_id}' in {file_path.name}")
                return False

            # Find the conclusion line below the task metadata line (stop if we hit next task heading)
            conclusion_idx = -1
            for idx in range(target_idx + 1, len(lines)):
                line = lines[idx]
                if "#### Task" in line:
                    break
                if "Conclusion" in line:
                    conclusion_idx = idx
                    break

            if conclusion_idx == -1:
                print(f"  ⚠️ No Conclusion line found for task '{task_id}' in {file_path.name}")
                return False

            old_line = lines[conclusion_idx]
            prefix_match = re.match(r"(?P<prefix>.*?\*\*Conclusion\*\*:\s*)", old_line, re.IGNORECASE)
            if not prefix_match:
                return False

            new_line = prefix_match.group("prefix") + conclusion + "\n"
            if new_line == old_line:
                return True  # Already identical

            lines[conclusion_idx] = new_line

            # Create backup
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            try:
                backup_path.write_text(content, encoding="utf-8")
            except OSError:
                pass

            file_path.write_text("".join(lines), encoding="utf-8")
            print(f"  ✅ Updated conclusion for task '{task_id}' in {file_path.name}")
            return True
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            lock_fd.close()
            if lock_path.exists():
                try:
                    lock_path.unlink()
                except OSError:
                    pass

