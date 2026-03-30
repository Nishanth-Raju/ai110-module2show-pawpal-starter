"""
pawpal_system.py — Core scheduling logic for PawPal+.

Classes
-------
Task          : A single pet care task with time, priority, and daily state.
Pet           : Basic pet information.
Owner         : Pet owner with a time budget and a list of tasks.
ScheduledTask : A Task assigned an actual start time and an explanation.
Plan          : The output of the scheduler — scheduled and skipped tasks.
Scheduler     : Builds a daily Plan from an Owner's tasks and constraints.
"""

from datetime import datetime, timedelta


class Task:
    """A single pet care task.

    Attributes
    ----------
    title : str
        Short name for the task (e.g. "Morning walk").
    duration_minutes : int
        How long the task takes.
    priority : str
        One of "low", "medium", or "high".
    category : str
        Type of care (e.g. "walk", "feeding", "meds"). Defaults to "general".
    required : bool
        If True, the task is always scheduled first regardless of priority.
    recurs_daily : bool
        If True, the task resets each day and can be skipped with skip_today().
    start_time : str
        Desired start time in "HH:MM AM/PM" format (e.g. "08:00 AM").
    completed : bool
        Set to True when the owner marks the task done. Reset each day.
    skipped_today : bool
        Set to True to skip a recurring task for today only. Reset each day.
    """

    def __init__(
        self,
        title: str,
        duration_minutes: int,
        priority: str,
        category: str = "general",
        required: bool = False,
        recurs_daily: bool = False,
        start_time: str = "8:00 AM",
    ):
        self.title = title
        self.duration_minutes = duration_minutes
        self.priority = priority  # "low", "medium", "high"
        self.category = category
        self.required = required
        self.recurs_daily = recurs_daily
        self.start_time = start_time
        self.completed: bool = False
        self.skipped_today: bool = False

    def priority_value(self) -> int:
        """Return a numeric priority for sorting (higher = more important).

        Returns
        -------
        int
            3 for "high", 2 for "medium", 1 for "low", 0 for unknown.
        """
        mapping = {"high": 3, "medium": 2, "low": 1}
        return mapping.get(self.priority, 0)


class Pet:
    """Basic pet information.

    Attributes
    ----------
    name : str
        The pet's name.
    species : str
        The pet's species (e.g. "dog", "cat").
    """

    def __init__(self, name: str, species: str):
        self.name = name
        self.species = species


class Owner:
    """A pet owner with a daily time budget and a list of care tasks.

    Attributes
    ----------
    name : str
        The owner's name.
    available_minutes : int
        Total minutes the owner has available for pet care today.
    pet : Pet
        The owner's pet.
    tasks : list[Task]
        All care tasks the owner manages.
    """

    def __init__(self, name: str, available_minutes: int):
        self.name = name
        self.available_minutes = available_minutes
        self.pet: Pet = None
        self.tasks: list[Task] = []

    def add_task(self, task: Task) -> None:
        """Add a task to the owner's task list."""
        self.tasks.append(task)

    def remove_task(self, title: str) -> None:
        """Remove a task by title. No-op if the title is not found."""
        self.tasks = [t for t in self.tasks if t.title != title]

    def mark_complete(self, title: str) -> None:
        """Mark a task as completed for today."""
        for task in self.tasks:
            if task.title == title:
                task.completed = True

    def skip_today(self, title: str) -> None:
        """Skip a recurring task for today only. Non-recurring tasks are unaffected."""
        for task in self.tasks:
            if task.title == title and task.recurs_daily:
                task.skipped_today = True

    def reset_day(self) -> None:
        """Reset all daily state — clears completed and skipped_today on every task."""
        for task in self.tasks:
            task.skipped_today = False
            task.completed = False

    def filter_tasks(self, completed: bool) -> list:
        """Return tasks filtered by completion status.

        Parameters
        ----------
        completed : bool
            Pass True to get completed tasks, False to get pending tasks.

        Returns
        -------
        list[Task]
            Tasks whose completed field matches the given value.
        """
        return [t for t in self.tasks if t.completed == completed]


class ScheduledTask:
    """A Task that has been assigned an actual start time and an explanation.

    Attributes
    ----------
    task : Task
        The underlying task.
    start_time : str
        The actual scheduled start time (may differ from task.start_time if
        shifted forward to avoid overlap).
    reason : str
        Human-readable explanation of why and when this task was scheduled.
    """

    def __init__(self, task: Task, start_time: str, reason: str):
        self.task = task
        self.start_time = start_time
        self.reason = reason


