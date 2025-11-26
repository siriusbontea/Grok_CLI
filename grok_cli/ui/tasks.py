"""Live task tracker with real-time updates.

Provides a Claude Code-style todo list that updates in real-time
as the agent works through tasks.
"""

from dataclasses import dataclass, field
from enum import Enum
from types import TracebackType
from typing import Literal, Optional, Type

from rich.console import Console, RenderableType
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


class TaskStatus(Enum):
    """Task status states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# Status icons and colors
STATUS_DISPLAY = {
    TaskStatus.PENDING: ("○", "dim"),
    TaskStatus.IN_PROGRESS: ("⟳", "yellow"),
    TaskStatus.COMPLETED: ("✓", "green"),
    TaskStatus.FAILED: ("✗", "red"),
}


@dataclass
class Task:
    """A single task in the tracker."""

    description: str
    status: TaskStatus = TaskStatus.PENDING
    detail: Optional[str] = None


@dataclass
class TaskTracker:
    """Manages a list of tasks with live terminal updates.

    Usage:
        tracker = TaskTracker()
        with tracker.live_display():
            task_id = tracker.add_task("Reading file")
            tracker.start_task(task_id)
            # ... do work ...
            tracker.complete_task(task_id)
    """

    title: str = "Tasks"
    tasks: list[Task] = field(default_factory=list)
    _live: Optional[Live] = field(default=None, repr=False)
    _console: Console = field(default_factory=Console, repr=False)

    def add_task(self, description: str, detail: Optional[str] = None) -> int:
        """Add a new task to the tracker.

        Args:
            description: Task description
            detail: Optional detail text

        Returns:
            Task index (for updating later)
        """
        task = Task(description=description, detail=detail)
        self.tasks.append(task)
        self._refresh()
        return len(self.tasks) - 1

    def start_task(self, task_id: int, detail: Optional[str] = None) -> None:
        """Mark a task as in progress.

        Args:
            task_id: Task index
            detail: Optional updated detail
        """
        if 0 <= task_id < len(self.tasks):
            self.tasks[task_id].status = TaskStatus.IN_PROGRESS
            if detail:
                self.tasks[task_id].detail = detail
            self._refresh()

    def complete_task(self, task_id: int, detail: Optional[str] = None) -> None:
        """Mark a task as completed.

        Args:
            task_id: Task index
            detail: Optional completion detail
        """
        if 0 <= task_id < len(self.tasks):
            self.tasks[task_id].status = TaskStatus.COMPLETED
            if detail:
                self.tasks[task_id].detail = detail
            self._refresh()

    def fail_task(self, task_id: int, error: Optional[str] = None) -> None:
        """Mark a task as failed.

        Args:
            task_id: Task index
            error: Optional error message
        """
        if 0 <= task_id < len(self.tasks):
            self.tasks[task_id].status = TaskStatus.FAILED
            if error:
                self.tasks[task_id].detail = error
            self._refresh()

    def update_detail(self, task_id: int, detail: str) -> None:
        """Update a task's detail text.

        Args:
            task_id: Task index
            detail: New detail text
        """
        if 0 <= task_id < len(self.tasks):
            self.tasks[task_id].detail = detail
            self._refresh()

    def clear(self) -> None:
        """Clear all tasks."""
        self.tasks = []
        self._refresh()

    def _build_display(self) -> Panel:
        """Build the task display panel."""
        content: RenderableType
        if not self.tasks:
            content = Text("No active tasks", style="dim")
        else:
            table = Table(show_header=False, box=None, padding=(0, 1))
            table.add_column("status", width=2)
            table.add_column("task")

            for task in self.tasks:
                icon, color = STATUS_DISPLAY[task.status]
                status_text = Text(icon, style=color)

                task_text = Text(task.description)
                if task.status == TaskStatus.IN_PROGRESS:
                    task_text.stylize("bold")
                elif task.status == TaskStatus.COMPLETED:
                    task_text.stylize("dim")
                elif task.status == TaskStatus.FAILED:
                    task_text.stylize("red")

                if task.detail:
                    task_text.append(f" ({task.detail})", style="dim")

                table.add_row(status_text, task_text)

            content = table

        return Panel(
            content,
            title=f"[bold cyan]{self.title}[/bold cyan]",
            border_style="dim",
            padding=(0, 1),
        )

    def _refresh(self) -> None:
        """Refresh the live display if active."""
        if self._live is not None:
            self._live.update(self._build_display())

    def live_display(self) -> Live:
        """Get a Live context manager for real-time updates.

        Usage:
            with tracker.live_display():
                # Tasks will update in real-time
                pass

        Returns:
            Rich Live context manager
        """
        self._live = Live(
            self._build_display(),
            console=self._console,
            refresh_per_second=4,
            transient=False,  # Keep display after exit
        )
        return self._live

    def print_static(self) -> None:
        """Print tasks without live updates (for final summary)."""
        self._console.print(self._build_display())


class TaskContext:
    """Context manager for a single task within a tracker.

    Usage:
        tracker = TaskTracker()
        with tracker.live_display():
            with TaskContext(tracker, "Processing file") as task:
                # Task is automatically started
                task.update("50% complete")
            # Task is automatically completed
    """

    def __init__(self, tracker: TaskTracker, description: str):
        """Initialize task context.

        Args:
            tracker: Parent task tracker
            description: Task description
        """
        self.tracker = tracker
        self.description = description
        self.task_id: int = -1

    def __enter__(self) -> "TaskContext":
        """Start the task."""
        self.task_id = self.tracker.add_task(self.description)
        self.tracker.start_task(self.task_id)
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> Literal[False]:
        """Complete or fail the task based on exception."""
        if exc_type is not None:
            self.tracker.fail_task(self.task_id, str(exc_val))
        else:
            self.tracker.complete_task(self.task_id)
        return False

    def update(self, detail: str) -> None:
        """Update task detail.

        Args:
            detail: New detail text
        """
        self.tracker.update_detail(self.task_id, detail)
