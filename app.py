import streamlit as st
import pandas as pd
from ortools.sat.python import cp_model

# --- UI CONFIGURATION ---
st.set_page_config(page_title="SLS Timetable Generator", page_icon="🏫", layout="wide")

def solve_timetable():
    model = cp_model.CpModel()

    # --- MOCK DATA ---
    num_days = 5
    num_periods = 5
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    
    # {teacher_id: ("Name", max_daily_hours, max_weekly_hours, "PRIORITY")}
    teachers = {
        0: ("Mr. Sharma", 4, 15, "SENIOR"),
        1: ("Ms. Davis", 3, 12, "JUNIOR"),
        2: ("Mr. Kumar", 5, 20, "NONE") 
    }
    
    # {class_id: ("Class Name", "YEAR_LEVEL")}
    classes = {
        0: ("10th Std - A", "SENIOR"),
        1: ("8th Std - B", "JUNIOR")
    }

    # --- VARIABLE CREATION ---
    assignments = {}
    for t in teachers:
        for c in classes:
            for d in range(num_days):
                for p in range(num_periods):
                    assignments[(t, c, d, p)] = model.NewBoolVar(f'assign_t{t}_c{c}_d{d}_p{p}')

    # --- HARD CONSTRAINTS ---
    # 1. A teacher can teach at most 1 class per period across all days
    for t in teachers:
        for d in range(num_days):
            for p in range(num_periods):
                model.AddAtMostOne(assignments[(t, c, d, p)] for c in classes)

    # 2. A class must have exactly 1 teacher per period (no empty periods)
    for c in classes:
        for d in range(num_days):
            for p in range(num_periods):
                model.AddExactlyOne(assignments[(t, c, d, p)] for t in teachers)

    # 3. Daily Workload Cap for Teachers
    for t, t_data in teachers.items():
        max_daily = t_data[1]
        for d in range(num_days):
            model.Add(sum(assignments[(t, c, d, p)] for c in classes for p in range(num_periods)) <= max_daily)

    # 4. Weekly Workload Cap for Teachers
    for t, t_data in teachers.items():
        max_weekly = t_data[2]
        model.Add(sum(assignments[(t, c, d, p)] for c in classes for d in range(num_days) for p in range(num_periods)) <= max_weekly)

    # --- SOFT CONSTRAINTS (Optimization) ---
    priority_matches = []
    for t, t_data in teachers.items():
        t_priority = t_data[3]
        for c, c_data in classes.items():
            c_level = c_data[1]
            for d in range(num_days):
                for p in range(num_periods):
                    if t_priority == c_level:
                        priority_matches.append(assignments[(t, c, d, p)])

    # Maximize the number of times a teacher is assigned to their preferred year level
    model.Maximize(sum(priority_matches))

    # --- SOLVE ---
    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    results = {}
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        # Format results into Pandas DataFrames for clean Streamlit rendering
        for c, c_data in classes.items():
            class_name = c_data[0]
            schedule_grid = []
            
            for d in range(num_days):
                day_row = {"Day": days[d]}
                for p in range(num_periods):
                    for t in teachers:
                        if solver.Value(assignments[(t, c, d, p)]) == 1:
                            day_row[f"Period {p+1}"] = teachers[t][0]
                schedule_grid.append(day_row)
            
            results[class_name] = pd.DataFrame(schedule_grid)
        return True, results
    else:
        return False, None

# --- STREAMLIT UI ---
# Sidebar Configuration
st.sidebar.image("https://placehold.co/200x200/red/white?text=SLS+Logo", caption="Saint Lawrence School")
st.sidebar.title("Admin Controls")
st.sidebar.info("Academic Year: 2026-2027")
st.sidebar.markdown("---")
st.sidebar.write("This engine uses AI constraint satisfaction to automatically generate collision-free schedules based on teacher availability and priority.")

# Main Page Configuration
st.title("🏫 Saint Lawrence School")
st.subheader("Teacher-Class Allotment & Timetable Engine")
st.markdown("---")

if st.button("🚀 Generate Optimized Timetable", type="primary", use_container_width=True):
    with st.spinner("Running Constraint Satisfaction Algorithm..."):
        success, schedules = solve_timetable()
        
    if success:
        st.success("✅ Timetable Generated Successfully! All constraints met.")
        
        # Create interactive Tabs for different classes
        class_names = list(schedules.keys())
        tabs = st.tabs(class_names)
        
        for i, tab in enumerate(tabs):
            with tab:
                st.markdown(f"### Schedule for {class_names[i]}")
                # Display the Pandas DataFrame as a clean UI table without the index numbers
                st.dataframe(schedules[class_names[i]], use_container_width=True, hide_index=True)
    else:
        st.error("❌ Failed to generate schedule. Constraints are too tight. Please relax the max hours or priority settings.")
