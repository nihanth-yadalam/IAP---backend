# Tech Stack & Database Schema {#tech-stack-database-schema}

## 

## 1. Technology Stack {#technology-stack}

### **Frontend (The Interface)**

- **Framework:** **React.js (Vite)** with **TypeScript**.

  - *Why:* Type safety is critical for handling complex Task/Schedule data structures.

- **State Management:** **Zustand**.

  - *Why:* Lightweight and perfect for managing local calendar state (drag-and-drop updates).

- **UI Library:** **Shadcn/UI** + **Tailwind CSS**.

  - *Why:* Provides accessible, pre-built components (Modals, Popovers) for rapid UI development.

- **Calendar Engine:** **React-Big-Calendar**.

  - *Why:* Handles the complex math of rendering Week/Day views.

- **Visualization:** **Recharts**.

  - *Why:* Needed for the \"Burnout Meter\" and \"Planned vs Actual\" analytics.

### **Backend (The Brain)**

- **Framework:** **FastAPI (Python)**.

  - *Why:* Native support for AI libraries, async performance, and auto-generated API docs.

- **Authentication:** **OAuth2 + JWT (JSON Web Tokens)**.

  - *Why:* Stateless, secure session management.

- **Task Scheduling:** **APScheduler**.

  - *Why:* Runs the background \"Reflexion Agent\" every 3-5 days to summarize logs.

- **AI & ML:** **LangChain** (Logic) + **Scikit-Learn** (Prediction).

  - *Why:* LangChain manages LLM prompts; Scikit-Learn handles simple time-estimation regression.

### **Database (The Memory)**

- **Database:** **PostgreSQL**.

  - *Why:* The only database that handles **Relational Data** (Tasks/Users) and **Unstructured Data** (JSONB for AI Memory) effectively in one place.

- **ORM:** **SQLAlchemy**.

## 3. Database Schema (SQL) {#database-schema-sql}

This schema is designed for **PostgreSQL**. It includes JSONB columns for AI flexibility and a dedicated courses table for subject management.

### **A. Identity & Profile** {#a.-identity-profile}

> SQL

\-- 1. Users (Auth)  
CREATE TABLE users (  
id SERIAL PRIMARY KEY,  
email VARCHAR(255) UNIQUE NOT NULL,  
username VARCHAR(50) UNIQUE NOT NULL,  
password_hash VARCHAR(255) NOT NULL,  
google_refresh_token VARCHAR(255), \-- Stores long-term GCal token  
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  
);  
  
\-- 2. User Profiles (AI Context)  
CREATE TABLE user_profiles (  
user_id INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,  
full_name VARCHAR(100),  
major VARCHAR(100),  
university VARCHAR(100),  
  
\-- The \"Digital Twin\" Memory  
current_archetype VARCHAR(50) DEFAULT \'Unclassified\', \-- e.g., \'The Night Owl\'  
  
\-- Flexible \"Cold Start\" & Learned Traits  
\-- Stores: Chronotype, Math Confidence, Duration Multipliers  
onboarding_data JSONB DEFAULT \'{}\'  
);

### **B. Academics & Schedule** {#b.-academics-schedule}

> SQL

\-- 3. Courses (Subjects)  
\-- Users define these (e.g., \"Calculus\", \"History\") to link tasks to memory.  
CREATE TABLE courses (  
id SERIAL PRIMARY KEY,  
user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,  
name VARCHAR(100) NOT NULL,  
color_code VARCHAR(7), \-- Hex Color for Calendar UI  
default_priority VARCHAR(20) DEFAULT \'Medium\',  
UNIQUE(user_id, name)  
);  
  
\-- 4. Fixed Schedule (Hard Constraints)  
CREATE TABLE fixed_slots (  
id SERIAL PRIMARY KEY,  
user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,  
day_of_week VARCHAR(10) NOT NULL, \-- \'Monday\', \'Tuesday\'  
start_time TIME NOT NULL,  
end_time TIME NOT NULL,  
label VARCHAR(100), \-- e.g., \"Chemistry Lab\"  
is_google_event BOOLEAN DEFAULT FALSE,  
google_event_id VARCHAR \-- To sync updates back to Google  
);

### **C. Task Engine** {#c.-task-engine}

> SQL

\-- 5. Tasks (The Planner)  
CREATE TABLE tasks (  
id SERIAL PRIMARY KEY,  
user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,  
course_id INTEGER REFERENCES courses(id) ON DELETE SET NULL, \-- Link to Subject  
  
title VARCHAR(255) NOT NULL,  
description TEXT,  
category VARCHAR(50), \-- \'Assignment\', \'Exam\', \'Project\'  
priority VARCHAR(20) DEFAULT \'Medium\',  
  
\-- Scheduling Logic  
deadline TIMESTAMP,  
estimated_duration_mins INTEGER, \-- AI Prediction  
is_high_burden BOOLEAN DEFAULT FALSE,  
status VARCHAR(20) DEFAULT \'Pending\',  
  
\-- Recursive Decomposition (Sub-tasks)  
parent_task_id INTEGER REFERENCES tasks(id) ON DELETE SET NULL,  
  
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP  
);

### **D. Feedback Loop (AI Memory)** {#d.-feedback-loop-ai-memory}

> SQL

\-- 6. Task Logs (The Reality)  
CREATE TABLE task_logs (  
id SERIAL PRIMARY KEY,  
task_id INTEGER REFERENCES tasks(id) ON DELETE CASCADE,  
user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,  
  
completion_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
actual_duration_mins INTEGER, \-- Used to calculate \"Planning Fallacy\"  
drain_intensity INTEGER CHECK (drain_intensity BETWEEN 1 AND 5), \-- Burnout Calc  
  
mood_note TEXT,  
ai_feedback_tags JSONB \-- e.g., \[\"procrastinated\", \"distracted\"\]  
);  
  
\-- 7. AI Rolling Summaries (Reflexion)  
CREATE TABLE ai_memories (  
id SERIAL PRIMARY KEY,  
user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,  
generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  
  
\-- The text summary for the user to read  
summary_text TEXT,  
  
\-- The structured data for the System to read (updates the profile)  
updated_traits JSONB  
);

## 4. JSON Data Structures (AI Memory) {#json-data-structures-ai-memory}

To ensure the \"Memory\" is readable by code (not just LLMs), we enforce the following JSON structures in the onboarding_data column.

**Storage Location:** user_profiles.onboarding_data

> JSON

{  
\"global_settings\": {  
\"chronotype\": \"night_owl\", // Affects scheduling logic (pushes tasks later)  
\"base_energy_level\": 7 // 1-10 scale  
},  
\"subject_modifiers\": {  
\"55\": { // \"55\" is the Course ID for \"Calculus\"  
\"confidence_score\": 3,  
\"duration_multiplier\": 1.5, // System multiplies User Input \* 1.5  
\"drain_rate\": 5 // High drain = Don\'t schedule back-to-back  
},  
\"56\": { // \"56\" is Course ID for \"History\"  
\"confidence_score\": 9,  
\"duration_multiplier\": 0.9, // User usually over-estimates this  
\"drain_rate\": 2  
}  
}  
}
