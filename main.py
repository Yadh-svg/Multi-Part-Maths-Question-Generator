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
            "taxonomy": ["Remembering"]
        }
    elif index == 1:  # Part b
        return {
            "label": "b",
            "DOK": 2,
            "marks": 1,
            "taxonomy": ["Understanding"]
        }
    elif index == 2:  # Part c
        return {
            "label": "c",
            "DOK": 3,
            "marks": 2,
            "taxonomy": ["Analysing", "Evaluating"]
        }
    else:  # Additional parts default to DOK 1
        return {
            "label": chr(ord("a") + index),
            "DOK": 1,
            "marks": 1,
            "taxonomy": ["Remembering"]
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
    st.session_state.Input_Mode = "Manual"  # Default to Manual mode

    st.session_state.subparts = [default_subpart(i) for i in range(st.session_state.Number_of_subparts)]

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

# ------------------ ASSEMBLE PROMPT ------------------
def assemble_prompt(state):
    """
    Load prompt.yaml and replace placeholders with YAML-safe quotes.
    Uses your existing regex logic to inject subpart specs.
    For PDF mode, uses a modified prompt that references the PDF.
    """
    try:
        with open("prompt.yaml", "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return "Error: prompt.yaml file not found!"

    # Select the appropriate prompt template based on input mode
    if state.get("Input_Mode") == "PDF Upload":
        # Extract the PDF-specific prompt template
        if "multi_part_maths_pdf:" in content:
            prompt_template = content.split("multi_part_maths_pdf:")[1].strip()
            # Remove the leading '|' if present
            if prompt_template.startswith("|"):
                prompt_template = prompt_template[1:].strip()
        else:
            # Fallback to regular template if PDF template doesn't exist yet
            prompt_template = content.split("multi_part_maths:")[1].strip()
            if prompt_template.startswith("|"):
                prompt_template = prompt_template[1:].strip()
    else:
        # Extract the regular prompt template
        prompt_template = content.split("multi_part_maths:")[1].strip()
        if prompt_template.startswith("|"):
            prompt_template = prompt_template[1:].strip()
        # If there's a PDF template, remove it
        if "multi_part_maths_pdf:" in prompt_template:
            prompt_template = prompt_template.split("multi_part_maths_pdf:")[0].strip()

    num_sub = state["Number_of_subparts"]

    # Replace placeholders (YAML-safe quoting)
    prompt_text = prompt_template.replace('{{Grade}}', yq(state["Grade"]))
    prompt_text = prompt_text.replace('{{Curriculam}}', yq(state["Curriculum"]))
    prompt_text = prompt_text.replace('{{Subject}}', yq(state["Subject"]))
    prompt_text = prompt_text.replace('{{Chapter}}', yq(state["Chapter"]))
    prompt_text = prompt_text.replace('{{Topic}}', yq(state["Topic"]))
    prompt_text = prompt_text.replace('{{New_Concept}}', yq(state["New_Concept"]))
    prompt_text = prompt_text.replace('{{Old_Concept}}', yq(state["Old_Concept"]))
    prompt_text = prompt_text.replace('{{Number_of_subparts}}', yq(str(num_sub)))
    prompt_text = prompt_text.replace('{{Number_of_questions}}', yq(str(state["Number_of_questions"])))

    # Build subpart specs (no subtopic)
    subpart_specs = ""
    for s in state["subparts"]:
        taxonomy_list = ", ".join(s["taxonomy"]) if s["taxonomy"] else ""
        subpart_specs += (
            f"      {s['label']} → DOK {s['DOK']}, "
            f"Marks: {s['marks']}, Taxonomy: {taxonomy_list}\n"
        )

    # Inject using the existing regex (unchanged per your request)
    pattern = r'(- Number of Sub-Parts:.*?)(For each sub-part.*?)(- From the provided input.*?\n)'
    replacement = f"- Number of Sub-Parts: {num_sub}\n\n{subpart_specs}"
    prompt_text = re.sub(pattern, replacement, prompt_text, flags=re.DOTALL)

    return prompt_text

# ------------------ GEMINI CALL ------------------
def generate_questions_with_gemini(prompt, api_key):
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-pro",
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=5000)
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
                thinking_config=types.ThinkingConfig(thinking_budget=5000)
            )
        )
        return getattr(response, "text", str(response))
    except Exception as e:
        return f"Error generating questions with PDF: {e}"

# ------------------ UI ------------------
st.title("Multi-Part Maths Question Generator")

# ---- Input Mode Selection ----
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
else:
    # PDF mode: show PDF uploader and only Old Concept
    st.file_uploader("Upload PDF (New Concept)", type=["pdf"], key="pdf_file",
                    help="Upload a PDF file containing the new concepts for this chapter")
    st.text_area("Old Concept (prerequisite knowledge to check)", value=st.session_state.Old_Concept, key="Old_Concept",
                 help="Enter the concepts the student should already know from previous chapters")

# Number of Questions: editable, stored immediately (but prompt only built on Generate)
st.number_input("Number of Questions", min_value=1, max_value=10,
                value=st.session_state.Number_of_questions, step=1, key="Number_of_questions")

# Number of Subparts: triggers live update via on_change callback
st.number_input("Number of Sub-Parts per Question",
                min_value=1, max_value=26,
                value=st.session_state.Number_of_subparts,
                step=1,
                key="Number_of_subparts",
                on_change=update_subparts)

st.markdown("---")

# ---- Subparts editor (widgets are created per index and stored in subpart keys) ----
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

    s_dok = c1.selectbox(f"DOK_{i}", options=[1, 2, 3], index=[1,2,3].index(st.session_state[dok_key]), key=dok_key)
    s_marks = c2.number_input(f"marks_{i}", min_value=1.0, max_value=20.0, value=float(st.session_state[marks_key]), step=1.0, key=marks_key)
    # All taxonomies are available for all DOK levels
    all_taxonomies = get_taxonomies_for_dok(s_dok)
    
    # Get current taxonomy selection, ensure it's valid
    old_tax = st.session_state.get(tax_key, [])
    cleaned_tax = [t for t in old_tax if t in all_taxonomies]

    if not cleaned_tax:
        cleaned_tax = [all_taxonomies[0]]  # Default to "Remembering"

    # Update session_state BEFORE rendering widget
    st.session_state[tax_key] = cleaned_tax

    s_tax = c3.multiselect(
        f"tax_{i}",
        options=all_taxonomies,
        default=cleaned_tax,
        key=tax_key,
        help="Select one or more taxonomy levels (independent of DOK level)"
    )

    # write back to session_state.subparts
    st.session_state.subparts[i] = {
        "label": chr(ord("a") + i),
        "DOK": int(s_dok),
        "marks": float(s_marks),
        "taxonomy": s_tax
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
        "Number_of_questions": int(st.session_state.Number_of_questions),
        "Number_of_subparts": int(st.session_state.Number_of_subparts),
        "subparts": st.session_state.subparts.copy(),
        "Input_Mode": st.session_state.Input_Mode
    }

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