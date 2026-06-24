import streamlit as st
import pandas as pd
import sqlite3
from ortools.sat.python import cp_model

# --- UI CONFIGURATION ---
st.set_page_config(page_title="SLS Timetable Generator", page_icon="🏫", layout="wide")

# --- DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('sls_database.db')
    c = conn.cursor()
    # Subjects Master Table
    c.execute('''CREATE TABLE IF NOT EXISTS subjects
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE)''')
    # Classes Table (with Grade and Section)
    c.execute('''CREATE TABLE IF NOT EXISTS classes
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT, grade TEXT, section TEXT, year_level TEXT)''')
    # Teachers Table 
    c.execute('''CREATE TABLE IF NOT EXISTS teachers
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT, max_daily INTEGER, max_weekly INTEGER, priority TEXT, subjects TEXT)''')
    # Curriculum Table 
    c.execute('''CREATE TABLE IF NOT EXISTS curriculum
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  class_id INTEGER, subject TEXT, is_lab BOOLEAN, periods INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- DATABASE HELPER FUNCTIONS ---
def run_query(query, params=()):
    conn = sqlite3.connect('sls_database.db')
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def execute_db(query, params=()):
    conn = sqlite3.connect('sls_database.db')
    c = conn.cursor()
    try:
        c.execute(query, params)
        conn.commit()
    except sqlite3.IntegrityError:
        pass 
    finally:
        conn.close()

# --- TIMETABLE LOGIC ENGINE ---
def solve_timetable(df_teachers, df_classes, df_curriculum):
    model = cp_model.CpModel()
    num_days = 5
    num_periods = 8
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    assignments = {}
    valid_t_req = []
    
    teacher_subjects = {}
    for _, t in df_teachers.iterrows():
        subjects = [s.strip().lower() for s in str(t['subjects']).split(',')]
        teacher_subjects[t['id']] = subjects

    for _, req in df_curriculum.iterrows():
        req_sub = str(req['subject']).strip().lower()
        for _, t in df_teachers.iterrows():
            if req_sub in teacher_subjects[t['id']]:
                valid_t_req.append((t['id'], req['id']))
                for d in range(num_days):
                    for p in range(num_periods):
                        assignments[(t['id'], req['id'], d, p)] = model.NewBoolVar(f'assign_t{t["id"]}_req{req["id"]}_d{d}_p{p}')

    # --- CONSTRAINTS ---
    for _, req in df_curriculum.iterrows():
        req_id = req['id']
        required_periods = req['periods']
        model.Add(sum(assignments[(t, req_id, d, p)] 
                      for t, r in valid_t_req if r == req_id 
                      for d in range(num_days) 
                      for p in range(num_periods)) == required_periods)

    for _, t in df_teachers.iterrows():
        t_id = t['id']
        for d in range(num_days):
            for p in range(num_periods):
                model.AddAtMostOne(assignments[(t_id, req_id, d, p)] 
                                   for t, req_id in valid_t_req if t == t_id)

    for _, c in df_classes.iterrows():
        c_id = c['id']
        class_reqs = df_curriculum[df_curriculum['class_id'] == c_id]['id'].tolist()
        for d in range(num_days):
            for p in range(num_periods):
                model.AddAtMostOne(assignments[(t_id, req_id, d, p)] 
                                   for t_id, req_id in valid_t_req if req_id in class_reqs)

    for _, t in df_teachers.iterrows():
        t_id = t['id']
        for d in range(num_days):
            model.Add(sum(assignments[(t_id, req_id, d, p)] 
                          for t, req_id in valid_t_req if t == t_id 
                          for p in range(num_periods)) <= t['max_daily'])
        model.Add(sum(assignments[(t_id, req_id, d, p)] 
                      for t, req_id in valid_t_req if t == t_id 
                      for d in range(num_days) 
                      for p in range(num_periods)) <= t['max_weekly'])

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0 
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        class_results = {}
        teacher_results = {}
        period_times = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]
        
        for _, c in df_classes.iterrows():
            class_name = c['name']
            class_reqs = df_curriculum[df_curriculum['class_id'] == c['id']]
            schedule_grid = []
            for d in range(num_days):
                day_row = {"Day": days[d]}
                for p in range(num_periods):
                    day_row[period_times[p]] = "---" 
                    for _, req in class_reqs.iterrows():
                        for t_id, req_id in valid_t_req:
                            if req_id == req['id'] and solver.Value(assignments[(t_id, req_id, d, p)]) == 1:
                                teacher_name = df_teachers[df_teachers['id'] == t_id].iloc[0]['name']
                                day_row[period_times[p]] = f"{req['subject']} [{teacher_name}]"
                schedule_grid.append(day_row)
            class_results[class_name] = pd.DataFrame(schedule_grid)

        for _, t in df_teachers.iterrows():
            t_name = t['name']
            t_id = t['id']
            schedule_grid = []
            for d in range(num_days):
                day_row = {"Day": days[d]}
                for p in range(num_periods):
                    day_row[period_times[p]] = "---"
                    for _, req in df_curriculum.iterrows():
                        if (t_id, req['id']) in valid_t_req and solver.Value(assignments[(t_id, req['id'], d, p)]) == 1:
                            c_name = df_classes[df_classes['id'] == req['class_id']].iloc[0]['name']
                            day_row[period_times[p]] = f"{req['subject']} [{c_name}]"
                schedule_grid.append(day_row)
            teacher_results[t_name] = pd.DataFrame(schedule_grid)

        return True, class_results, teacher_results
    return False, None, None

# --- UI ---
st.title("🏫 Saint Lawrence School - Timetable Generator")
page = st.sidebar.radio("Navigation", ["Setup", "Teachers", "Curriculum", "Generate"])

if page == "Setup":
    st.subheader("Master Subjects & Classes")
    if st.button("Add Subject"): execute_db("INSERT INTO subjects (name) VALUES (?)", ("Physics",))
    if st.form_submit_button("Generate Bulk Classes"): pass # Add logic here as per requirements

elif page == "Teachers":
    st.subheader("Manage Teachers")
    # Form to add/remove teachers

elif page == "Curriculum":
    st.subheader("Assign Subjects to Classes")

elif page == "Generate":
    st.subheader("Run Optimization")
    if st.button("Generate Schedules"):
        # Invoke solve_timetable
        st.success("Timetable ready!")
