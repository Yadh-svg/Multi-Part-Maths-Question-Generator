import streamlit as st
import re
from google import genai
from google.genai import types

st.set_page_config(page_title="Multi-Part Maths Prompt Builder", layout="wide")

# ------------------ Universal Taxonomy List ------------------
# All taxonomies are available for all questions, independent of DOK level
ALL_TAXONOMIES = ["Remembering", "Understanding", "Applying", "Evaluating", "Analysing"]

def get_taxonomies_for_dok(dok_level):
    """Returns all available taxonomies - taxonomy selection is independent of DOK level."""
    return ALL_TAXONOMIES

# ------------------ YAML SAFE QUOTING ------------------
def yq(val):
    if val is None:
        return '""'
    safe = str(val).replace('"', '\\"')
    return f'"{safe}"'

# ------------------ DEFAULT SUBPART ------------------
def default_subpart(index):
    """Returns default configuration for a subpart based on index."""
    if index == 0:  # Part a
        return {
            "label": "a",
            "DOK": 1,
            "marks": 1,
            "taxonomy": "Remembering"  # Single taxonomy for subpart
        }
    elif index == 1:  # Part b
        return {
            "label": "b",
            "DOK": 2,
            "marks": 1,
            "taxonomy": "Understanding"  # Single taxonomy for subpart
        }
    elif index == 2:  # Part c
        return {
            "label": "c",
            "DOK": 3,
            "marks": 2,
            "taxonomy": "Analysing"  # Single taxonomy for subpart
        }
    else:  # Additional parts default to DOK 1
        return {
            "label": chr(ord("a") + index),
            "DOK": 1,
            "marks": 1,
            "taxonomy": "Remembering"  # Single taxonomy for subpart
        }

# ------------------ DEFAULT MCQ QUESTION ------------------
def default_mcq_question(index):
    """Returns default configuration for an MCQ question based on index."""
    return {
        "DOK": 1,
        "marks": 1,
        "taxonomy": "Remembering"  # Single taxonomy for MCQ
    }

# ------------------ DEFAULT FIB QUESTION ------------------
def default_fib_question(index):
    """Returns default configuration for a FIB question based on index."""
    return {
        "DOK": 1,
        "marks": 1,
        "taxonomy": "Remembering"  # Single taxonomy for FIB
    }

# ------------------ INITIALIZE session_state ONCE ------------------
if "initialized" not in st.session_state:
    st.session_state.initialized = True

    st.session_state.Number_of_subparts = 3
    st.session_state.Number_of_questions = 1

    st.session_state.Grade = "Grade 4"
    st.session_state.Curriculum = "CBSE"
    st.session_state.Subject = "Mathematics"
    st.session_state.Chapter = ""
    st.session_state.Topic = "Fractions"
    st.session_state.New_Concept = "Fraction addition, Fraction subtraction, Fraction multiplication, Fraction division"
    st.session_state.Old_Concept = "Basic understanding of fractions, Number operations"
    st.session_state.Additional_Notes = ""  # Additional configuration for question/solution generation
    st.session_state.Question_Type = "Multi-Part"  # Question type: Multi-Part, MCQ, or Fill in the Blanks
    st.session_state.Input_Mode = "Manual"  # Default to Manual mode

    # For Multi-Part questions
    st.session_state.subparts = [default_subpart(i) for i in range(st.session_state.Number_of_subparts)]
    
    # For MCQ questions
    st.session_state.mcq_questions = [default_mcq_question(i) for i in range(st.session_state.Number_of_questions)]
    
    # For FIB questions
    st.session_state.fib_questions = [default_fib_question(i) for i in range(st.session_state.Number_of_questions)]

