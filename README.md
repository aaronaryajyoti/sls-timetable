#🏫 Saint Lawrence School - Automated Timetable & Faculty Management System

An advanced, AI-powered timetable generation and school administration web application built specifically for Saint Lawrence School (Angul) using Streamlit, SQLite, and Google's OR-Tools Constraint Programming Engine.

✨ Key Features

🔒 Secure Administrator Authentication: Protected portal gateway ensuring only authorized administrative staff can modify school parameters, manage curriculum, and run the solver engine.

🏫 Smart Class & Section Management:

One-click automated setup for Classes 1–7 (4 sections: A, B, C, D) and Classes 8–10 (3 sections: A, B, C).

Ability to manually add custom sections or remove unused slots dynamically.

📚 Excel-Driven Master Curriculum: Seamlessly load and sync syllabus requirements, weekly period counts, and grade-level mappings straight from master spreadsheets.

👨‍🏫 Advanced Teacher Roster: Assign qualified teachers, define maximum daily/weekly workload thresholds, and restrict teachers to specific class levels.

⚙️ OR-Tools AI Solver Engine:

Automatically resolves complex scheduling conflicts.

Enforces hard constraints (no teacher double-booking, no overlapping classes).

Optional Group Synchronization: Mathematically locks optional language groups (Hindi vs. Odia) and electives so all sections of a grade attend them simultaneously.

📊 Dual-Perspective Outputs: Generates clean, separate grid views for both individual Class Timetables and Teacher Schedules.

📥 One-Click Excel & PDF Exports: Download any generated schedule directly as a formatted spreadsheet for physical printing or digital distribution.

📈 Teacher Workload & Gap Analytics: Real-time analytical breakdown comparing assigned teaching hours against weekly limits to spot overloads or free-period gaps.

🛠️ Technology Stack

Frontend & UI: Streamlit (with custom branding, watermarks, and responsive layout)

Database: SQLite (sls_master_v4.db)

Optimization Engine: Google OR-Tools (cp_model)

Data Manipulation: Pandas & OpenPyXL

🚀 Installation & Deployment

Clone the Repository:

git clone https://github.com/your-username/sls-timetable.git
cd sls-timetable


Install Dependencies:
Ensure you have Python installed, then run:

pip install -r requirements.txt


Run the Application Locally:

streamlit run app.py


🔐 Administrator Access

When launching the app for the first time, log in using the default admin credentials:

Password: slsangul2026

Love in Service • Est. 1986 • Tentoloi, Angul
