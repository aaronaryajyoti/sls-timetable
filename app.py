import streamlit as st
import pandas as pd
import sqlite3
import os
import base64
from ortools.sat.python import cp_model

# --- 1. DEFINITIVE SUBJECT & TEACHER LISTS ---
MASTER_SUBJECTS = [
    "English 1", "English 2", "Mathematics", "Science", "EVS", 
    "Physics", "Chemistry", "Biology", "History & Civics", "Geography", 
    "SST", "Hindi", "Odia", "Computer", "Physical Education", 
    "Arts/Drawing", "M.Sc/G.K.", "Activity/SUPW"
]

HARDCODED_TEACHERS = [
    "A.S BASA", "B. PRIYA", "BEENA MOHAPATRA", "BHOLA CH", "BISHNUPRIYA SAMAL", 
    "CHAMAN DEEP", "CHAMPA SUBUDHI", "CHITTA RANJAN DASH", "DEBJANI GHOSH", 
    "DEEP RANA", "DEEPANJALI NAYAK", "DEVBANI GANGULY", "GARIMA", "JAYASALILA PANDA", 
    "JUGAL KI NAYAK", "KALPANA", "MAHABIR PANI", "MALA CHA", "MAN.SOOD", 
    "MEERA BISOI", "MONALISHA JENA", "NEELAM", "NIHAR TRIPATHY", "PRADEEP TRIPATHY", 
    "PRAGYANPINI", "PRAKASH KU SINGH", "PRAMILA XAXA", "PREETI KOUR", "PRITI MINZ", 
    "PUJA SINHA", "RAJESH MAJHI", "RANJITA PANI", "RASHMI DAS", "RASHMI PARIDA", 
    "RASHMI SWAIN", "SABITA PADHI", "SANJEEV P", "SARANJIT K", "SEEMA JHA", 
    "SHALINI SINHA", "SHEELARANI MISHRA", "SHWETA SINGH", "SIMION MALI", 
    "SNEHALATA", "SONIA", "SUMATI PRADHAN", "SUSHANTA", "SWAGATIKA MOHAPATRA", "VINAY"
]

# --- 2. UI & ST. LAWRENCE BRANDING ---
def get_base64_of_bin_file(bin_file):
    try:
        with open(bin_file, 'rb') as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except Exception:
        return ""

logo_base64 = get_base64_of_bin_file('slsangul_logo.jpg')

# Set page icon
st.set_page_config(page_title="St. Lawrence Timetable", page_icon="slsangul_logo.jpg", layout="wide")

st.markdown(f"""
    <style>
    .stApp {{ background-color: #F8F9FA; }}
    .css-1d391kg {{ background-color: #00205B !important; }}
    .css-1d391kg * {{ color: white !important; }}
    
    /* Subtle Watermark */
    .stApp::before {{
        content: "";
        position: fixed;
        top: 0;
        left: 0;
        width: 100vw;
        height: 100vh;
        background-image: url("data:image/jpeg;base64,{logo_base64}");
        background-repeat: no-repeat;
        background-position: center center;
        background-attachment: fixed;
        background-size: 50vh;
        opacity: 0.03;
        z-index: -1;
        pointer-events: none;
    }}

    .stButton>button {{
        background-color: #F2A900 !important; 
        color: #00205B !important;
        font-weight: bold;
        border: None;
    }}
    h1, h2, h3 {{ color: #00205B !important; }}
    </style>
""", unsafe_allow_html=True)

# --- 3. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('sls_master_v4.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS classes (id INTEGER PRIMARY KEY AUTOINCREMENT, grade TEXT, section TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS teachers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, max_daily INTEGER, max_weekly INTEGER, subjects TEXT, classes TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS curriculum (id INTEGER PRIMARY KEY AUTOINCREMENT, grade TEXT, subject TEXT, periods INTEGER, optional_group TEXT)''')
    conn.commit()
    conn.close()

if not os.path.exists('sls_master_v4.db'):
    init_db()

def run_query(query, params=()):
    conn = sqlite3.connect('sls_master_v4.db')
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def execute_db(query, params=()):
    conn = sqlite3.connect('sls_master_v4.db')
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    conn.close()