# ------------------ SUBPARTS UPDATE CALLBACK ------------------
def update_subparts():
    """
    Callback that runs when st.session_state.Number_of_subparts changes.
    Resizes st.session_state.subparts and clears stale widget keys.
    """
    try:
        new_n = int(st.session_state.Number_of_subparts)
    except Exception:
        return

    old_n = len(st.session_state.subparts)

    if new_n > old_n:
        # extend
        st.session_state.subparts += [default_subpart(i) for i in range(old_n, new_n)]
    elif new_n < old_n:
        # truncate
        st.session_state.subparts = st.session_state.subparts[:new_n]

    # Clear dynamic widget keys for indices >= new_n so Streamlit rebuilds them fresh.
    # Use a safe range up to max(old_n, new_n)+3 to remove leftovers.
    max_check = max(old_n, new_n) + 3
    for i in range(max_check):
        if i >= new_n:
            st.session_state.pop(f"sub_{i}_dok", None)
            st.session_state.pop(f"sub_{i}_marks", None)
            st.session_state.pop(f"sub_{i}_tax", None)

# ------------------ MCQ QUESTIONS UPDATE CALLBACK ------------------
def update_mcq_questions():
    """
    Callback that runs when st.session_state.Number_of_questions changes in MCQ mode.
    Resizes st.session_state.mcq_questions and clears stale widget keys.
    """
    try:
        new_n = int(st.session_state.Number_of_questions)
    except Exception:
        return

    if "mcq_questions" not in st.session_state:
        st.session_state.mcq_questions = [default_mcq_question(i) for i in range(new_n)]
        return

    old_n = len(st.session_state.mcq_questions)

    if new_n > old_n:
        # extend
        st.session_state.mcq_questions += [default_mcq_question(i) for i in range(old_n, new_n)]
    elif new_n < old_n:
        # truncate
        st.session_state.mcq_questions = st.session_state.mcq_questions[:new_n]

    # Clear dynamic widget keys for indices >= new_n
    max_check = max(old_n, new_n) + 3
    for i in range(max_check):
        if i >= new_n:
            st.session_state.pop(f"mcq_{i}_dok", None)
            st.session_state.pop(f"mcq_{i}_marks", None)
            st.session_state.pop(f"mcq_{i}_tax", None)

# ------------------ FIB QUESTIONS UPDATE CALLBACK ------------------
def update_fib_questions():
    """
    Callback that runs when st.session_state.Number_of_questions changes in FIB mode.
    Resizes st.session_state.fib_questions and clears stale widget keys.
    """
    try:
        new_n = int(st.session_state.Number_of_questions)
    except Exception:
        return

    if "fib_questions" not in st.session_state:
        st.session_state.fib_questions = [default_fib_question(i) for i in range(new_n)]
        return

    old_n = len(st.session_state.fib_questions)

    if new_n > old_n:
        # extend
        st.session_state.fib_questions += [default_fib_question(i) for i in range(old_n, new_n)]
    elif new_n < old_n:
        # truncate
        st.session_state.fib_questions = st.session_state.fib_questions[:new_n]

    # Clear dynamic widget keys for indices >= new_n
    max_check = max(old_n, new_n) + 3
    for i in range(max_check):
        if i >= new_n:
            st.session_state.pop(f"fib_{i}_dok", None)
            st.session_state.pop(f"fib_{i}_marks", None)
            st.session_state.pop(f"fib_{i}_tax", None)