class Plan:
    """The output of the Scheduler.

    Attributes
    ----------
    scheduled : list[ScheduledTask]
        Tasks accepted into the plan, in scheduled order.
    skipped : list[Task]
        Tasks excluded because they would exceed the owner's time budget.
    total_minutes : int
        Sum of durations of all scheduled tasks.
    """

    def __init__(self):
        self.scheduled: list[ScheduledTask] = []
        self.skipped: list[Task] = []
        self.total_minutes: int = 0

    def summary(self) -> str:
        """Return a plain-text summary of the plan.

        Returns
        -------
        str
            Formatted list of scheduled and skipped tasks with times and reasons.
        """
        lines = []
        if self.scheduled:
            lines.append("Scheduled tasks:")
            for st in self.scheduled:
                lines.append(
                    f"  {st.start_time} — {st.task.title} ({st.task.duration_minutes} min) | {st.reason}"
                )
        if self.skipped:
            lines.append("Skipped tasks (not enough time):")
            for t in self.skipped:
                lines.append(
                    f"  - {t.title} ({t.duration_minutes} min, {t.priority} priority)"
                )
        lines.append(f"Total time used: {self.total_minutes} min")
        return "\n".join(lines)


class Scheduler:
    """Builds a daily care Plan from an Owner's tasks and time budget.

    Scheduling rules
    ----------------
    1. Completed and skipped-today tasks are excluded before scheduling begins.
    2. Remaining tasks are sorted by desired start time, then required status,
       then priority (high to low), then duration (shorter first as tiebreaker).
    3. Tasks are greedily accepted if they fit within available_minutes.
    4. If a task's desired start time overlaps with the end of the previous task,
       its actual start is shifted forward to avoid the overlap.

    Attributes
    ----------
    owner : Owner
        Provides the time budget.
    pet : Pet
        The pet being cared for.
    tasks : list[Task]
        Tasks to consider for scheduling.
    """

    def __init__(self, owner: Owner, pet: Pet, tasks: list[Task]):
        self.owner = owner
        self.pet = pet
        self.tasks = tasks

    def build_plan(self) -> Plan:
        """Build and return a daily Plan.

        Returns
        -------
        Plan
            Contains scheduled tasks (with start times and reasons) and
            any tasks that were skipped due to the time budget.
        """
        plan = Plan()
        sorted_tasks = [
            t for t in self._sort_tasks() if not t.completed and not t.skipped_today
        ]
        used_minutes = 0
        current_time = None
        rank = 0

        for task in sorted_tasks:
            if self._fits_in_time(task, used_minutes):
                rank += 1
                desired_start = datetime.strptime(task.start_time, "%I:%M %p")
                actual_start = (
                    max(desired_start, current_time) if current_time else desired_start
                )
                shifted = actual_start != desired_start
                remaining_before = self.owner.available_minutes - used_minutes
                reason = self._explain(
                    task,
                    rank,
                    len(sorted_tasks),
                    used_minutes,
                    remaining_before,
                    shifted,
                )
                plan.scheduled.append(
                    ScheduledTask(task, actual_start.strftime("%I:%M %p"), reason)
                )
                current_time = actual_start + timedelta(minutes=task.duration_minutes)
                used_minutes += task.duration_minutes
            else:
                plan.skipped.append(task)

        plan.total_minutes = used_minutes
        return plan

    def _sort_tasks(self) -> list[Task]:
        """Return tasks sorted by start time, required status, priority, then duration."""
        return sorted(
            self.tasks,
            key=lambda t: (
                datetime.strptime(t.start_time, "%I:%M %p"),
                not t.required,
                -t.priority_value(),
                t.duration_minutes,
            ),
        )

    def _fits_in_time(self, task: Task, used_minutes: int) -> bool:
        """Return True if adding this task would not exceed the owner's time budget."""
        return used_minutes + task.duration_minutes <= self.owner.available_minutes

    def _explain(
        self,
        task: Task,
        rank: int,
        total: int,
        used_minutes: int,
        remaining_minutes: int,
        shifted: bool,
    ) -> str:
        """Build a human-readable reason string for why a task was scheduled.

        Parameters
        ----------
        task : Task
            The task being scheduled.
        rank : int
            Position of this task in the accepted schedule (1-based).
        total : int
            Total number of eligible tasks considered.
        used_minutes : int
            Minutes already used before this task.
        remaining_minutes : int
            Minutes remaining in the budget when this task was accepted.
        shifted : bool
            True if the actual start was pushed forward to avoid overlap.

        Returns
        -------
        str
            A sentence-level explanation of the scheduling decision.
        """
        parts = []

        if task.required:
            parts.append(
                "Marked as required — always scheduled regardless of priority."
            )
        else:
            parts.append(
                f"Ranked #{rank} of {total} tasks by priority ({task.priority})."
            )

        parts.append(
            f"Takes {task.duration_minutes} min; {remaining_minutes} min were available when scheduled."
        )

        if shifted:
            parts.append(
                "Start shifted forward to avoid overlap with the previous task."
            )
        elif used_minutes == 0:
            parts.append("Placed first in the day.")
        else:
            parts.append(f"Placed after {used_minutes} min of earlier tasks.")

        return " ".join(parts)
