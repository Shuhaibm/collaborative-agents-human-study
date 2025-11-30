"""
Sample run command: 
    `streamlit run full_human_study.py`
"""

import streamlit as st
import time
import json
import uuid
import os
from datetime import datetime

from collaborator_agent import CollaboratorAgent


# ============================================================================
# STUDY CONFIGURATIONS
# ============================================================================


CODING_PREFERENCES = [
    "When an agent is writing code or explaining a programming concept, you prefer responses that begin with pseudocode (e.g., high-level idea, design rationale) before showing going into implementation details.",
    "If multiple high-level, valid solutions exist for a coding problem (recursion vs. dynamic programming), then you would prefer the agent to present the different approaches and their tradeoffs.",
    "If the code solution requires extensive use of an imported library, the agent should always provide an explanation detailing why the dependency is helpful.",
    "When writing variable names, function names, or method names, you prefer that the agent consistently use camelCase rather than other naming conventions."
]

CODING_PROBLEMS = [
    {
        "id": "p1",
        "title": "Session 1",
        "description": """**Problem #1:**

The function below is intended to walk a directory tree and collect files whose names match a pattern. It always returns an empty list. Can you fix it and/or find a cleaner way to implement it?

```python
import os

def scan_dir(path, pattern):
    curr_results = []
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.endswith(pattern):
                curr_results = curr_results.append(os.path.join(root, f))
    return curr_results
```
"""
    },
    {
        "id": "p2",
        "title": "Session 2",
        "description": "Write a function that resizes an image, converts it to grayscale, and saves it."
    },
    {
        "id": "p3",
        "title": "Session 3",
        "description": "You are implementing an object-oriented program to help students plan their coursework each semester. Your program must support checking whether a student has completed all prerequisites for a course, where some prerequisites include a minimum completion date."
    }
]

MIXED_PREFERENCES = [
    "When producing an answer, you prefer responses that begin with a high-level plan before showing concrete revisions, implementations, solutions, or rewritten text. This plan should outline the conceptual strategy, structural intent, and major steps the agent will take.",
    "If multiple high-level, valid strategies exist for completing a task, you prefer that the agent first present these different approaches along with their tradeoffs. The agent should briefly explain how each strategy would shape the outcome and then ask which direction you want to pursue before producing any detailed edits or solutions."
]

MIXED_PROBLEMS = [
    {
        "id": "p1",
        "title": "Session 1",
        "description": """Add a plot twist to the paragraph below, but make sure the twist (e.g., character-based, setting-based, or perspective-based) integrates smoothly with the existing setup. The twist should feel motivated rather than sudden or random.
\“Nora stood waiting at the empty bus stop, the cold wind tugging at her coat as she checked the time again. The streetlamps flickered in uneven intervals, casting long shadows across the pavement. Behind her, the small bakery she had just left was closing for the night, its warm lights dimming one by one. The bus was already ten minutes late, and the neighborhood felt unusually deserted for a Thursday evening.\”"""
    },
    {
        "id": "p2",
        "title": "Session 2",
        "description": "How many ways are there to put 4 distinguishable balls into 2 indistinguishable boxes?"
    },
    {
        "id": "p3",
        "title": "Session 3",
        "description": "Write a function that resizes an image, converts it to grayscale, and saves it."
    }
]

# Study condition configurations
STUDY_CONDITIONS = {
    "coding_standard_agent": {
        "name": "Coding Study - Version A",
        "description": "You will be solving debugging, implementation, and object-oriented design problems.",
        "uses_memory": False,
        "preferences": CODING_PREFERENCES,
        "problems": CODING_PROBLEMS
    },
    "coding_collaborative_agent": {
        "name": "Coding Study - Version B",
        "description": "You will be solving debugging, implementation, and object-oriented design problems.",
        "uses_memory": True,
        "preferences": CODING_PREFERENCES,
        "problems": CODING_PROBLEMS
    },
    "mixed_standard_agent": {
        "name": "Mixed Domains Study - Version A",
        "description": "You will be solving a writing, math, and coding problems.",
        "uses_memory": False,
        "preferences": CODING_PREFERENCES,
        "problems": MIXED_PROBLEMS
    },
    "mixed_collaborative_agent": {
        "name": "Mixed Domains Study - Version B",
        "description": "You will be solving a writing, math, and coding problems.",
        "uses_memory": True,
        "preferences": MIXED_PREFERENCES,
        "problems": MIXED_PROBLEMS
    }
}

