import pytest
from pawpal_system import Task, Pet, Owner, Scheduler, Plan


# --- Fixtures ---


def make_owner(minutes=120):
    owner = Owner(name="Jordan", available_minutes=minutes)
    owner.pet = Pet(name="Mochi", species="dog")
    return owner


def make_task(
    title="Walk", duration=20, priority="high", required=False, start_time="8:00 AM"
):
    return Task(
        title=title,
        duration_minutes=duration,
        priority=priority,
        required=required,
        start_time=start_time,
    )


# --- Task tests ---


def test_priority_value_high():
    assert make_task(priority="high").priority_value() == 3


def test_priority_value_medium():
    assert make_task(priority="medium").priority_value() == 2


def test_priority_value_low():
    assert make_task(priority="low").priority_value() == 1


# --- Owner tests ---


def test_add_task():
    owner = make_owner()
    task = make_task()
    owner.add_task(task)
    assert task in owner.tasks


def test_remove_task():
    owner = make_owner()
    task = make_task(title="Feeding")
    owner.add_task(task)
    owner.remove_task("Feeding")
    assert task not in owner.tasks


def test_remove_task_nonexistent_does_not_raise():
    owner = make_owner()
    owner.remove_task("Ghost Task")  # should not raise


# --- Scheduling: priority ordering ---


def test_high_priority_scheduled_before_low():
    owner = make_owner(minutes=120)
    tasks = [
        make_task(title="Low task", duration=20, priority="low"),
        make_task(title="High task", duration=20, priority="high"),
    ]
    plan = Scheduler(owner, owner.pet, tasks).build_plan()
    titles = [st.task.title for st in plan.scheduled]
    assert titles.index("High task") < titles.index("Low task")


# --- Scheduling: required tasks come first ---


def test_required_task_scheduled_before_high_priority():
    owner = make_owner(minutes=120)
    tasks = [
        make_task(title="High task", duration=20, priority="high", required=False),
        make_task(title="Required task", duration=20, priority="low", required=True),
    ]
    plan = Scheduler(owner, owner.pet, tasks).build_plan()
    titles = [st.task.title for st in plan.scheduled]
    assert titles.index("Required task") < titles.index("High task")


# --- Scheduling: time constraint ---


def test_task_skipped_when_no_time():
    owner = make_owner(minutes=30)
    tasks = [
        make_task(title="Short task", duration=20, priority="high"),
        make_task(title="Long task", duration=60, priority="high"),
    ]
    plan = Scheduler(owner, owner.pet, tasks).build_plan()
    scheduled_titles = [st.task.title for st in plan.scheduled]
    skipped_titles = [t.title for t in plan.skipped]
    assert "Short task" in scheduled_titles
    assert "Long task" in skipped_titles


def test_total_minutes_does_not_exceed_available():
    owner = make_owner(minutes=60)
    tasks = [
        make_task(title=f"Task {i}", duration=25, priority="high") for i in range(4)
    ]
    plan = Scheduler(owner, owner.pet, tasks).build_plan()
    assert plan.total_minutes <= owner.available_minutes


# --- Scheduling: all tasks fit ---


def test_all_tasks_scheduled_when_time_is_sufficient():
    owner = make_owner(minutes=999)
    tasks = [
        make_task(title=f"Task {i}", duration=10, priority="medium") for i in range(5)
    ]
    plan = Scheduler(owner, owner.pet, tasks).build_plan()
    assert len(plan.scheduled) == 5
    assert len(plan.skipped) == 0


# --- Scheduling: empty task list ---


def test_empty_task_list_produces_empty_plan():
    owner = make_owner()
    plan = Scheduler(owner, owner.pet, []).build_plan()
    assert plan.scheduled == []
    assert plan.skipped == []
    assert plan.total_minutes == 0


# --- Completion and filtering ---


def test_mark_complete():
    owner = make_owner()
    task = make_task(title="Feeding")
    owner.add_task(task)
    owner.mark_complete("Feeding")
    assert task.completed is True


def test_filter_tasks_completed():
    owner = make_owner()
    done = make_task(title="Done task")
    pending = make_task(title="Pending task")
    owner.add_task(done)
    owner.add_task(pending)
    owner.mark_complete("Done task")
    assert owner.filter_tasks(completed=True) == [done]
    assert owner.filter_tasks(completed=False) == [pending]


def test_completed_task_excluded_from_plan():
    owner = make_owner(minutes=120)
    task = make_task(title="Walk")
    owner.add_task(task)
    owner.mark_complete("Walk")
    plan = Scheduler(owner, owner.pet, owner.tasks).build_plan()
    titles = [st.task.title for st in plan.scheduled]
    assert "Walk" not in titles


# --- Recurring tasks ---


def test_recurring_task_skipped_today():
    owner = make_owner(minutes=120)
    task = Task(
        title="Morning walk", duration_minutes=20, priority="high", recurs_daily=True
    )
    owner.add_task(task)
    owner.skip_today("Morning walk")
    plan = Scheduler(owner, owner.pet, owner.tasks).build_plan()
    titles = [st.task.title for st in plan.scheduled]
    assert "Morning walk" not in titles


def test_skip_today_does_not_affect_non_recurring():
    owner = make_owner(minutes=120)
    task = make_task(title="One-time task")  # recurs_daily=False by default
    owner.add_task(task)
    owner.skip_today("One-time task")
    assert task.skipped_today is False  # skip_today only works on recurring tasks


def test_reset_day_clears_skipped_today():
    owner = make_owner(minutes=120)
    task = Task(
        title="Evening walk", duration_minutes=20, priority="medium", recurs_daily=True
    )
    owner.add_task(task)
    owner.skip_today("Evening walk")
    owner.reset_day()
    assert task.skipped_today is False


def test_reset_day_restores_recurring_task_to_plan():
    owner = make_owner(minutes=120)
    task = Task(
        title="Feeding", duration_minutes=10, priority="high", recurs_daily=True
    )
    owner.add_task(task)
    owner.skip_today("Feeding")
    owner.reset_day()
    plan = Scheduler(owner, owner.pet, owner.tasks).build_plan()
    titles = [st.task.title for st in plan.scheduled]
    assert "Feeding" in titles


def test_reset_day_clears_completed_on_non_recurring():
    owner = make_owner()
    task = make_task(title="One-time task")
    owner.add_task(task)
    owner.mark_complete("One-time task")
    owner.reset_day()
    assert task.completed is False


def test_reset_day_clears_completed_on_recurring():
    owner = make_owner()
    task = Task(
        title="Daily meds", duration_minutes=5, priority="high", recurs_daily=True
    )
    owner.add_task(task)
    owner.mark_complete("Daily meds")
    owner.reset_day()
    assert task.completed is False  # recurring tasks also reset completion each day


# --- Plan summary ---


def test_summary_returns_string():
    owner = make_owner(minutes=60)
    tasks = [make_task(title="Walk", duration=20, priority="high")]
    plan = Scheduler(owner, owner.pet, tasks).build_plan()
    assert isinstance(plan.summary(), str)
    assert len(plan.summary()) > 0


def test_summary_contains_task_title():
    owner = make_owner(minutes=60)
    tasks = [make_task(title="Grooming", duration=20, priority="medium")]
    plan = Scheduler(owner, owner.pet, tasks).build_plan()
    assert "Grooming" in plan.summary()