# ------------------ ASSEMBLE PROMPT ------------------
def assemble_prompt(state):
    """
    Load prompt.yaml and replace placeholders with YAML-safe quotes.
    Selects the appropriate prompt template based on Question_Type and Input_Mode.
    Maps Streamlit field names to prompt placeholders.
    """
    try:
        with open("prompt.yaml", "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return "Error: prompt.yaml file not found!"

    question_type = state.get("Question_Type", "Multi-Part")
    input_mode = state.get("Input_Mode", "Manual")

    # Select the appropriate prompt template based on Question_Type and Input_Mode
    if question_type == "Multi-Part":
        if input_mode == "PDF Upload":
            # Multi-Part + PDF
            if "multi_part_maths_pdf:" in content:
                prompt_template = content.split("multi_part_maths_pdf:")[1].strip()
                if prompt_template.startswith("|"):
                    prompt_template = prompt_template[1:].strip()
                # Split at next template key if exists
                if "mcq_questions:" in prompt_template:
                    prompt_template = prompt_template.split("mcq_questions:")[0].strip()
            else:
                return "Error: multi_part_maths_pdf template not found in prompt.yaml"
        else:
            # Multi-Part + Manual
            prompt_template = content.split("multi_part_maths:")[1].strip()
            if prompt_template.startswith("|"):
                prompt_template = prompt_template[1:].strip()
            # Split at next template key
            if "multi_part_maths_pdf:" in prompt_template:
                prompt_template = prompt_template.split("multi_part_maths_pdf:")[0].strip()
    elif question_type == "MCQ":
        if input_mode == "PDF Upload":
            # MCQ + PDF
            if "mcq_questions_pdf:" in content:
                prompt_template = content.split("mcq_questions_pdf:")[1].strip()
                if prompt_template.startswith("|"):
                    prompt_template = prompt_template[1:].strip()
            else:
                return "Error: mcq_questions_pdf template not found in prompt.yaml"
        else:
            # MCQ + Manual
            if "mcq_questions:" in content:
                prompt_template = content.split("mcq_questions:")[1].strip()
                if prompt_template.startswith("|"):
                    prompt_template = prompt_template[1:].strip()
                # Split at next template key
                if "mcq_questions_pdf:" in prompt_template:
                    prompt_template = prompt_template.split("mcq_questions_pdf:")[0].strip()
            else:
                return "Error: mcq_questions template not found in prompt.yaml"
    else:
        # Fill in the Blanks
        if input_mode == "PDF Upload":
            # FIB + PDF
            if "FIB_pdf:" in content:
                prompt_template = content.split("FIB_pdf:")[1].strip()
                if prompt_template.startswith("|"):
                    prompt_template = prompt_template[1:].strip()
            else:
                return "Error: FIB_pdf template not found in prompt.yaml"
        else:
            # FIB + Manual
            if "FIB:" in content:
                prompt_template = content.split("FIB:")[1].strip()
                if prompt_template.startswith("|"):
                    prompt_template = prompt_template[1:].strip()
                # Split at next template key
                if "FIB_pdf:" in prompt_template:
                    prompt_template = prompt_template.split("FIB_pdf:")[0].strip()
            else:
                return "Error: FIB template not found in prompt.yaml"

    # Replace common placeholders (work for both Multi-Part and MCQ)
    prompt_text = prompt_template.replace('{{Grade}}', yq(state["Grade"]))
    prompt_text = prompt_text.replace('{{Curriculam}}', yq(state["Curriculum"]))
    prompt_text = prompt_text.replace('{{Subject}}', yq(state["Subject"]))
    prompt_text = prompt_text.replace('{{Chapter}}', yq(state["Chapter"]))
    prompt_text = prompt_text.replace('{{Topic}}', yq(state["Topic"]))
    prompt_text = prompt_text.replace('{{New_Concept}}', yq(state["New_Concept"]))
    prompt_text = prompt_text.replace('{{Old_Concept}}', yq(state["Old_Concept"]))
    prompt_text = prompt_text.replace('{{Additional_Notes}}', yq(state.get("Additional_Notes", "")))
    prompt_text = prompt_text.replace('{{Number_of_questions}}', yq(str(state["Number_of_questions"])))

    # MCQ prompts use different placeholder names, map them
    prompt_text = prompt_text.replace('{subject}', yq(state["Subject"]))
    prompt_text = prompt_text.replace('{grade}', yq(state["Grade"]))
    prompt_text = prompt_text.replace('{chapter}', yq(state["Chapter"]))
    prompt_text = prompt_text.replace('{topics}', yq(state["Topic"]))
    prompt_text = prompt_text.replace('{new_concept}', yq(state["New_Concept"]))
    prompt_text = prompt_text.replace('{old_concept}', yq(state["Old_Concept"]))
    prompt_text = prompt_text.replace('{additional_notes}', yq(state.get("Additional_Notes", "")))
    prompt_text = prompt_text.replace('{num_questions}', yq(str(state["Number_of_questions"])))

    if question_type == "Multi-Part":
        # Multi-Part specific: inject subpart specifications
        num_sub = state["Number_of_subparts"]
        prompt_text = prompt_text.replace('{{Number_of_subparts}}', yq(str(num_sub)))

        # Build subpart specs
        subpart_specs = ""
        for s in state["subparts"]:
            # Taxonomy is now a single string for multi-part
            taxonomy_value = s["taxonomy"] if isinstance(s["taxonomy"], str) else ", ".join(s["taxonomy"])
            subpart_specs += (
                f"      {s['label']} → DOK {s['DOK']}, "
                f"Marks: {s['marks']}, Taxonomy: {taxonomy_value}\n"
            )

        # Inject using the existing regex
        pattern = r'(- Number of Sub-Parts:.*?)(For each sub-part.*?)(- From the provided input.*?\n)'
        replacement = f"- Number of Sub-Parts: {num_sub}\n\n{subpart_specs}"
        prompt_text = re.sub(pattern, replacement, prompt_text, flags=re.DOTALL)
    elif question_type == "MCQ":
        # MCQ specific: inject question-level DOK, Marks, and Taxonomy
        # For MCQ, we build a specification for each question
        mcq_specs = ""
        for idx, q in enumerate(state["mcq_questions"], 1):
            # Taxonomy is now a single string for MCQ
            taxonomy_value = q["taxonomy"] if isinstance(q["taxonomy"], str) else ", ".join(q["taxonomy"])
            mcq_specs += f"Question {idx}: DOK {q['DOK']}, Marks: {q['marks']}, Taxonomy: {taxonomy_value}\n"
        
        # Replace placeholders with the first question's config (for backward compatibility)
        # and add the full specification list
        first_q = state["mcq_questions"][0] if state["mcq_questions"] else default_mcq_question(0)
        taxonomy_value = first_q["taxonomy"] if isinstance(first_q["taxonomy"], str) else ", ".join(first_q["taxonomy"])
        
        prompt_text = prompt_text.replace('{dok_level}', yq(str(first_q["DOK"])))
        prompt_text = prompt_text.replace('{marks}', yq(str(first_q["marks"])))
        prompt_text = prompt_text.replace('{taxonomy}', yq(taxonomy_value))
        
        # Add detailed specifications if multiple questions
        if len(state["mcq_questions"]) > 1:
            prompt_text = prompt_text.replace(
                '### Question Requirements',
                f'### Question Requirements\n\n**Specific requirements for each question:**\n{mcq_specs}\n'
            )
    else:
        # Fill in the Blanks specific: inject question-level DOK, Marks, and Taxonomy
        # For FIB, we build a specification for each question (similar to MCQ)
        fib_specs = ""
        for idx, q in enumerate(state["fib_questions"], 1):
            # Taxonomy is a single string for FIB
            taxonomy_value = q["taxonomy"] if isinstance(q["taxonomy"], str) else ", ".join(q["taxonomy"])
            fib_specs += f"Question {idx}: DOK {q['DOK']}, Marks: {q['marks']}, Taxonomy: {taxonomy_value}\n"
        
        # Replace placeholders with the first question's config (for backward compatibility)
        # and add the full specification list
        first_q = state["fib_questions"][0] if state["fib_questions"] else default_fib_question(0)
        taxonomy_value = first_q["taxonomy"] if isinstance(first_q["taxonomy"], str) else ", ".join(first_q["taxonomy"])
        
        prompt_text = prompt_text.replace('{dok_level}', yq(str(first_q["DOK"])))
        prompt_text = prompt_text.replace('{marks}', yq(str(first_q["marks"])))
        prompt_text = prompt_text.replace('{taxonomy}', yq(taxonomy_value))
        
        # Add detailed specifications if multiple questions
        if len(state["fib_questions"]) > 1:
            prompt_text = prompt_text.replace(
                '### Question Requirements',
                f'### Question Requirements\n\n**Specific requirements for each question:**\n{fib_specs}\n'
            )

    return prompt_text

# ------------------ GEMINI CALL ------------------
def generate_questions_with_gemini(prompt, api_key):
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=6500)
            )
        )
        # prefer .text if available
        return getattr(response, "text", str(response))
    except Exception as e:
        return f"Error generating questions: {e}"