# ============================================================================
# API CONFIGURATION
# ============================================================================

MODEL_NAME = "together_ai/meta-llama/Llama-3.3-70B-Instruct-Turbo"

try:
    api_key = st.secrets["TOGETHER_API_KEY"]
except (FileNotFoundError, KeyError):
    api_key = os.getenv("TOGETHER_API_KEY", "")
    if not api_key:
        st.error("⚠️ API key not found. Please configure TOGETHER_API_KEY in secrets or environment.")
        st.stop()

os.environ["TOGETHERAI_API_KEY"] = api_key
os.environ["TOGETHER_API_KEY"] = api_key
API_BASE = None
API_KEY = None


def init_session():
    """Initialize session state variables"""
    if "page" not in st.session_state:
        st.session_state.page = "intro"
    
    if "selected_study" not in st.session_state:
        st.session_state.selected_study = None

    if "current_problem_index" not in st.session_state:
        st.session_state.current_problem_index = 0
    
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "agent_notes" not in st.session_state:
        st.session_state.agent_notes = ""

    # Track completed studies and store all data
    if "completed_studies" not in st.session_state:
        st.session_state.completed_studies = set()
    
    if "all_study_data" not in st.session_state:
        st.session_state.all_study_data = {
            "participant_id": str(uuid.uuid4()), 
            "overall_start_time": str(datetime.now()),
            "studies": []  # Will contain data from all 4 studies
        }


def show_study_selector():
    """Landing page to select which study condition to run"""
    st.title("🎓 Collaborative Agents Research Study")
    st.markdown("### Study Selection")
    
    completed_count = len(st.session_state.completed_studies)
    total_count = len(STUDY_CONDITIONS)
    
    # Progress indicator
    st.progress(completed_count / total_count)
    st.markdown(f"**Progress: {completed_count}/{total_count} studies completed**")
    
    st.write("")
    
    if completed_count == total_count:
        st.success("🎉 All studies completed! Please proceed to download your data.")
        if st.button("📥 Download All Data", type="primary"):
            st.session_state.page = "final_download"
            st.rerun()
        return
    
    st.write("""
    Please complete all of the following studies. You can complete them in any order.
    At the end, you'll download a single file containing all your data.
    """)
    
    st.write("")
    
    # Create buttons for each study condition
    for study_key, study_info in STUDY_CONDITIONS.items():
        is_completed = study_key in st.session_state.completed_studies
        
        with st.container(border=True):
            col1, col2 = st.columns([3, 1])
            with col1:
                status_icon = "✅" if is_completed else "⏳"
                st.markdown(f"{status_icon} **{study_info['name']}**")
                st.caption(study_info['description'])
            with col2:
                if is_completed:
                    st.success("Done")
                else:
                    if st.button("Start", key=f"btn_{study_key}", type="primary"):
                        st.session_state.selected_study = study_key
                        st.session_state.study_start_time = str(datetime.now())
                        st.session_state.page = "study_intro"
                        st.rerun()
    
    st.divider()
    st.caption(f"Complete all {total_count} studies to download your data.")