# --- 4. THE AI SOLVER ENGINE ---
def solve_timetable(df_teachers, df_classes, df_curriculum, num_days=5, num_periods=8):
    model = cp_model.CpModel()
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    period_times = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8"]
    
    assignments = {}
    valid_t_req = []
    
    teacher_subjects = {t['id']: [s.strip() for s in str(t['subjects']).split(',')] for _, t in df_teachers.iterrows()}
    teacher_classes = {t['id']: [c.strip() for c in str(t.get('classes', '')).split(',')] if pd.notna(t.get('classes')) else [] for _, t in df_teachers.iterrows()}
    
    grades = df_classes['grade'].unique()
    
    for _, req in df_curriculum.iterrows():
        req_sub = str(req['subject']).strip()
        req_grade = str(req['grade']).strip()
        sections = df_classes[df_classes['grade'] == req['grade']]['id'].tolist()
        
        for _, t in df_teachers.iterrows():
            t_id = t['id']
            t_classes_assigned = teacher_classes.get(t_id, [])
            
            if req_sub in teacher_subjects[t_id] and (not t_classes_assigned or t_classes_assigned == [''] or req_grade in t_classes_assigned):
                valid_t_req.append((t_id, req['id']))
                for sec in sections:
                    for d in range(num_days):
                        for p in range(num_periods):
                            assignments[(t_id, sec, req['id'], d, p)] = model.NewBoolVar(f'assign_t{t_id}_s{sec}_req{req["id"]}_d{d}_p{p}')

    for _, req in df_curriculum.iterrows():
        sections = df_classes[df_classes['grade'] == req['grade']]['id'].tolist()
        for sec in sections:
            model.Add(sum(assignments[(t, sec, req['id'], d, p)] for t, r in valid_t_req if r == req['id'] for d in range(num_days) for p in range(num_periods)) == req['periods'])

    for _, t in df_teachers.iterrows():
        for d in range(num_days):
            for p in range(num_periods):
                model.AddAtMostOne(assignments[(t['id'], sec, req_id, d, p)] for sec in df_classes['id'] for t_id, req_id in valid_t_req if t_id == t['id'] and (t_id, sec, req_id, d, p) in assignments)

    for sec in df_classes['id'].tolist():
        for d in range(num_days):
            for p in range(num_periods):
                model.AddAtMostOne(assignments[(t_id, sec, req_id, d, p)] for t_id, req_id in valid_t_req if (t_id, sec, req_id, d, p) in assignments)

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
                        model.Add(sum(assignments[(t_id, sec, req_id, d, p)] for req_id in req_ids_in_group for t_id, r in valid_t_req if r == req_id and (t_id, sec, req_id, d, p) in assignments) == is_active)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0 
    status = solver.Solve(model)

    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        class_results = {}
        teacher_results = {}
        
        for _, c in df_classes.iterrows():
            sec_id = c['id']
            schedule_grid = []
            for d in range(num_days):
                day_row = {"Day": days[d]}
                for p in range(num_periods):
                    day_row[period_times[p]] = "---"
                    for _, req in df_curriculum.iterrows():
                        for t_id, r in valid_t_req:
                            if r == req['id'] and (t_id, sec_id, req['id'], d, p) in assignments and solver.Value(assignments[(t_id, sec_id, req['id'], d, p)]) == 1:
                                teacher_name = df_teachers[df_teachers['id'] == t_id].iloc[0]['name']
                                day_row[period_times[p]] = f"{req['subject']} [{teacher_name}]"
                schedule_grid.append(day_row)
            class_results[f"Class {c['grade']} - {c['section']}"] = pd.DataFrame(schedule_grid)
            
        for _, t in df_teachers.iterrows():
            t_id = t['id']
            t_name = t['name']
            schedule_grid = []
            for d in range(num_days):
                day_row = {"Day": days[d]}
                for p in range(num_periods):
                    day_row[period_times[p]] = "---"
                    for _, req in df_curriculum.iterrows():
                        for sec_id in df_classes['id'].tolist():
                            if (t_id, sec_id, req['id'], d, p) in assignments and solver.Value(assignments[(t_id, sec_id, req['id'], d, p)]) == 1:
                                grade_val = df_classes[df_classes['id'] == sec_id].iloc[0]['grade']
                                sec_val = df_classes[df_classes['id'] == sec_id].iloc[0]['section']
                                day_row[period_times[p]] = f"{req['subject']} [Cls {grade_val}-{sec_val}]"
                schedule_grid.append(day_row)
            teacher_results[t_name] = pd.DataFrame(schedule_grid)
            
        return True, class_results, teacher_results
    return False, None, None

