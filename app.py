# ... existing code ...
    "SNEHALATA", "SONIA", "SUMATI PRADHAN", "SUSHANTA", "SWAGATIKA MOHAPATRA", "VINAY"
]

# --- 2. UI & ST. LAWRENCE BRANDING ---
import base64

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
# ... existing code ...
            class_results[f"Class {c['grade']} - {c['section']}"] = pd.DataFrame(schedule_grid)
            
        # Build Teacher Timetables
        for _, t in df_teachers.iterrows():
# ... existing code ...
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
# ... existing code ...
