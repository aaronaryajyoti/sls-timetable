import streamlit as st
import pandas as pd
import sqlite3
import os
from ortools.sat.python import cp_model

st.set_page_config(page_title="St. Lawrence Timetable", page_icon="🏫", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; }
    .css-1d391kg { background-color: #00205B !important; }
    .css-1d391kg * { color: white !important; }
    .stButton>button {
        background-color: #F2A900 !important; 
        color: #00205B !important;
        font-weight: bold;
        border: None;
        border-radius: 8px;
    }
    .stButton>button:hover {
        background-color: #E6A000 !important;
    }
    h1, h2, h3 { color: #00205B !important; }
    .info-box {
        background-color: #E8F0FE;
        border-left: 5px solid #00205B;
        padding: 10px;
        margin-bottom: 20px;
        border-radius: 4px;
    }
    </style>
""", unsafe_allow_html=True)

# Definitive list of subjects extracted from St. Lawrence PDFs
MASTER_SUBJECTS = [
    "English 1", "English 2", "Mathematics", "Science", "EVS", 
    "Physics", "Chemistry", "Biology", "History & Civics", "Geography", 
    "SST", "Hindi", "Odia", "Computer", "Physical Education", 
    "Arts/Drawing", "M.Sc/G.K.", "Activity/SUPW"
]

DB_NAME = 'sls_timetable_final.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS classes (id INTEGER PRIMARY KEY AUTOINCREMENT, grade TEXT, section TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, max_daily INTEGER, max_weekly INTEGER, subjects TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS curriculum (id INTEGER PRIMARY KEY AUTOINCREMENT, grade TEXT, subject TEXT, periods INTEGER, optional_group TEXT)''')
    conn.commit()
    conn.close()

if not os.path.exists(DB_NAME):
    init_db()

def run_query(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def execute_db(query, params=()):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

def solve_timetable(df_teachers, df_classes, df_curriculum):
    model = cp_model.CpModel()
    num_days = 5
    num_periods = 8
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    period_times = ["P1 (08:20)", "P2 (09:00)", "P3 (09:40)", "P4 (10:20)", "P5 (11:20)", "P6 (12:00)", "P7 (12:40)", "P8 (01:20)"]
    
    assignments = {}
    valid_t_req = []
    
    # Parse teacher subjects
    teacher_subjects = {t['id']: [s.strip() for s in str(t['subjects']).split(',')] for _, t in df_teachers.iterrows()}
    grades = df_classes['grade'].unique()
    
    # Create variables matching teachers to curriculum requirements
    for _, req in df_curriculum.iterrows():
        req_sub = str(req['subject']).strip()
        sections = df_classes[df_classes['grade'] == req['grade']]['id'].tolist()
        
        for _, t in df_teachers.iterrows():
            if req_sub in teacher_subjects[t['id']]:
                valid_t_req.append((t['id'], req['id']))
                for sec in sections:
                    for d in range(num_days):
                        for p in range(num_periods):
                            assignments[(t['id'], sec, req['id'], d, p)] = model.NewBoolVar(f'assign_t{t["id"]}_s{sec}_req{req["id"]}_d{d}_p{p}')

    # Constraint 1: Fulfill all required periods
    for _, req in df_curriculum.iterrows():
        sections = df_classes[df_classes['grade'] == req['grade']]['id'].tolist()
        for sec in sections:
            model.Add(sum(assignments[(t, sec, req['id'], d, p)] 
                          for t, r in valid_t_req if r == req['id'] 
                          for d in range(num_days) for p in range(num_periods)) == req['periods'])

    # Constraint 2: Teachers can only be in one class per period
    for _, t in df_teachers.iterrows():
        for d in range(num_days):
            for p in range(num_periods):
                model.AddAtMostOne(assignments[(t['id'], sec, req_id, d, p)] 
                                   for sec in df_classes['id'] 
                                   for t_id, req_id in valid_t_req if t_id == t['id'] and (t_id, sec, req_id, d, p) in assignments)

    # Constraint 3: Sections can only have one teacher per period
    for sec in df_classes['id'].tolist():
        for d in range(num_days):
            for p in range(num_periods):
                model.AddAtMostOne(assignments[(t_id, sec, req_id, d, p)] 
                                   for t_id, req_id in valid_t_req if (t_id, sec, req_id, d, p) in assignments)

    for _, t in df_teachers.iterrows():
        for d in range(num_days):
            model.Add(sum(assignments[(t['id'], sec, req_id, d, p)] 
                          for sec in df_classes['id'] 
                          for t_id, req_id in valid_t_req if t_id == t['id'] and (t_id, sec, req_id, d, p) in assignments) <= t['max_daily'])
        model.Add(sum(assignments[(t['id'], sec, req_id, d, p)] 
                      for sec in df_classes['id'] 
                      for t_id, req_id in valid_t_req if t_id == t['id'] 
                      for d in range(num_days) for p in range(num_periods) if (t_id, sec, req_id, d, p) in assignments) <= t['max_weekly'])

    for grade in grades:
        grade_curriculum = df_curriculum[df_curriculum['grade'] == grade]
        optional_groups = grade_curriculum[grade_curriculum['optional_group'] != 'NONE']['optional_group'].unique()
        sections = df_classes[df_classes['grade'] == grade]['id'].tolist()
        
        for opt_grp in optional_groups:
            req_ids_in_group = grade_curriculum[grade_curriculum['optional_group'] == opt_grp]['id'].tolist()
            for d in range(num_days):
                for p in range(num_periods):
                    is_active = model.NewBoolVar(f'{grade}_{opt_grp}_active_d{d}_p{p}')
                    for sec in sections:
                        # Force ALL sections of this grade to take a subject from this group at the exact same time
                        model.Add(sum(assignments[(t_id, sec, req_id, d, p)] 
                                      for req_id in req_ids_in_group 
                                      for t_id, r in valid_t_req if r == req_id and (t_id, sec, req_id, d, p) in assignments) == is_active)

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 120.0 # Allow up to 2 mins for complex calculations
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        class_results = {}
        teacher_results = {}
        
        # Format Class Timetables
        for _, c in df_classes.iterrows():
            sec_id = c['id']
            class_name = f"Class {c['grade']} - {c['section']}"
            schedule_grid = []
            for d in range(num_days):
                day_row = {"Day": days[d]}
                for p in range(num_periods):
                    day_row[period_times[p]] = "---"
                    for _, req in df_curriculum.iterrows():
                        for t_id, r in valid_t_req:
                            if r == req['id'] and (t_id, sec_id, req['id'], d, p) in assignments and solver.Value(assignments[(t_id, sec_id, req['id'], d, p)]) == 1:
                                teacher_name = df_teachers[df_teachers['id'] == t_id].iloc[0]['name']
                                display_text = req['subject']
                                if req['optional_group'] != 'NONE':
                                    display_text += f" ({req['optional_group']})"
                                day_row[period_times[p]] = f"{display_text}\n[{teacher_name}]"
                    if p == 3: day_row["☕ BREAK"] = "RECREATION"
                schedule_grid.append(day_row)
            class_results[class_name] = pd.DataFrame(schedule_grid)

        # Format Teacher Timetables
        for _, t in df_teachers.iterrows():
            t_name = t['name']
            t_id = t['id']
            schedule_grid = []
            for d in range(num_days):
                day_row = {"Day": days[d]}
                for p in range(num_periods):
                    day_row[period_times[p]] = "---"
                    for _, req in df_curriculum.iterrows():
                        for _, c in df_classes.iterrows():
                            sec_id = c['id']
                            if (t_id, req['id']) in valid_t_req and (t_id, sec_id, req['id'], d, p) in assignments and solver.Value(assignments[(t_id, sec_id, req['id'], d, p)]) == 1:
                                c_name = f"{c['grade']} - {c['section']}"
                                day_row[period_times[p]] = f"{req['subject']}\n[{c_name}]"
                    if p == 3: day_row["☕ BREAK"] = "RECREATION"
                schedule_grid.append(day_row)
            teacher_results[t_name] = pd.DataFrame(schedule_grid)

        return True, class_results, teacher_results
    return False, None, None

try:
    st.sidebar.image("1000421843.png", use_column_width=True)
except:
    st.sidebar.markdown("### 🏫 Saint Lawrence School")

page = st.sidebar.radio("System Menu", [
    "⚙️ 1. Auto-Setup School", 
    "📚 2. Master Curriculum", 
    "👨‍🏫 3. Teacher Roster", 
    "📅 4. Generate Timetable"
])

if page == "⚙️ 1. Auto-Setup School":
    st.title("🏫 Auto-Initialize Classes")
    st.markdown('<div class="info-box">Click the button below to instantly generate 4 sections (A,B,C,D) for Classes 1-7, and 3 sections (A,B,C) for Classes 8-10.</div>', unsafe_allow_html=True)
    
    if st.button("🚀 Auto-Generate All Class Sections", type="primary"):
        execute_db("DELETE FROM classes") # Clear old data to prevent duplicates
        
        # Classes 1 to 7 (A, B, C, D)
        for grade in ["1", "2", "3", "4", "5", "6", "7"]:
            for sec in ["A", "B", "C", "D"]:
                execute_db("INSERT INTO classes (grade, section) VALUES (?, ?)", (grade, sec))
        
        # Classes 8, 9, 10 (A, B, C)
        for grade in ["8", "9", "10"]:
            for sec in ["A", "B", "C"]:
                execute_db("INSERT INTO classes (grade, section) VALUES (?, ?)", (grade, sec))
                
        st.success("✅ Classes 1 through 10 and all their sections successfully generated!")
        st.rerun()
        
    df_c = run_query("SELECT grade as 'Class', section as 'Section' FROM classes ORDER BY grade, section")
    if not df_c.empty:
        st.write(f"**Total Sections in Database:** {len(df_c)}")
        st.dataframe(df_c, hide_index=True)

elif page == "📚 2. Master Curriculum":
    st.title("📚 Define Master Curriculum")
    st.markdown('<div class="info-box">Assign subjects to a Class. To make subjects optional (like Hindi vs Odia), put them in the same <b>Optional Group</b>. The AI will force all sections of that class to attend those subjects at the exact same time.</div>', unsafe_allow_html=True)
    
    grades = run_query("SELECT DISTINCT grade FROM classes")['grade'].tolist()
    
    if not grades:
        st.warning("Please auto-setup classes in Step 1 first.")
    else:
        with st.form("add_curriculum_form"):
            c1, c2, c3, c4 = st.columns(4)
            sel_grade = c1.selectbox("Target Class", grades)
            sel_subj = c2.selectbox("Select Subject", MASTER_SUBJECTS)
            periods = c3.number_input("Periods/Week", 1, 10, 4)
            
            # Optional Group Assignment
            opt_group = c4.selectbox("Optional Group Mapping", [
                "NONE", 
                "Group 1 (Language: Hindi/Odia)", 
                "Group 2 (Elective: IT/PE/Arts)"
            ])
            
            if st.form_submit_button("Add to Master Syllabus"):
                execute_db("INSERT INTO curriculum (grade, subject, periods, optional_group) VALUES (?, ?, ?, ?)",
                           (sel_grade, sel_subj, periods, opt_group))
                st.success(f"Added {sel_subj} to Class {sel_grade}")
                st.rerun()
                
        st.subheader("Current Syllabus Mappings")
        df_curr = run_query("SELECT id, grade as 'Class', subject as 'Subject', periods as 'Periods/Week', optional_group as 'Synchronization' FROM curriculum ORDER BY grade, optional_group")
        st.dataframe(df_curr, hide_index=True, use_container_width=True)
        
        del_curr = st.number_input("Enter ID to Delete Rule:", min_value=0)
        if st.button("Delete Requirement", type="primary"):
            execute_db("DELETE FROM curriculum WHERE id=?", (del_curr,))
            st.rerun()

elif page == "👨‍🏫 3. Teacher Roster":
    st.title("👨‍🏫 Teacher Roster")
    st.markdown('<div class="info-box">Extract data from your Excel sheets and enter the teachers here. You can assign multiple subjects to a single teacher.</div>', unsafe_allow_html=True)
    
    with st.form("add_teacher_form"):
        col1, col2 = st.columns(2)
        t_name = col1.text_input("Teacher Name", placeholder="e.g. Prof. Sharma")
        t_subs = col2.multiselect("Select Subjects Taught", MASTER_SUBJECTS)
        
        c1, c2 = st.columns(2)
        t_daily = c1.number_input("Max Periods per Day", 1, 8, 6)
        t_weekly = c2.number_input("Max Periods per Week", 1, 40, 28)
        
        if st.form_submit_button("Add Teacher to System"):
            if t_name and t_subs:
                execute_db("INSERT INTO teachers (name, max_daily, max_weekly, subjects) VALUES (?, ?, ?, ?)",
                           (t_name, t_daily, t_weekly, ",".join(t_subs)))
                st.success(f"Added {t_name}")
                st.rerun()
            else:
                st.error("Please provide a name and select at least one subject.")
            
    st.subheader("Current Faculty")
    df_t = run_query("SELECT id, name as 'Name', max_daily as 'Max/Day', max_weekly as 'Max/Week', subjects as 'Subjects' FROM teachers")
    st.dataframe(df_t, hide_index=True, use_container_width=True)
    
    del_t = st.number_input("Enter Teacher ID to Remove (Retired/Left):", min_value=0)
    if st.button("Remove Teacher", type="primary"):
        execute_db("DELETE FROM teachers WHERE id=?", (del_t,))
        st.rerun()

elif page == "📅 4. Generate Timetable":
    st.title("⚙️ AI Schedule Generator")
    
    df_t = run_query("SELECT * FROM teachers")
    df_c = run_query("SELECT * FROM classes")
    df_curr = run_query("SELECT * FROM curriculum")
    
    if df_t.empty or df_c.empty or df_curr.empty:
        st.warning("Please ensure Classes, Curriculum, and Teachers are fully populated before running the engine.")
    else:
        st.info(f"System Ready: Scheduling {len(df_t)} teachers across {len(df_c)} class sections.")
        
        if st.button("🚀 Execute Optimization Engine", type="primary", use_container_width=True):
            with st.spinner("AI is calculating the optimal schedule... (This may take a minute to synchronize optional subjects)"):
                success, class_res, teacher_res = solve_timetable(df_t, df_c, df_curr)
                
            if success:
                st.success("✅ Schedules Generated Successfully!")
                
                tab_classes, tab_teachers = st.tabs(["📚 Class Timetables", "👨‍🏫 Teacher Timetables"])
                
                with tab_classes:
                    st.write("Schedules for students. Notice how optional subjects are synchronized across sections of the same class.")
                    c_names = list(class_res.keys())
                    c_tabs = st.tabs(c_names)
                    for i, t in enumerate(c_tabs):
                        with t:
                            st.dataframe(class_res[c_names[i]], use_container_width=True, hide_index=True)
                            
                with tab_teachers:
                    st.write("Personalized schedules showing teachers exactly which section they teach at what time.")
                    t_names = list(teacher_res.keys())
                    t_tabs = st.tabs(t_names)
                    for i, t in enumerate(t_tabs):
                        with t:
                            st.dataframe(teacher_res[t_names[i]], use_container_width=True, hide_index=True)
            else:
                st.error("❌ The AI could not find a valid schedule. Constraints are too tight. Make sure you have enough teachers to cover the required periods, especially during synchronized optional blocks.")