# --- 5. STREAMLIT UI ---
try:
    st.sidebar.image("slsangul_logo.jpg", use_column_width=True)
except:
    st.sidebar.markdown("### 🏫 Saint Lawrence School")

page = st.sidebar.radio("Navigation", ["1. Manage Classes", "2. Master Curriculum", "3. Teacher Roster", "4. Generate Timetable"])

if page == "1. Manage Classes":
    st.title("🏫 Manage Classes & Sections")
    
    st.subheader("Auto-Initialize Classes")
    if st.button("🚀 Auto-Generate Classes 1-10", type="primary"):
        execute_db("DELETE FROM classes") 
        for grade in ["1", "2", "3", "4", "5", "6", "7"]:
            for sec in ["A", "B", "C", "D"]:
                execute_db("INSERT INTO classes (grade, section) VALUES (?, ?)", (grade, sec))
        for grade in ["8", "9", "10"]:
            for sec in ["A", "B", "C"]:
                execute_db("INSERT INTO classes (grade, section) VALUES (?, ?)", (grade, sec))
        st.success("✅ Standard classes successfully generated!")
        st.rerun()
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Add Specific Section")
        with st.form("manual_add"):
            c_grade = st.text_input("Class/Grade (e.g., 11)")
            c_sec = st.text_input("Section (e.g., A)")
            if st.form_submit_button("Add Section"):
                execute_db("INSERT INTO classes (grade, section) VALUES (?, ?)", (c_grade.strip(), c_sec.strip().upper()))
                st.success(f"Added {c_grade}-{c_sec}")
                st.rerun()
                
    with col2:
        st.subheader("Remove Section")
        with st.form("manual_remove"):
            del_id = st.number_input("Delete by ID:", min_value=0)
            if st.form_submit_button("Delete Section"):
                execute_db("DELETE FROM classes WHERE id=?", (del_id,))
                st.success("Section removed!")
                st.rerun()

    st.subheader("Current Database")
    df_c = run_query("SELECT * FROM classes ORDER BY CAST(grade AS INTEGER), section")
    if not df_c.empty:
        st.dataframe(df_c, hide_index=True, use_container_width=True)

elif page == "2. Master Curriculum":
    st.title("📚 Define Master Curriculum")
    grades = run_query("SELECT DISTINCT grade FROM classes ORDER BY CAST(grade AS INTEGER)")['grade'].tolist()
    
    if not grades:
        st.warning("Please setup classes first.")
    else:
        st.info("Assign subjects to a Class. The Optional Group rules update based on the Class you select.")
        sel_grade = st.selectbox("🎯 Step 1: Select Target Class", grades)
        
        if str(sel_grade) in ['9', '10']:
            opt_choices = ["NONE", "Group 1 (Language: Hindi/Odia)", "Group 2 (Electives: IT/PE/Arts)"]
        elif str(sel_grade) == '8':
            opt_choices = ["NONE", "Group 1 (Language: Hindi/Odia)"]
        else:
            opt_choices = ["NONE"]
        
        st.markdown(f"**Step 2: Add Subjects to Class {sel_grade}**")
        with st.form("add_curriculum_form"):
            c1, c2, c3 = st.columns(3)
            sel_subj = c1.selectbox("Select Subject", MASTER_SUBJECTS)
            periods = c2.number_input("Periods/Week", 1, 10, 4)
            opt_group = c3.selectbox("Optional Group Mapping", opt_choices)
            
            if st.form_submit_button("Add to Master Syllabus"):
                execute_db("INSERT INTO curriculum (grade, subject, periods, optional_group) VALUES (?, ?, ?, ?)", (sel_grade, sel_subj, periods, opt_group))
                st.success(f"Added {sel_subj} to Class {sel_grade}")
                st.rerun()
                
        st.subheader("Current Syllabus")
        df_curr = run_query("SELECT * FROM curriculum ORDER BY CAST(grade AS INTEGER)")
        if not df_curr.empty:
            st.dataframe(df_curr, hide_index=True, use_container_width=True)
            del_curr = st.number_input("Delete Row ID:", min_value=0)
            if st.button("Delete Requirement"):
                execute_db("DELETE FROM curriculum WHERE id=?", (del_curr,))
                st.rerun()