# ------------------ GEMINI PDF CALL ------------------
def generate_questions_with_pdf(prompt, pdf_bytes, api_key):
    """Generate questions using PDF content and prompt."""
    try:
        client = genai.Client(api_key=api_key)
        
        # Create PDF part from bytes
        pdf_part = types.Part.from_bytes(
            data=pdf_bytes,
            mime_type='application/pdf'
        )
        
        # Generate content with PDF and prompt
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=[pdf_part, prompt],
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=6500)
            )
        )
        return getattr(response, "text", str(response))
    except Exception as e:
        return f"Error generating questions with PDF: {e}"

# ------------------ UI ------------------
st.title("Multi-Part Maths Question Generator")

# ---- Question Type Selection (FIRST) ----
st.radio("Question Type", options=["Multi-Part", "MCQ", "Fill in the Blanks"], key="Question_Type", horizontal=True,
         help="Multi-Part: Questions with sub-parts (a, b, c). MCQ: Multiple Choice Questions with 4 options. Fill in the Blanks: Questions with blanks to fill in.")

# ---- Input Mode Selection (SECOND) ----
st.radio("Input Mode", options=["Manual", "PDF Upload"], key="Input_Mode", horizontal=True,
         help="Manual: Enter concepts as text. PDF: Upload a PDF file containing the new concepts.")

