import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")
st.caption("A daily pet care planner for busy owners.")

st.divider()

# --- Owner + Pet Info ---
st.subheader("Owner & Pet Info")
col1, col2 = st.columns(2)
with col1:
    owner_name = st.text_input("Owner name", value="Jordan")
    available_minutes = st.number_input(
        "Time available today (minutes)",
        min_value=10,
        max_value=480,
        value=120,
        step=10,
    )
with col2:
    pet_name = st.text_input("Pet name", value="Mochi")
    species = st.selectbox("Species", ["dog", "cat", "other"])

st.divider()

# --- Task Management ---
st.subheader("Tasks")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

with st.form("add_task_form", clear_on_submit=True):
    col1, col2, col3 = st.columns([3, 2, 2])
    with col1:
        task_title = st.text_input("Task title", value="Morning walk")
    with col2:
        duration = st.number_input(
            "Duration (min)", min_value=1, max_value=240, value=20
        )
    with col3:
        task_time = st.time_input("Start time", value=None, step=300)
    col1b, col2b, col3b, col4b = st.columns([2, 2, 2, 2])
    with col1b:
        priority = st.selectbox("Priority", ["low", "medium", "high"], index=2)
    with col2b:
        category = st.selectbox(
            "Category", ["walk", "feeding", "meds", "grooming", "enrichment", "general"]
        )
    with col3b:
        required = st.checkbox("Required", value=False)
    with col4b:
        recurs_daily = st.checkbox("Recurring daily", value=False)
    submitted = st.form_submit_button("Add task")
    if submitted and task_title.strip():
        time_str = task_time.strftime("%I:%M %p") if task_time else "08:00 AM"
        st.session_state.tasks.append(
            {
                "title": task_title.strip(),
                "duration_minutes": int(duration),
                "priority": priority,
                "category": category,
                "required": required,
                "recurs_daily": recurs_daily,
                "start_time": time_str,
                "completed": False,
                "skipped_today": False,
            }
        )

if st.session_state.tasks:
    st.write(f"{len(st.session_state.tasks)} task(s):")

    for i, t in enumerate(st.session_state.tasks):
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([4, 2, 2, 1])
            with col1:
                badges = []
                if t["required"]:
                    badges.append("required")
                if t["recurs_daily"]:
                    badges.append("recurring")
                badge_str = f" · {', '.join(badges)}" if badges else ""
                style = "~~" if t["completed"] or t["skipped_today"] else ""
                st.markdown(
                    f"{style}**{t['title']}**{style} — {t['start_time']} · {t['duration_minutes']} min | {t['priority']} | {t['category']}{badge_str}"
                )
            with col2:
                done = st.checkbox(
                    "Mark done",
                    value=t["completed"],
                    key=f"done_{i}",
                )
                if done != t["completed"]:
                    st.session_state.tasks[i]["completed"] = done
                    st.rerun()
            with col3:
                if t["recurs_daily"]:
                    skipped = st.checkbox(
                        "Skip today",
                        value=t["skipped_today"],
                        key=f"skip_{i}",
                    )
                    if skipped != t["skipped_today"]:
                        st.session_state.tasks[i]["skipped_today"] = skipped
                        st.rerun()
            with col4:
                if st.button("✕", key=f"remove_{i}"):
                    st.session_state.tasks.pop(i)
                    st.rerun()

    if st.button("Reset day"):
        for t in st.session_state.tasks:
            t["completed"] = False
            t["skipped_today"] = False
        st.rerun()
else:
    st.info("No tasks yet. Add one above.")

st.divider()

# --- Generate Schedule ---
st.subheader("Generate Schedule")

if st.button("Build daily plan", type="primary"):
    if not st.session_state.tasks:
        st.warning("Add at least one task before generating a plan.")
    else:
        owner = Owner(
            name=owner_name,
            available_minutes=int(available_minutes),
        )
        owner.pet = Pet(name=pet_name, species=species)

        tasks = [
            Task(
                title=t["title"],
                duration_minutes=t["duration_minutes"],
                priority=t["priority"],
                category=t["category"],
                required=t["required"],
                recurs_daily=t["recurs_daily"],
                start_time=t["start_time"],
            )
            for t in st.session_state.tasks
        ]

        # Apply daily state from session to Task objects before scheduling
        for task_obj, t in zip(tasks, st.session_state.tasks):
            task_obj.completed = t["completed"]
            task_obj.skipped_today = t["skipped_today"]

        plan = Scheduler(owner, owner.pet, tasks).build_plan()

        st.success(
            f"Plan built for {owner_name} and {pet_name}! {plan.total_minutes} of {available_minutes} minutes used."
        )

        if plan.scheduled:
            st.markdown("### Scheduled Tasks")
            for st_task in plan.scheduled:
                with st.container(border=True):
                    col1, col2 = st.columns([3, 2])
                    with col1:
                        st.markdown(f"**{st_task.task.title}**")
                        st.caption(st_task.reason)
                    with col2:
                        st.markdown(f"🕐 {st_task.start_time}")
                        st.caption(
                            f"{st_task.task.duration_minutes} min | {st_task.task.priority} priority"
                        )

        if plan.skipped:
            st.markdown("### Skipped Tasks")
            st.caption("These tasks didn't fit within your available time.")
            for t in plan.skipped:
                st.markdown(
                    f"- **{t.title}** ({t.duration_minutes} min, {t.priority} priority)"
                )
