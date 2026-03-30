# PawPal+ Project Reflection

## 1. System Design

**a. Initial design**

The initial UML design included six classes: `Owner`, `Pet`, `Task`, `Scheduler`, `ScheduledTask`, and `Plan`.

- `Task` holds what needs to be done (title, duration, priority, category, required flag, recurrence, and daily state).
- `Pet` stores basic pet info (name, species).
- `Owner` tracks who the care is for and how much time they have. It owns a `Pet` and a list of `Task`s.
- `Scheduler` takes an `Owner`, `Pet`, and task list and produces a `Plan` by sorting tasks by priority and greedily fitting them within the owner's available time.
- `ScheduledTask` pairs a `Task` with a computed start time and a reason string explaining why it was included.
- `Plan` is the output: an ordered list of `ScheduledTask`s`, a list of skipped tasks, and the total minutes used.

**b. Design changes**

The design stayed true to the UML through implementation. One small addition was a private `_explain()` helper method on `Scheduler` that was not in the original UML — it was extracted to keep `build_plan()` readable.

After an initial implementation, `_explain()` was revised: the original version only received the `Task` object and produced generic labels like "High priority walk task." This wasn't meaningful enough — it didn't say *why* that specific task was chosen. The method signature was updated to also accept the task's rank in the sorted list, the total number of tasks, minutes used so far, and minutes remaining at the time of scheduling. This gave it enough context to produce a specific explanation for each decision.

Later iterations added task completion status (`completed`, `skipped_today`) and recurring task support (`recurs_daily`) to `Task`, along with four new methods on `Owner`: `mark_complete()`, `skip_today()`, `reset_day()`, and `filter_tasks()`. The scheduler was updated to automatically exclude completed and skipped-today tasks from the plan. A bug was caught during testing: `reset_day()` originally preserved `completed` on recurring tasks, but since recurring tasks come back each day, their completion state must also be reset — the condition was removed to fix this.

A further redesign moved the day's start time from `Owner` down to each individual `Task` as a `start_time` field. This gave owners the ability to set a specific time per task rather than having times assigned sequentially from a single daily start. The scheduler sort order was updated to use task start time as the primary sort key. Overlap handling was added: if a task's desired start time falls before the end of the previous task, its actual start is shifted forward automatically, and the explanation notes the shift.

---

## 2. Scheduling Logic and Tradeoffs

**a. Constraints and priorities**

The scheduler considers four constraints:

- **Time**: the owner's `available_minutes` acts as a hard budget. No task is scheduled if it would exceed this limit.
- **Start time**: each task has a user-set desired start time. Tasks are sorted by this time first, so the plan respects the owner's intended schedule. If two tasks overlap, the later one is shifted forward.
- **Priority**: tasks at the same time are ranked `high > medium > low`, with required tasks always winning ties regardless of priority level.
- **Daily state**: tasks marked as `completed` or `skipped_today` are excluded from the plan entirely before scheduling begins.

Required tasks were treated as the most important tiebreaker because missing them (e.g., medication) could have real consequences for the pet. Start time was made the primary sort key because an owner who sets a task for 9:00 AM expects it to appear near that time, not wherever priority would place it. Daily state was added to reflect that real-world plans change throughout the day.

**b. Tradeoffs**

The scheduler uses a greedy approach: it accepts tasks in sorted order and takes each one that fits, rather than finding the optimal combination. This means it can miss a better arrangement — for example, two shorter tasks that together fit perfectly might be skipped because one longer task was accepted first.

A second tradeoff is in overlap handling: rather than rejecting a task whose desired start time conflicts with the previous task, the scheduler shifts it forward. This keeps more tasks in the plan but may place a task later than the owner intended.

Both tradeoffs are reasonable because the goal is a quick, explainable daily plan. A greedy approach is fast and predictable, and shifting overlaps is more useful than silently dropping tasks the owner explicitly added.

---

## 3. AI Collaboration

**a. How you used AI**

AI was used throughout the project: generating the Mermaid diagram code, writing Python class stubs, implementing the scheduling logic, writing tests, and building the Streamlit UI. The most useful prompts were step-by-step and scoped.

**b. Judgment and verification**

The AI-generated tests were reviewed before accepting them. For example, the test `test_task_skipped_when_no_time` was checked to ensure it actually exercised the time constraint and not just task count. The 14 tests were run with `pytest` to confirm they all passed before moving on.

A more significant judgment call was made when reviewing the initial `_explain()` output in the running app. The AI-generated reason strings were technically correct but not useful — "High priority walk task" doesn't explain a decision, it just restates a label. Rather than accepting this output, the method was redesigned to receive scheduling context (rank, remaining time, minutes used) so it could produce explanations that actually reflect the reasoning behind each choice.

---

## 4. Testing and Verification

**a. What you tested**

23 tests were written across seven areas:

- `Task.priority_value()` returns the correct numeric value for each priority level.
- `Owner.add_task()` and `remove_task()` correctly mutate the task list, including a safe no-op when removing a nonexistent task.
- Scheduling order: high-priority tasks are scheduled before low-priority ones; required tasks are scheduled before high-priority ones.
- Time constraint: tasks that don't fit are skipped; total minutes never exceeds `available_minutes`.
- Edge cases: empty task list produces an empty plan; all tasks are scheduled when time is unlimited.
- Completion and filtering: `mark_complete()` flags a task correctly; `filter_tasks()` returns the right subset; completed tasks are excluded from the generated plan.
- Recurring tasks: `skip_today()` excludes a recurring task from the plan but not a non-recurring one; `reset_day()` clears `skipped_today` and `completed` on all tasks so the next day starts fresh; recurring tasks reappear in the plan after a reset.

These tests mattered because scheduling order, the time budget, and daily state are all core behaviors — if any are wrong, the plan is either incorrect or stale.

**b. Confidence**

Confidence is high for the core behaviors covered by the tests. A bug was found and fixed during testing: `reset_day()` initially preserved `completed` on recurring tasks, which would have caused a task completed on Monday to remain done on Tuesday. The tests caught this before it reached the UI. Edge cases that would be worth testing next include: two tasks with identical priority and duration (tie-breaking stability), a single task that exactly fills the available time, and a required task that is too long to fit at all.

---

## 5. Reflection

**a. What went well**

The separation of concerns between `pawpal_system.py` (logic) and `app.py` (UI) worked well. It made testing straightforward — `pytest` could import and test the scheduling logic directly without involving Streamlit at all. It also made iterating on the explanation quality easy: the `_explain()` method could be improved and re-tested in isolation without touching the UI.

**b. What you would improve**

The scheduling algorithm is purely greedy. A future improvement would be to try fitting shorter lower-priority tasks into remaining time after higher-priority tasks are placed, rather than skipping them entirely. This would make better use of the owner's available time.

**c. Key takeaway**

Designing the system on paper (UML) before writing code made implementation faster and more deliberate. Having a clear picture of what each class was responsible for meant there were fewer surprises during implementation, and changes were easy to reason about.