elif page == "3. Teacher Roster":
    st.title("👨‍🏫 Teacher Roster")
    st.info("Select a teacher from the dropdown, assign their allowed classes, and assign their subjects.")
    
    grades = run_query("SELECT DISTINCT grade FROM classes ORDER BY CAST(grade AS INTEGER)")['grade'].tolist()

    with st.form("add_teacher_form"):
        col1, col2, col3 = st.columns(3)
        t_name = col1.selectbox("Teacher Name", HARDCODED_TEACHERS)
        t_classes = col2.multiselect("Assigned Classes (Leave blank for all)", grades)
        t_subs = col3.multiselect("Select Subjects Taught", MASTER_SUBJECTS)
        
        c1, c2 = st.columns(2)
        t_daily = c1.number_input("Max Periods per Day", 1, 8, 6)
        t_weekly = c2.number_input("Max Periods per Week", 1, 40, 28)
        
        if st.form_submit_button("Add Teacher to System"):
            execute_db("INSERT INTO teachers (name, max_daily, max_weekly, subjects, classes) VALUES (?, ?, ?, ?, ?)", 
                       (t_name, t_daily, t_weekly, ",".join(t_subs), ",".join(t_classes)))
            st.success(f"Added {t_name}")
            st.rerun()
            
    st.subheader("Current Faculty")
    df_t = run_query("SELECT * FROM teachers")
    st.dataframe(df_t, hide_index=True, use_container_width=True)
    
    with st.form("delete_teacher_form"):
        del_t = st.number_input("Delete Teacher by ID:", min_value=0)
        if st.form_submit_button("Remove Teacher"):
            execute_db("DELETE FROM teachers WHERE id=?", (del_t,))
            st.success("Teacher removed!")
            st.rerun()

elif page == "4. Generate Timetable":
    st.title("⚙️ St. Lawrence Timetable Engine")
    
    df_t = run_query("SELECT * FROM teachers")
    df_c = run_query("SELECT * FROM classes ORDER BY CAST(grade AS INTEGER), section")
    df_curr = run_query("SELECT * FROM curriculum")
    
    if st.button("🚀 Generate Optimized Timetable", type="primary", use_container_width=True):
        # 1. SAFETY CHECK: Ensure database is not empty before running
        if df_t.empty or df_c.empty or df_curr.empty:
            st.warning("⚠️ Database is incomplete! Please ensure you have added Classes, Curriculum, and Teachers before generating.")
        else:
            with st.spinner("Calculating optimal schedules..."):
                success, class_schedules, teacher_schedules = solve_timetable(df_t, df_c, df_curr)
                
            if success:
                st.success("✅ Timetable Generated Successfully!")
                
                tab_classes, tab_teachers = st.tabs(["📚 Class Timetables", "👨‍🏫 Teacher Timetables"])
                
                with tab_classes:
                    # 2. SAFETY CHECK: Only draw tabs if class_schedules is not empty
                    if class_schedules:
                        class_tabs = st.tabs(list(class_schedules.keys()))
                        for idx, t in enumerate(class_tabs):
                            with t:
                                st.dataframe(class_schedules[list(class_schedules.keys())[idx]], hide_index=True)
                    else:
                        st.info("No class schedules generated.")
                            
                with tab_teachers:
                    # 3. SAFETY CHECK: Only draw tabs if teacher_schedules is not empty
                    if teacher_schedules:
                        teacher_tabs = st.tabs(list(teacher_schedules.keys()))
                        for idx, t in enumerate(teacher_tabs):
                            with t:
                                st.dataframe(teacher_schedules[list(teacher_schedules.keys())[idx]], hide_index=True)
                    else:
                        st.info("No teacher schedules generated.")
            else:
                st.error("❌ Failed. You need more teachers or fewer required periods.")