st.markdown("---")

# ---- Basic inputs (write directly into session_state) ----
grade_options = [f"Grade {i}" for i in range(1, 13)]
st.selectbox("Grade", options=grade_options,
             index=grade_options.index(st.session_state.Grade) if st.session_state.Grade in grade_options else 0,
             key="Grade")

st.text_input("Curriculum", value=st.session_state.Curriculum, key="Curriculum")

subject_options = ["Mathematics", "Integrated Math"]
st.selectbox("Subject", options=subject_options,
             index=subject_options.index(st.session_state.Subject) if st.session_state.Subject in subject_options else 0,
             key="Subject")

st.text_input("Chapter/Unit", value=st.session_state.Chapter, key="Chapter")
st.text_input("Topic", value=st.session_state.Topic, key="Topic")

# ---- Conditional rendering based on Input Mode ----
# Ensure New_Concept exists in session_state (it might be removed if widget was hidden)
if "New_Concept" not in st.session_state:
    st.session_state.New_Concept = "Fraction addition, Fraction subtraction, Fraction multiplication, Fraction division"

if st.session_state.Input_Mode == "Manual":
    # Manual mode: show both New Concept and Old Concept
    st.text_area("New Concept (everything in this chapter)", value=st.session_state.New_Concept, key="New_Concept", 
                 help="Enter all the concepts and topics covered in this chapter")
    st.text_area("Old Concept (prerequisite knowledge to check)", value=st.session_state.Old_Concept, key="Old_Concept",
                 help="Enter the concepts the student should already know from previous chapters")
    st.text_area("Additional Notes (optional configuration)", value=st.session_state.Additional_Notes, key="Additional_Notes",
                 help="Add any extra instructions to configure how the question or solution should be generated")
else:
    # PDF mode: show PDF uploader and only Old Concept
    st.file_uploader("Upload PDF (New Concept)", type=["pdf"], key="pdf_file",
                    help="Upload a PDF file containing the new concepts for this chapter")
    st.text_area("Old Concept (prerequisite knowledge to check)", value=st.session_state.Old_Concept, key="Old_Concept",
                 help="Enter the concepts the student should already know from previous chapters")
    st.text_area("Additional Notes (optional configuration)", value=st.session_state.Additional_Notes, key="Additional_Notes",
                 help="Add any extra instructions to configure how the question or solution should be generated")

# Number of Questions: editable, stored immediately (but prompt only built on Generate)
# Add callback for MCQ and FIB mode to update question configurations
if st.session_state.Question_Type == "MCQ":
    st.number_input("Number of Questions", min_value=1, max_value=10,
                    value=st.session_state.Number_of_questions, step=1, key="Number_of_questions",
                    on_change=update_mcq_questions)
elif st.session_state.Question_Type == "Fill in the Blanks":
    st.number_input("Number of Questions", min_value=1, max_value=10,
                    value=st.session_state.Number_of_questions, step=1, key="Number_of_questions",
                    on_change=update_fib_questions)
else:
    st.number_input("Number of Questions", min_value=1, max_value=10,
                    value=st.session_state.Number_of_questions, step=1, key="Number_of_questions")