def show_intro_page():
    """Introduction page with consent and instructions - shown only once at the very beginning"""
    st.title("🎓 Collaborative Agents Research Study")
    st.markdown("#### Welcome")
    
    st.write("""
    Thank you for participating in our research study on collaborative AI agents!
    
    In this study, you will complete **4 different study conditions**, each consisting of 3 problem-solving sessions.
    
    ### What to Expect:
    - **Duration:** Approximately 1.5 hours total (all 4 studies)
    - **Tasks:** In each session, you will work with an agent to solve a problem. After the session, you will be asked to answer a brief survey about your experience.
    - **Data:** At the end, you will download a single file with all your data.

    ### Instructions:
    You will be provided with interaction preferences for each study that describe how you should expect the agent to behave. You are also free to add any additional preferences of your own that help you with solving the problem.
    For each session:
    - You will be provided with a problem
    - Your goal is to have the agent help you solve the problem
    - Avoid copy and pasting, unless you have to (e.g. the problem provides a code snippet or paragraph you need to change)
    - You must ensure the agent adheres to your preferences throughout the session
    - When completed, click "✅ Task Complete" to move to the survey
    """)

    st.write("")
    
    with st.container(border=True):
        st.markdown("#### 🔒 Data Collection & Consent")
        st.markdown("""
        Before beginning, please check the box below if you agree to allow us to collect your interaction data and survey responses as part of our research. We will anonymize the data before sharing it publicly.

        **Privacy Notice:** To protect your privacy, please do **NOT** reveal any personal identifying information throughout the study.
        """)

        agreed = st.checkbox("I agree to participate in this research study")

    st.divider()

    if st.button("Begin Studies", type="primary", disabled=not agreed):
        st.session_state.page = "study_select"
        st.rerun()

    if not agreed:
        st.caption("⚠️ *Please agree to participate above to proceed.*")


def show_study_intro_page():
    """Show intro for each individual study with its specific preferences"""
    config = STUDY_CONDITIONS[st.session_state.selected_study]
    
    st.title("🎓 Collaborative Agents Study")
    st.markdown(f"#### {config['name']}")
    
    # Display preferences in a highlighted container
    with st.container(border=True):
        st.markdown("### 📋 Your Assigned Preferences")
        st.markdown("For this study, please adopt the following preferences (you will be able to see these throughout the sessions):")
        st.write("")
        
        for i, pref in enumerate(config["preferences"], 1):
            st.markdown(f"**{i}.** {pref}")
        st.markdown(f"Feel free to apply any additional preferences of your own that help you with solving the problem.")
    
    st.write("")
    st.markdown("**Remember these preferences as you interact with the agent throughout the sessions.**")
    st.write("")

    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("← Back to Study Selection", type="secondary"):
            st.session_state.page = "study_select"
            st.rerun()
    
    with col2:
        if st.button("Begin Study →", type="primary"):
            # Initialize agent for this study
            user_prefs_text = "\n".join([f"{i+1}. {pref}" for i, pref in enumerate(config["preferences"])])
            
            kwargs = {
                "model_name": MODEL_NAME,
                # "user_preferences": user_prefs_text,
            }
            if API_BASE and API_KEY:
                kwargs["api_base"] = API_BASE
                kwargs["api_key"] = API_KEY
            
            st.session_state.agent = CollaboratorAgent(**kwargs)
            st.session_state.page = "study"
            st.rerun()


def show_study_interface():
    """Main study interface with chat"""
    config = STUDY_CONDITIONS[st.session_state.selected_study]
    problems = config["problems"]
    
    if st.session_state.current_problem_index >= len(problems):
        # Study complete, go to survey for last session
        st.session_state.page = "survey"
        st.rerun()
        return

    current_problem = problems[st.session_state.current_problem_index]
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.header(f"Session {st.session_state.current_problem_index + 1}/{len(problems)}")
        st.progress((st.session_state.current_problem_index) / len(problems))
        st.divider()
        st.warning("REMEMBER YOUR PREFERENCES:")
        for pref in config["preferences"]:
            st.caption(f"- {pref}")
        st.divider()

        # Reminder before completing task
        st.info("⚠️ Before completing: Did you verify that all your preferences were adhered to?")
        
        # Moves to Survey Page (Doesn't save data yet)
        if st.button("✅ Task Complete", type="primary"):
            st.session_state.page = "survey"
            st.rerun()

    # --- CHAT UI ---
    st.subheader(current_problem["title"])
    
    # Display problem description with proper formatting
    with st.container(border=True):
        st.markdown("**Task: Please solve the problem below by communicating with the agent. Remember, they do not see this problem description.** Avoid copy and pasting, unless you have to (e.g. the problem provides a code snippet or paragraph you need to change).")
        st.markdown(current_problem['description'])

    # Display History
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Handle Input
    if prompt := st.chat_input("Type here..."):
        # User message
        st.session_state.messages.append({"role": "user", "content": prompt, "timestamp": str(datetime.now())})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Agent message
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Build conversation for agent (include history for context)
                conversation = [{"role": msg["role"], "content": msg["content"]} 
                               for msg in st.session_state.messages 
                               if "role" in msg and "content" in msg]
                
                # Get response from agent
                result = st.session_state.agent.generate_collaborator_response(conversation)
                
                if result and "response" in result:
                    response_text = result["response"]
                else:
                    response_text = "I apologize, but I'm having trouble generating a response. Could you please try rephrasing your question?"
                
                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text, "timestamp": str(datetime.now())})