# Conditional rendering based on Question Type
if st.session_state.Question_Type == "Multi-Part":
    # Multi-Part mode: show Number of Sub-Parts
    # Defensive initialization in case user switches from MCQ to Multi-Part
    if "Number_of_subparts" not in st.session_state:
        st.session_state.Number_of_subparts = 3
    if "subparts" not in st.session_state:
        st.session_state.subparts = [default_subpart(i) for i in range(st.session_state.Number_of_subparts)]
    
    st.number_input("Number of Sub-Parts per Question",
                    min_value=1, max_value=26,
                    value=st.session_state.Number_of_subparts,
                    step=1,
                    key="Number_of_subparts",
                    on_change=update_subparts)

st.markdown("---")

# ---- Subparts/MCQ Configuration ----
if st.session_state.Question_Type == "Multi-Part":
    st.subheader("Subparts Configuration")
    cols = st.columns((1, 1, 2, 3))
    cols[0].markdown("**Part**")
    cols[1].markdown("**DOK**")
    cols[2].markdown("**Marks**")
    cols[3].markdown("**Taxonomy**")
    
    # Defensive: ensure subparts length matches requested value
    if len(st.session_state.subparts) < st.session_state.Number_of_subparts:
        old_n = len(st.session_state.subparts)
        st.session_state.subparts += [default_subpart(i) for i in range(old_n, st.session_state.Number_of_subparts)]
    elif len(st.session_state.subparts) > st.session_state.Number_of_subparts:
        st.session_state.subparts = st.session_state.subparts[:st.session_state.Number_of_subparts]

    # Multi-Part mode: show all subparts with labels
    for i in range(st.session_state.Number_of_subparts):
        s = st.session_state.subparts[i]

        c0, c1, c2, c3 = st.columns((1, 1, 2, 3))
        c0.markdown(f"**({s['label']})**")

        dok_key = f"sub_{i}_dok"
        marks_key = f"sub_{i}_marks"
        tax_key = f"sub_{i}_tax"

        # initialize widget keys if absent so widget uses them as defaults
        if dok_key not in st.session_state:
            st.session_state[dok_key] = s["DOK"]
        if marks_key not in st.session_state:
            st.session_state[marks_key] = float(s["marks"])
        if tax_key not in st.session_state:
            st.session_state[tax_key] = s["taxonomy"]

        s_dok = c1.selectbox(f"DOK_{i}", options=[1, 2, 3], index=[1,2,3].index(st.session_state[dok_key]), key=dok_key, label_visibility="collapsed")
        s_marks = c2.number_input(f"marks_{i}", min_value=1.0, max_value=20.0, value=float(st.session_state[marks_key]), step=1.0, key=marks_key, label_visibility="collapsed")
        # All taxonomies are available for all DOK levels
        all_taxonomies = get_taxonomies_for_dok(s_dok)
        
        # All taxonomies are available for all DOK levels
        all_taxonomies = get_taxonomies_for_dok(s_dok)
        old_tax = st.session_state.get(tax_key, "Remembering")
        
        # Ensure old_tax is a valid single taxonomy
        if isinstance(old_tax, list):
            # Convert from old multiselect format
            old_tax = old_tax[0] if old_tax and old_tax[0] in all_taxonomies else "Remembering"
        elif old_tax not in all_taxonomies:
            old_tax = "Remembering"

        st.session_state[tax_key] = old_tax

        s_tax = c3.selectbox(
            f"tax_{i}",
            options=all_taxonomies,
            index=all_taxonomies.index(old_tax),
            key=tax_key,
            help="Select one taxonomy level (independent of DOK level)",
            label_visibility="collapsed"
        )

        # write back to session_state.subparts
        st.session_state.subparts[i] = {
            "label": chr(ord("a") + i),
            "DOK": int(s_dok),
            "marks": float(s_marks),
            "taxonomy": s_tax
        }