def show_survey_interface():
    """Post-session survey"""
    st.title("📋 Post-Session Survey")

    st.write("Please answer the following questions regarding your experience in the last session.")
    
    with st.form("survey_form"):
        q1 = st.slider("""1. How well did the agent adhere to your preferences?
        
        - 1: Struggled to adhere to preferences even after I specified them
        
        - 2: Adhered to some preferences after I specified them, but also struggled with others
        
        - 3: Adhered to all preferences after I specified them

        - 4: Proactively adhered to some preferences without me specifying them

        - 5: Proactively adhered to all preferences without me specifying them""",
        1, 5, 3)

        st.divider()

        q2 = st.slider("""2. How well did the agent remember your preferences from previous sessions? (If this is the first session, select 1)

        - 1: Remembered none of my preferences from previous sessions. I had to repeat everything.

        - 2: Remembered few of my preferences from previous sessions. I had to repeat most of them.

        - 3: Remembered some of my preferences from previous sessions, but there were some that I had to repeat.

        - 4: Remembered most of my preferences from previous sessions, but I had to gently remind it of small details.

        - 5: Remembered all of my preferences from previous sessions perfectly, and I did not have to repeat myself at all.""",
        1, 5, 3)

        st.divider()

        q3 = st.radio(
            "3. How helpful was the agent's preference adherence, and in what way did it impact your collaborative problem-solving experience?",
            options=[
                "Did not adhere to my preferences, and this negatively impacted my experience.",
                
                "Did not adhere to my preferences, but this did not negatively impact my experience.",
                
                "Adhered to my preferences, but this did not positively impact my experience.",

                "Adhered to my preferences, and this positively impacted my experience."
            ]
        )

        st.divider()

        q4 = st.slider("""4. How confident are you in the agent's ability to continuously improve collaboration and remember your preferences in future sessions?

        - 1: Not confident - I expect to always repeat myself

        - 2: Slightly confident - I expect to repeat most preferences

        - 3: Moderately confident - I expect to repeat some preferences  

        - 4: Confident - I expect to only give occasional reminders

        - 5: Very confident - I expect it to remember everything""",
        1, 5, 3)

        st.divider()

        q_sat = st.slider(
            "Overall, how satisfied were you with this session?",
            1, 5, 3,
            format="%d"  
        )

        st.divider()

        q5 = st.text_area(
            "5. Were there any specific moments in this session where the agent's behavior stood out to you?",
            placeholder="Example: 'I was surprised it remembered to use Python instead of C++...'"
        )

        q6 = st.text_area(
            "6. Were there any additional preferences that you enforced while solving the problem? How well did the agent adhere to them? Did they remember them from previous sessions?",
            placeholder="Example: 'I asked the agent to use Python instead of C++...'"
        )

        submitted = st.form_submit_button("Submit & Continue")
        
        if submitted:
            config = STUDY_CONDITIONS[st.session_state.selected_study]
            current_problem = config["problems"][st.session_state.current_problem_index]
            
            # Save agent notes before update
            agent_notes_before = st.session_state.agent_notes
            
            # Update agent memory if this is a collaborative condition
            if config["uses_memory"]:
                conversation = [{"role": msg["role"], "content": msg["content"]} 
                              for msg in st.session_state.messages 
                              if "role" in msg and "content" in msg]
                
                # Update agent notes
                if st.session_state.agent_notes:
                    result = st.session_state.agent.update_agent_notes(st.session_state.agent_notes, conversation)
                else:
                    result = st.session_state.agent.update_agent_notes(
                        "Initial notes: No preferences learned yet.",
                        conversation
                    )
                
                # Get updated agent notes
                if result and "agent_notes" in result:
                    st.session_state.agent_notes = result["agent_notes"]
                    
                    # Reinitialize agent with updated notes
                    user_prefs_text = "\n".join([f"{i+1}. {pref}" for i, pref in enumerate(config["preferences"])])
                    kwargs = {
                        "model_name": MODEL_NAME,
                        "agent_notes": st.session_state.agent_notes,
                    }
                    if API_BASE and API_KEY:
                        kwargs["api_base"] = API_BASE
                        kwargs["api_key"] = API_KEY
                    
                    st.session_state.agent = CollaboratorAgent(**kwargs)
            
            agent_notes_after = st.session_state.agent_notes
            
            # Create session record
            session_record = {
                "session_index": st.session_state.current_problem_index,
                "problem_id": current_problem['id'],
                "problem_title": current_problem['title'],
                "chat_history": st.session_state.messages,
                "agent_notes_before": agent_notes_before,
                "agent_notes_after": agent_notes_after,
                "survey_responses": {
                    "q1_preference_adherence": q1,
                    "q2_preference_memory": q2,
                    "q3_preference_impact": q3,
                    "q4_confidence": q4,
                    "q_satisfaction": q_sat,
                    "q5_memorable_moments": q5
                },
                "timestamp": str(datetime.now())
            }
            
            # Store session data temporarily
            if "current_study_sessions" not in st.session_state:
                st.session_state.current_study_sessions = []
            st.session_state.current_study_sessions.append(session_record)
            
            # Move to next session
            st.session_state.current_problem_index += 1
            st.session_state.messages = []
            
            # Check if this study is complete (all 3 sessions done)
            if st.session_state.current_problem_index >= len(config["problems"]):
                # Save completed study data
                study_record = {
                    "study_condition": st.session_state.selected_study,
                    "study_name": config["name"],
                    "start_time": st.session_state.get("study_start_time", str(datetime.now())),
                    "end_time": str(datetime.now()),
                    "assigned_preferences": config["preferences"],
                    "uses_memory": config["uses_memory"],
                    "sessions": st.session_state.current_study_sessions
                }
                
                st.session_state.all_study_data["studies"].append(study_record)
                st.session_state.completed_studies.add(st.session_state.selected_study)
                
                # Reset for next study
                st.session_state.current_problem_index = 0
                st.session_state.current_study_sessions = []
                st.session_state.agent_notes = ""
                st.session_state.selected_study = None
                
                # Return to study selection
                st.session_state.page = "study_select"
            else:
                # Continue to next session in same study
                st.session_state.page = "study"
            
            st.rerun()