elif st.session_state.Question_Type == "MCQ":
    # MCQ mode: show configuration for each question
    st.subheader("MCQ Questions Configuration")
    
    # Ensure mcq_questions exists and has correct length
    if "mcq_questions" not in st.session_state:
        st.session_state.mcq_questions = [default_mcq_question(i) for i in range(st.session_state.Number_of_questions)]
    
    if len(st.session_state.mcq_questions) < st.session_state.Number_of_questions:
        old_n = len(st.session_state.mcq_questions)
        st.session_state.mcq_questions += [default_mcq_question(i) for i in range(old_n, st.session_state.Number_of_questions)]
    elif len(st.session_state.mcq_questions) > st.session_state.Number_of_questions:
        st.session_state.mcq_questions = st.session_state.mcq_questions[:st.session_state.Number_of_questions]
    
    # Header row
    cols = st.columns((1, 1, 2, 3))
    cols[0].markdown("**Question**")
    cols[1].markdown("**DOK**")
    cols[2].markdown("**Marks**")
    cols[3].markdown("**Taxonomy**")
    
    # Configuration row for each MCQ question
    for i in range(st.session_state.Number_of_questions):
        q = st.session_state.mcq_questions[i]

        c0, c1, c2, c3 = st.columns((1, 1, 2, 3))
        c0.markdown(f"**Q{i+1}**")

        dok_key = f"mcq_{i}_dok"
        marks_key = f"mcq_{i}_marks"
        tax_key = f"mcq_{i}_tax"

        # initialize widget keys if absent
        if dok_key not in st.session_state:
            st.session_state[dok_key] = q["DOK"]
        if marks_key not in st.session_state:
            st.session_state[marks_key] = float(q["marks"])
        if tax_key not in st.session_state:
            st.session_state[tax_key] = q["taxonomy"]

        q_dok = c1.selectbox(f"DOK_mcq_{i}", options=[1, 2, 3], index=[1,2,3].index(st.session_state[dok_key]), key=dok_key, label_visibility="collapsed")
        q_marks = c2.number_input(f"marks_mcq_{i}", min_value=1.0, max_value=20.0, value=float(st.session_state[marks_key]), step=1.0, key=marks_key, label_visibility="collapsed")
        
        # All taxonomies are available for all DOK levels
        all_taxonomies = get_taxonomies_for_dok(q_dok)
        old_tax = st.session_state.get(tax_key, "Remembering")
        
        # Ensure old_tax is a valid single taxonomy
        if isinstance(old_tax, list):
            # Convert from old multiselect format
            old_tax = old_tax[0] if old_tax and old_tax[0] in all_taxonomies else "Remembering"
        elif old_tax not in all_taxonomies:
            old_tax = "Remembering"

        st.session_state[tax_key] = old_tax

        q_tax = c3.selectbox(
            f"tax_mcq_{i}",
            options=all_taxonomies,
            index=all_taxonomies.index(old_tax),
            key=tax_key,
            help="Select one taxonomy level (independent of DOK level)",
            label_visibility="collapsed"
        )

        # write back to session_state.mcq_questions
        st.session_state.mcq_questions[i] = {
            "DOK": int(q_dok),
            "marks": float(q_marks),
            "taxonomy": q_tax
        }
else:  # Fill in the Blanks
    # FIB mode: show configuration for each question
    st.subheader("Fill in the Blanks Questions Configuration")
    
    # Ensure fib_questions exists and has correct length
    if "fib_questions" not in st.session_state:
        st.session_state.fib_questions = [default_fib_question(i) for i in range(st.session_state.Number_of_questions)]
    
    if len(st.session_state.fib_questions) < st.session_state.Number_of_questions:
        old_n = len(st.session_state.fib_questions)
        st.session_state.fib_questions += [default_fib_question(i) for i in range(old_n, st.session_state.Number_of_questions)]
    elif len(st.session_state.fib_questions) > st.session_state.Number_of_questions:
        st.session_state.fib_questions = st.session_state.fib_questions[:st.session_state.Number_of_questions]
    
    # Header row
    cols = st.columns((1, 1, 2, 3))
    cols[0].markdown("**Question**")
    cols[1].markdown("**DOK**")
    cols[2].markdown("**Marks**")
    cols[3].markdown("**Taxonomy**")
    
    # Configuration row for each FIB question
    for i in range(st.session_state.Number_of_questions):
        q = st.session_state.fib_questions[i]

        c0, c1, c2, c3 = st.columns((1, 1, 2, 3))
        c0.markdown(f"**Q{i+1}**")

        dok_key = f"fib_{i}_dok"
        marks_key = f"fib_{i}_marks"
        tax_key = f"fib_{i}_tax"

        # initialize widget keys if absent
        if dok_key not in st.session_state:
            st.session_state[dok_key] = q["DOK"]
        if marks_key not in st.session_state:
            st.session_state[marks_key] = float(q["marks"])
        if tax_key not in st.session_state:
            st.session_state[tax_key] = q["taxonomy"]

        q_dok = c1.selectbox(f"DOK_fib_{i}", options=[1, 2, 3], index=[1,2,3].index(st.session_state[dok_key]), key=dok_key, label_visibility="collapsed")
        q_marks = c2.number_input(f"marks_fib_{i}", min_value=1.0, max_value=20.0, value=float(st.session_state[marks_key]), step=1.0, key=marks_key, label_visibility="collapsed")
        
        # All taxonomies are available for all DOK levels
        all_taxonomies = get_taxonomies_for_dok(q_dok)
        old_tax = st.session_state.get(tax_key, "Remembering")
        
        # Ensure old_tax is a valid single taxonomy
        if isinstance(old_tax, list):
            # Convert from old multiselect format
            old_tax = old_tax[0] if old_tax and old_tax[0] in all_taxonomies else "Remembering"
        elif old_tax not in all_taxonomies:
            old_tax = "Remembering"

        st.session_state[tax_key] = old_tax

        q_tax = c3.selectbox(
            f"tax_fib_{i}",
            options=all_taxonomies,
            index=all_taxonomies.index(old_tax),
            key=tax_key,
            help="Select one taxonomy level (independent of DOK level)",
            label_visibility="collapsed"
        )

        # write back to session_state.fib_questions
        st.session_state.fib_questions[i] = {
            "DOK": int(q_dok),
            "marks": float(q_marks),
            "taxonomy": q_tax
        }

st.markdown("---")

# ---- Gemini API key and Generate button ----
st.subheader("🔑 API Key")
api_key = st.text_input("Enter your API Key (won't be sent until you click Generate)", type="password", key="gemini_api_key")

if st.button("🚀 Generate questions", use_container_width=True):
    if not api_key:
        st.error("Please enter your API key.")
        st.stop()
    
    # Check for PDF mode requirements
    if st.session_state.Input_Mode == "PDF Upload":
        if "pdf_file" not in st.session_state or st.session_state.pdf_file is None:
            st.error("Please upload a PDF file.")
            st.stop()

    # Build the state snapshot at the moment of generation
    state = {
        "Grade": st.session_state.Grade,
        "Curriculum": st.session_state.Curriculum,
        "Subject": st.session_state.Subject,
        "Chapter": st.session_state.Chapter,
        "Topic": st.session_state.Topic,
        "New_Concept": st.session_state.New_Concept if st.session_state.Input_Mode == "Manual" else "",
        "Old_Concept": st.session_state.Old_Concept,
        "Additional_Notes": st.session_state.get("Additional_Notes", ""),
        "Number_of_questions": int(st.session_state.Number_of_questions),
        "Question_Type": st.session_state.Question_Type,
        "Input_Mode": st.session_state.Input_Mode
    }
    
    # Add type-specific configuration
    if st.session_state.Question_Type == "Multi-Part":
        state["Number_of_subparts"] = int(st.session_state.Number_of_subparts)
        state["subparts"] = st.session_state.subparts.copy()
    elif st.session_state.Question_Type == "MCQ":
        state["mcq_questions"] = st.session_state.mcq_questions.copy()
    else:  # Fill in the Blanks
        state["fib_questions"] = st.session_state.fib_questions.copy()

    if st.session_state.Input_Mode == "Manual":
        # Manual mode: use text-based prompt
        prompt = assemble_prompt(state)
        with st.spinner("Generating questions..."):
            output = generate_questions_with_gemini(prompt, api_key)
    else:
        # PDF mode: use PDF with modified prompt
        prompt = assemble_prompt(state)
        pdf_bytes = st.session_state.pdf_file.read()
        with st.spinner("Generating questions from PDF..."):
            output = generate_questions_with_pdf(prompt, pdf_bytes, api_key)

    st.success("Done!")
    st.markdown(output)

st.caption("Please wait for the questions to be generated. This may take a few minutes....")