def show_final_download_page():
    """Final page with data download"""
    st.balloons()
    st.success("Study Complete! Thank you for your participation.")
    
    st.markdown("""
    ### Download Your Data
    Please download your session data below and send it to the study coordinator.
    """)
    
    # Convert the Python dictionary to a JSON string
    json_string = json.dumps(st.session_state.all_study_data, indent=4)
    
    # Create the Download Button
    st.download_button(
        label="📥 Download Study JSON",
        data=json_string,
        file_name=f"study_data_{st.session_state.all_study_data['participant_id']}.json",
        mime="application/json"
    )

    # Optional: Display what's in the file so they trust it
    with st.expander("View Data Preview"):
        st.json(st.session_state.all_study_data)
    
    st.divider()
    
    # Option to start a new study or return to study selection
    st.markdown("### What's Next?")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Start Another Study", type="primary", use_container_width=True):
            # Reset all session state
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    with col2:
        if st.button("👋 Exit Study", type="secondary", use_container_width=True):
            st.info("Thank you for your participation! You may now close this window.")
            st.stop()


def main():
    st.set_page_config(page_title="Collaborative Agent Study", layout="centered")
    init_session()
    
    if st.session_state.page == "intro":
        show_intro_page()
    elif st.session_state.page == "study_select":
        show_study_selector()
    elif st.session_state.page == "study_intro":
        show_study_intro_page()
    elif st.session_state.page == "study":
        show_study_interface()
    elif st.session_state.page == "survey":
        show_survey_interface()
    elif st.session_state.page == "final_download":
        show_final_download_page()

if __name__ == "__main__":
    main()