# # # multi_part_maths_streamlit_app.py
# # # Streamlit app to assemble and validate the 'multi_part_maths' prompt described by the user.
# # # Save and run with: streamlit run multi_part_maths_streamlit_app.py

# # import streamlit as st
# # import textwrap
# # import yaml
# # from typing import List
# # from google import genai
# # from google.genai import types

# # st.set_page_config(page_title="Multi-Part Maths Prompt Builder", layout="wide")

# # # DOK to Taxonomy Mapping
# # DOK_TAXONOMY_MAP = {
# #     1: {
# #         "name": "Knowing",
# #         "skills": "Recall, Identify, Order, Compute",
# #         "taxonomies": ["Recall", "Identify", "Order", "Compute"]
# #     },
# #     2: {
# #         "name": "Applying",
# #         "skills": "Formulating, Implementing, Representing",
# #         "taxonomies": ["Formulating", "Implementing", "Representing"]
# #     },
# #     3: {
# #         "name": "Reasoning",
# #         "skills": "Analyzing, Justifying, Integrating",
# #         "taxonomies": ["Analyzing", "Justifying", "Integrating"]
# #     }
# # }

# # def get_taxonomies_for_dok(dok_level: int) -> list:
# #     """Get allowed taxonomies for a given DOK level."""
# #     return DOK_TAXONOMY_MAP.get(dok_level, {}).get("taxonomies", [])

# # # --- Helper functions -----------------------------------------------------

# # def default_subpart(index: int):
# #     return {
# #         "label": chr(ord("a") + index),
# #         "DOK": 1,
# #         "marks": 1,
# #         "taxonomy": ["Recall"],  # Default to first DOK 1 skill
# #         "subtopic_hint": ""
# #     }


# # def validate_inputs(state):
# #     issues = []
# #     # Basic checks
# #     if not state["Topic"].strip():
# #         issues.append("Topic is empty — Topic is required by the Topic-Only Rule.")
# #     if state["Number_of_subparts"] < 1:
# #         issues.append("Number of subparts must be at least 1.")
# #     # Heuristic: if Topic is very short and many subparts, warn
# #     topic_words = len(state["Topic"].split())
# #     if topic_words <= 2 and state["Number_of_subparts"] > 4:
# #         issues.append("Topic looks narrow; having more than 4 subparts may make variation impossible.")
# #     # DOK 3 checks
# #     dok3_count = sum(1 for s in state["subparts"] if s["DOK"] == 3)
# #     if dok3_count > 1:
# #         issues.append("More than one DOK 3 subpart detected. DOK 3 is complex — consider limiting to 1.")
# #     # Variation / taxonomy sanity
# #     all_tax = set()
# #     for s in state["subparts"]:
# #         if not s["taxonomy"]:
# #             issues.append(f"Subpart {s['label']}: no taxonomy selected.")
# #         for t in s["taxonomy"]:
# #             all_tax.add(t)
# #     if len(all_tax) == 0:
# #         issues.append("No taxonomy labels selected across subparts — at least one required.")
# #     # Marks feasibility
# #     if any(s["marks"] <= 0 for s in state["subparts"]):
# #         issues.append("All subpart marks must be positive numbers.")

# #     return issues


# # def assemble_prompt(state) -> str:
# #     """
# #     Load prompt.yaml and replace placeholders with user values.
# #     """
# #     # Load the base prompt from prompt.yaml
# #     try:
# #         with open('prompt.yaml', 'r', encoding='utf-8') as f:
# #             prompt_template = f.read()
# #     except FileNotFoundError:
# #         return "Error: prompt.yaml file not found!"
    
# #     # Build the input details section
# #     num_questions = state.get('Number_of_questions', 1)
# #     num_subparts = state['Number_of_subparts']
    
# #     input_details = f"""    - Grade: {state['Grade']}
# #     - Curriculum: {state['Curriculum']}
# #     - Subject: {state['Subject']}
# #     - Chapter/Unit: {state['Chapter']}
# #     - Topic: {state['Topic']}
# #     - Concepts in Chapter: {state['Concepts']}
# #     - Number of Sub-Parts: {num_subparts}"""
    
# #     # Build subpart specifications (compact format)
# #     subpart_specs = f"\n    Number of Sub-Parts: {num_subparts}\n\n    Sub-Part Specifications:\n"
# #     for i in range(num_subparts):
# #         s = state["subparts"][i]
# #         dok_info = DOK_TAXONOMY_MAP.get(s['DOK'], {})
# #         dok_name = dok_info.get('name', '')
# #         tax = ", ".join(s["taxonomy"]) if s["taxonomy"] else ""
# #         subtopic = f", Subtopic: {s['subtopic_hint']}" if s.get('subtopic_hint') else ""
# #         subpart_specs += f"      {s['label']} → DOK {s['DOK']} ({dok_name}), Marks: {s['marks']}, Skills: {tax}{subtopic}\n"
    
# #     # Add note about DOK-skill selection
# #     subpart_specs += "    - From the provided input, each sub-part must use the DOK level given for that sub-part, and you may freely select any taxonomy label from the input list for that specific DOK level.\n"
    
# #     # Replace placeholders in the template
# #     prompt_text = prompt_template.replace('{{Number_of_questions}}', str(num_questions))
# #     prompt_text = prompt_text.replace('{{Grade}}', state['Grade'])
# #     prompt_text = prompt_text.replace('{{Curriculam}}', state['Curriculum'])
# #     prompt_text = prompt_text.replace('{{Subject}}', state['Subject'])
# #     prompt_text = prompt_text.replace('{{Chapter}}', state['Chapter'])
# #     prompt_text = prompt_text.replace('{{Topic}}', state['Topic'])
# #     prompt_text = prompt_text.replace('{{Concepts}}', state['Concepts'])
# #     prompt_text = prompt_text.replace('{{Number_of_subparts}}', str(num_subparts))
    
# #     # Replace the entire "For each sub-part" section with our compact format
# #     # Find and replace the section between "- Number of Sub-Parts:" and the next "===" line
# #     import re
# #     pattern = r'(- Number of Sub-Parts:.*?)(For each sub-part.*?)(- From the provided input.*?\n)'
# #     replacement = f"- Number of Sub-Parts: {num_subparts}\n\n{subpart_specs}"
# #     prompt_text = re.sub(pattern, replacement, prompt_text, flags=re.DOTALL)
    
# #     return prompt_text


# # def generate_questions_with_gemini(prompt: str, api_key: str = None) -> str:
# #     """
# #     Send the assembled prompt to Gemini 2.5 Pro with thinking budget of 5000.
# #     Returns the generated question text.
# #     """
# #     try:
# #         # Initialize Gemini client
# #         if api_key:
# #             client = genai.Client(api_key=api_key)
# #         else:
# #             client = genai.Client()
        
# #         # Generate content with Gemini 2.5 Pro and thinking budget
# #         response = client.models.generate_content(
# #             model="gemini-2.5-pro",
# #             contents=prompt,
# #             config=types.GenerateContentConfig(
# #                 thinking_config=types.ThinkingConfig(thinking_budget=5000)
# #             ),
# #         )
        
# #         return response.text
# #     except Exception as e:
# #         return f"Error generating questions: {str(e)}"


# # # Load base prompt from prompt.yaml if present
# # try:
# #     with open('prompt.yaml','r',encoding='utf-8') as f:
# #         BASE_PROMPT = f.read()
# # except FileNotFoundError:
# #     BASE_PROMPT = ""

# # # --- UI ------------------------------------------------------------------

# # st.title("Multi-Part Maths — Prompt Builder & Validator")
# # st.markdown("Use this app to assemble the `multi_part_maths` prompt and run quick validations before sending it to a model.")

# # with st.form(key="main_inputs"):
# #     st.header("Prompt Inputs")
# #     Grade = st.selectbox("Grade", options=[f"Grade {i}" for i in range(1,13)], index=3)
# #     Curriculum = st.text_input("Curriculum", value="CBSE")
# #     Subject = st.selectbox("Subject", options=["Mathematics", "Integrated Math"], index=0)
# #     Chapter = st.text_input("Chapter/Unit", value="")
# #     Topic = st.text_input("Topic", value="Fractions")
# #     Concepts = st.text_area("Concepts in Chapter (comma-separated)", value="Fraction addition, Fraction subtraction")
# #     Number_of_questions = st.number_input("Number of Questions to Generate", min_value=1, max_value=10, value=1, step=1, help="How many multi-part questions to generate")
# #     Number_of_subparts = st.number_input("Number of Sub-Parts per Question", min_value=1, max_value=8, value=3, step=1)
# #     submitted = st.form_submit_button("Set Inputs")

# # # Manage dynamic subpart state
# # if "subparts" not in st.session_state:
# #     st.session_state.subparts = [default_subpart(i) for i in range(6)]

# # if submitted:
# #     # Initialize only required number of subparts
# #     n = int(Number_of_subparts)
# #     st.session_state.subparts = [default_subpart(i) for i in range(n)]
# #     # store basic fields
# #     st.session_state.Grade = Grade
# #     st.session_state.Curriculum = Curriculum
# #     st.session_state.Subject = Subject
# #     st.session_state.Chapter = Chapter
# #     st.session_state.Topic = Topic
# #     st.session_state.Concepts = Concepts
# #     st.session_state.Number_of_questions = int(Number_of_questions)
# #     st.session_state.Number_of_subparts = n
# #     st.success("Inputs recorded. Now edit each subpart below and run validations.")

# # # If session not set yet, set some defaults
# # if "Grade" not in st.session_state:
# #     st.session_state.Grade = Grade
# #     st.session_state.Curriculum = Curriculum
# #     st.session_state.Subject = Subject
# #     st.session_state.Chapter = Chapter
# #     st.session_state.Topic = Topic
# #     st.session_state.Concepts = Concepts
# #     st.session_state.Number_of_questions = int(Number_of_questions)  # Use form value, not hardcoded 1
# #     st.session_state.Number_of_subparts = int(Number_of_subparts)

# # # Show current configuration
# # st.info(f"📊 **Current Configuration:** {st.session_state.get('Number_of_questions', 1)} question(s), {st.session_state.get('Number_of_subparts', 3)} subpart(s) per question | *Click 'Set Inputs' above to update*")

# # # Subparts editor
# # st.subheader("Subparts Configuration")
# # st.markdown("*Taxonomy options are filtered based on DOK level selection*")
# # cols = st.columns((1, 1, 2, 3))
# # cols[0].markdown("**Part**")
# # cols[1].markdown("**DOK**")
# # cols[2].markdown("**Marks**")
# # cols[3].markdown("**Taxonomy + Subtopic hint (optional)**")

# # for i in range(st.session_state.Number_of_subparts):
# #     s = st.session_state.subparts[i]
# #     c0, c1, c2, c3 = st.columns((1,1,2,3))
# #     c0.markdown(f"**({s['label']})**")
    
# #     # DOK selection with skill area info
# #     dok_info = DOK_TAXONOMY_MAP.get(s['DOK'], {})
# #     dok_label = f"DOK {s['DOK']} - {dok_info.get('name', '')}"
# #     s['DOK'] = c1.selectbox(
# #         f"DOK_{i}", 
# #         options=[1,2,3], 
# #         index=s['DOK']-1, 
# #         key=f"dok_{i}",
# #         help=f"Skills: {dok_info.get('skills', '')}"
# #     )
    
# #     # Marks input
# #     s['marks'] = c2.number_input(
# #         f"marks_{i}", 
# #         min_value=1.0, 
# #         max_value=20.0, 
# #         value=float(s['marks']), 
# #         step=1.0, 
# #         key=f"marks_{i}"
# #     )
    
# #     # Dynamic taxonomy based on DOK level
# #     allowed_taxonomies = get_taxonomies_for_dok(s['DOK'])
    
# #     # Filter existing taxonomy to only include allowed ones
# #     current_taxonomy = [t for t in s['taxonomy'] if t in allowed_taxonomies]
# #     if not current_taxonomy and allowed_taxonomies:
# #         current_taxonomy = [allowed_taxonomies[0]]  # Default to first allowed
    
# #     taxonomy = c3.multiselect(
# #         f"tax_{i}", 
# #         options=allowed_taxonomies, 
# #         default=current_taxonomy, 
# #         key=f"tax_{i}",
# #         help=f"DOK {s['DOK']} allows: {', '.join(allowed_taxonomies)}"
# #     )
# #     s['taxonomy'] = taxonomy
    
# #     # Subtopic hint
# #     subtopic_hint = c3.text_input(
# #         f"subtopic_hint_{i}", 
# #         value=s.get('subtopic_hint',''), 
# #         placeholder='Optional short subtopic used by this subpart', 
# #         key=f"subtopic_{i}"
# #     )
# #     s['subtopic_hint'] = subtopic_hint
# #     st.session_state.subparts[i] = s

# # # Action buttons
# # col1, col2, col3 = st.columns(3)
# # with col1:
# #     if st.button("Validate Prompt"):
# #         # collect state
# #         state = {
# #             "Grade": st.session_state.Grade,
# #             "Curriculum": st.session_state.Curriculum,
# #             "Subject": st.session_state.Subject,
# #             "Chapter": st.session_state.Chapter,
# #             "Topic": st.session_state.Topic,
# #             "Concepts": st.session_state.Concepts,
# #             "Number_of_questions": st.session_state.get("Number_of_questions", 1),
# #             "Number_of_subparts": st.session_state.Number_of_subparts,
# #             "subparts": st.session_state.subparts
# #         }
# #         issues = validate_inputs(state)
# #         if issues:
# #             st.error("Validation found issues. Review the list below:")
# #             for it in issues:
# #                 st.warning(it)
# #         else:
# #             st.success("No obvious issues found. Prompt looks consistent with the rules.")

# # with col2:
# #     if st.button("Assemble Prompt"):
# #         state = {
# #             "Grade": st.session_state.Grade,
# #             "Curriculum": st.session_state.Curriculum,
# #             "Subject": st.session_state.Subject,
# #             "Chapter": st.session_state.Chapter,
# #             "Topic": st.session_state.Topic,
# #             "Concepts": st.session_state.Concepts,
# #             "Number_of_questions": st.session_state.get("Number_of_questions", 1),
# #             "Number_of_subparts": st.session_state.Number_of_subparts,
# #             "subparts": st.session_state.subparts
# #         }
# #         prompt_out = assemble_prompt(state)
# #         st.code(prompt_out, language="yaml")
# #         st.markdown("**Tip:** Copy this prompt and use it as the system or instruction prompt for your question-generation model.\nYou can edit fields and re-assemble.")

# # with col3:
# #     if st.button("Export as .txt"):
# #         state = {
# #             "Grade": st.session_state.Grade,
# #             "Curriculum": st.session_state.Curriculum,
# #             "Subject": st.session_state.Subject,
# #             "Chapter": st.session_state.Chapter,
# #             "Topic": st.session_state.Topic,
# #             "Concepts": st.session_state.Concepts,
# #             "Number_of_questions": st.session_state.get("Number_of_questions", 1),
# #             "Number_of_subparts": st.session_state.Number_of_subparts,
# #             "subparts": st.session_state.subparts
# #         }
# #         prompt_out = assemble_prompt(state)
# #         filename = "multi_part_maths_prompt.txt"
# #         with open(filename, "w", encoding="utf-8") as f:
# #             f.write(prompt_out)
# #         st.success(f"Saved prompt to {filename}")
# #         st.markdown(f"[Download the prompt file]({filename})")

# # # API Key Input Section
# # st.markdown("---")
# # st.subheader("🔑 Gemini API Configuration")
# # api_key_input = st.text_input(
# #     "Enter your Gemini API Key", 
# #     type="password", 
# #     key="gemini_api_key",
# #     help="Get your API key from: https://aistudio.google.com/app/apikey"
# # )

# # # Generate Button
# # if st.button("🚀 Generate with Gemini 2.5 Pro", type="primary", use_container_width=True):
# #     if not api_key_input:
# #         st.error("⚠️ Please enter your Gemini API key above to generate questions.")
# #         st.stop()
    
# #     state = {
# #         "Grade": st.session_state.Grade,
# #         "Curriculum": st.session_state.Curriculum,
# #         "Subject": st.session_state.Subject,
# #         "Chapter": st.session_state.Chapter,
# #         "Topic": st.session_state.Topic,
# #         "Concepts": st.session_state.Concepts,
# #         "Number_of_questions": st.session_state.get("Number_of_questions", 1),
# #         "Number_of_subparts": st.session_state.Number_of_subparts,
# #         "subparts": st.session_state.subparts
# #     }
    
# #     # Assemble the prompt
# #     prompt_out = assemble_prompt(state)
    
# #     # Show the final prompt being sent to the model
# #     st.markdown("---")
# #     st.markdown("### 📋 Final Prompt Sent to Gemini 2.5 Pro")
# #     with st.expander("Click to view the complete prompt", expanded=False):
# #         st.code(prompt_out, language="yaml")
    
# #     # Generate with Gemini
# #     with st.spinner("🤖 Generating questions with Gemini 2.5 Pro (Thinking Budget: 5000)..."):
# #         result = generate_questions_with_gemini(prompt_out, api_key_input)
    
# #     st.success("✅ Questions generated successfully!")
# #     st.markdown("---")
# #     st.markdown("### 📝 Generated Multi-Part Question:")
# #     st.markdown(result)
    
# #     # Store in session state for later reference
# #     st.session_state.last_generated = result

# # # Help / Notes
# # st.markdown("---")
# # st.markdown("**Validation heuristics used:**\n- Topic non-empty\n- Number of subparts reasonable for narrow topics\n- Max one DOK 3 recommended\n- All subparts must have taxonomy labels\n- Marks must be positive numbers")

# # st.markdown("---")
# # st.markdown("Developed to follow the user's strict 'multi_part_maths' prompt. This tool assembles the prompt and runs lightweight consistency checks; it does NOT generate the questions themselves.")

# # # Footer
# # st.caption("Need changes? Edit the app or ask to include extra constraints like maximum subparts per topic or automatic subtopic extraction.")

# import streamlit as st
# import yaml
# import re
# from google import genai
# from google.genai import types

# st.set_page_config(page_title="Multi-Part Maths Prompt Builder", layout="wide")

# # ------------------ DOK Mapping ------------------
# DOK_TAXONOMY_MAP = {
#     1: {"name": "Knowing", "skills": "Recall, Identify, Order, Compute",
#         "taxonomies": ["Recall", "Identify", "Order", "Compute"]},
#     2: {"name": "Applying", "skills": "Formulating, Implementing, Representing",
#         "taxonomies": ["Formulating", "Implementing", "Representing"]},
#     3: {"name": "Reasoning", "skills": "Analyzing, Justifying, Integrating",
#         "taxonomies": ["Analyzing", "Justifying", "Integrating"]},
# }

# def get_taxonomies_for_dok(dok_level):
#     return DOK_TAXONOMY_MAP.get(dok_level, {}).get("taxonomies", [])


# # ------------------ YAML SAFE QUOTING ------------------
# def yq(val):
#     if val is None:
#         return "\"\""
#     return f"\"{val}\""


# # ------------------ DEFAULT SUBPART ------------------
# def default_subpart(index):
#     return {
#         "label": chr(ord("a") + index),
#         "DOK": 1,
#         "marks": 1,
#         "taxonomy": ["Recall"]
#     }


# # ------------------ INITIALIZE SESSION STATE ONCE ------------------
# if "initialized" not in st.session_state:
#     st.session_state.initialized = True

#     st.session_state.Number_of_subparts = 3
#     st.session_state.Number_of_questions = 1

#     st.session_state.Grade = "Grade 4"
#     st.session_state.Curriculum = "CBSE"
#     st.session_state.Subject = "Mathematics"
#     st.session_state.Chapter = ""
#     st.session_state.Topic = "Fractions"
#     st.session_state.Concepts = "Fraction addition, Fraction subtraction"

#     st.session_state.subparts = [default_subpart(i) for i in range(3)]


# # ------------------ ASSEMBLE PROMPT ------------------
# def assemble_prompt(state):
#     try:
#         with open("prompt.yaml", "r", encoding="utf-8") as f:
#             prompt_template = f.read()
#     except FileNotFoundError:
#         return "Error: prompt.yaml file missing!"

#     num_sub = state["Number_of_subparts"]

#     # Replace placeholders with YAML-safe versions
#     prompt_text = prompt_template.replace('{{Grade}}', yq(state["Grade"]))
#     prompt_text = prompt_text.replace('{{Curriculam}}', yq(state["Curriculum"]))
#     prompt_text = prompt_text.replace('{{Subject}}', yq(state["Subject"]))
#     prompt_text = prompt_text.replace('{{Chapter}}', yq(state["Chapter"]))
#     prompt_text = prompt_text.replace('{{Topic}}', yq(state["Topic"]))
#     prompt_text = prompt_text.replace('{{Concepts}}', yq(state["Concepts"]))
#     prompt_text = prompt_text.replace('{{Number_of_subparts}}', yq(str(num_sub)))
#     prompt_text = prompt_text.replace('{{Number_of_questions}}', yq(str(state["Number_of_questions"])))

#     # Build subpart spec block (no subtopic hint)
#     subpart_specs = ""
#     for s in state["subparts"]:
#         dok_info = DOK_TAXONOMY_MAP.get(s["DOK"], {})
#         dok_name = dok_info.get("name", "")
#         taxonomy_list = ", ".join(s["taxonomy"]) if s["taxonomy"] else ""

#         subpart_specs += (
#             f"      {s['label']} → DOK {s['DOK']} ({dok_name}), "
#             f"Marks: {s['marks']}, Skills: {taxonomy_list}\n"
#         )

#     # Replace block using your existing regex logic
#     pattern = r'(- Number of Sub-Parts:.*?)(For each sub-part.*?)(- From the provided input.*?\n)'
#     replacement = f"- Number of Sub-Parts: {num_sub}\n\n{subpart_specs}"
#     prompt_text = re.sub(pattern, replacement, prompt_text, flags=re.DOTALL)

#     return prompt_text


# # ------------------ GEMINI CALL ------------------
# def generate_questions_with_gemini(prompt, api_key):
#     try:
#         client = genai.Client(api_key=api_key)

#         response = client.models.generate_content(
#             model="gemini-2.5-pro",
#             contents=prompt,
#             config=types.GenerateContentConfig(
#                 thinking_config=types.ThinkingConfig(thinking_budget=5000)
#             )
#         )
#         return response.text
#     except Exception as e:
#         return f"Error: {e}"


# # ==========================================================
# # ----------------------   UI   ----------------------------
# # ==========================================================

# st.title("Multi-Part Maths — Prompt Builder")


# # ------------------- INPUT FORM -------------------
# with st.form("main_inputs"):
#     st.header("Prompt Inputs")

#     Grade = st.selectbox("Grade", options=[f"Grade {i}" for i in range(1, 13)],
#                          index=[f"Grade {i}" for i in range(1, 13)].index(st.session_state.Grade))

#     Curriculum = st.text_input("Curriculum", value=st.session_state.Curriculum)
#     Subject = st.selectbox("Subject", ["Mathematics", "Integrated Math"],
#                            index=["Mathematics", "Integrated Math"].index(st.session_state.Subject))
#     Chapter = st.text_input("Chapter/Unit", value=st.session_state.Chapter)
#     Topic = st.text_input("Topic", value=st.session_state.Topic)
#     Concepts = st.text_area("Concepts in Chapter", value=st.session_state.Concepts)

#     Number_of_questions = st.number_input(
#         "Number of Questions",
#         min_value=1, max_value=10,
#         value=st.session_state.Number_of_questions,
#         step=1
#     )

#     Number_of_subparts = st.number_input(
#         "Number of Sub-Parts per Question",
#         min_value=1, max_value=8,
#         value=st.session_state.Number_of_subparts,
#         step=1
#     )

#     submitted = st.form_submit_button("Set Inputs")

# # When user sets inputs
# if submitted:
#     st.session_state.Grade = Grade
#     st.session_state.Curriculum = Curriculum
#     st.session_state.Subject = Subject
#     st.session_state.Chapter = Chapter
#     st.session_state.Topic = Topic
#     st.session_state.Concepts = Concepts
#     st.session_state.Number_of_questions = int(Number_of_questions)

#     new_n = int(Number_of_subparts)
#     old_n = len(st.session_state.subparts)

#     if new_n > old_n:
#         st.session_state.subparts += [default_subpart(i) for i in range(old_n, new_n)]
#     elif new_n < old_n:
#         st.session_state.subparts = st.session_state.subparts[:new_n]

#     st.session_state.Number_of_subparts = new_n

#     st.success("Inputs updated!")


# # ------------------- SUBPART EDITOR -------------------
# st.subheader("Subparts Configuration")
# cols = st.columns((1, 1, 2, 3))

# cols[0].markdown("**Part**")
# cols[1].markdown("**DOK**")
# cols[2].markdown("**Marks**")
# cols[3].markdown("**Taxonomy**")

# for i in range(st.session_state.Number_of_subparts):
#     s = st.session_state.subparts[i]

#     c0, c1, c2, c3 = st.columns((1, 1, 2, 3))

#     c0.markdown(f"**({s['label']})**")

#     s["DOK"] = c1.selectbox(
#         f"DOK_{i}", [1, 2, 3],
#         index=s["DOK"] - 1,
#         key=f"dok_{i}"
#     )

#     s["marks"] = c2.number_input(
#         f"marks_{i}",
#         min_value=1.0, max_value=20.0,
#         value=float(s["marks"]),
#         step=1.0,
#         key=f"marks_{i}"
#     )

#     allowed = get_taxonomies_for_dok(s["DOK"])
#     current = [t for t in s["taxonomy"] if t in allowed] or [allowed[0]]

#     s["taxonomy"] = c3.multiselect(
#         f"tax_{i}",
#         options=allowed,
#         default=current,
#         key=f"tax_{i}"
#     )

#     st.session_state.subparts[i] = s


# # ------------------- GENERATE BUTTON -------------------
# st.markdown("---")
# st.subheader("🔑 Gemini API Key")
# api_key = st.text_input("Enter your API Key", type="password")

# if st.button("🚀 Generate with Gemini 2.5 Pro", use_container_width=True):
#     if not api_key:
#         st.error("Enter API Key")
#         st.stop()

#     state = {
#         "Grade": st.session_state.Grade,
#         "Curriculum": st.session_state.Curriculum,
#         "Subject": st.session_state.Subject,
#         "Chapter": st.session_state.Chapter,
#         "Topic": st.session_state.Topic,
#         "Concepts": st.session_state.Concepts,
#         "Number_of_questions": st.session_state.Number_of_questions,
#         "Number_of_subparts": st.session_state.Number_of_subparts,
#         "subparts": st.session_state.subparts,
#     }

#     prompt = assemble_prompt(state)

#     with st.spinner("Generating…"):
#         output = generate_questions_with_gemini(prompt, api_key)

#     st.success("Done!")
#     st.markdown(output)


# st.caption("All prompt UI removed. YAML-safe quoting enabled. Subtopics removed.")

import streamlit as st
import re
from google import genai
from google.genai import types

st.set_page_config(page_title="Multi-Part Maths Prompt Builder", layout="wide")

# ------------------ DOK Mapping ------------------
DOK_TAXONOMY_MAP = {
    1: {"name": "Knowing", "skills": "Recall, Identify, Order, Compute",
        "taxonomies": ["Recall", "Identify", "Order", "Compute"]},
    2: {"name": "Applying", "skills": "Formulating, Implementing, Representing",
        "taxonomies": ["Formulating", "Implementing", "Representing"]},
    3: {"name": "Reasoning", "skills": "Analyzing, Justifying, Integrating",
        "taxonomies": ["Analyzing", "Justifying", "Integrating"]},
}

def get_taxonomies_for_dok(dok_level):
    return DOK_TAXONOMY_MAP.get(dok_level, {}).get("taxonomies", [])

# ------------------ YAML SAFE QUOTING ------------------
def yq(val):
    if val is None:
        return "\"\""
    safe = str(val).replace('"', '\\"')
    return f"\"{safe}\""

# ------------------ DEFAULT SUBPART ------------------
def default_subpart(index):
    return {
        "label": chr(ord("a") + index),
        "DOK": 1,
        "marks": 1,
        "taxonomy": ["Recall"]
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
    st.session_state.Concepts = "Fraction addition, Fraction subtraction"

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
    """
    try:
        with open("prompt.yaml", "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except FileNotFoundError:
        return "Error: prompt.yaml file not found!"

    num_sub = state["Number_of_subparts"]

    # Replace placeholders (YAML-safe quoting)
    prompt_text = prompt_template.replace('{{Grade}}', yq(state["Grade"]))
    prompt_text = prompt_text.replace('{{Curriculam}}', yq(state["Curriculum"]))
    prompt_text = prompt_text.replace('{{Subject}}', yq(state["Subject"]))
    prompt_text = prompt_text.replace('{{Chapter}}', yq(state["Chapter"]))
    prompt_text = prompt_text.replace('{{Topic}}', yq(state["Topic"]))
    prompt_text = prompt_text.replace('{{Concepts}}', yq(state["Concepts"]))
    prompt_text = prompt_text.replace('{{Number_of_subparts}}', yq(str(num_sub)))
    prompt_text = prompt_text.replace('{{Number_of_questions}}', yq(str(state["Number_of_questions"])))

    # Build subpart specs (no subtopic)
    subpart_specs = ""
    for s in state["subparts"]:
        dok_info = DOK_TAXONOMY_MAP.get(s["DOK"], {})
        dok_name = dok_info.get("name", "")
        taxonomy_list = ", ".join(s["taxonomy"]) if s["taxonomy"] else ""
        subpart_specs += (
            f"      {s['label']} → DOK {s['DOK']} ({dok_name}), "
            f"Marks: {s['marks']}, Skills: {taxonomy_list}\n"
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

# ------------------ UI ------------------
st.title("Multi-Part Maths Question Generator")

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
st.text_area("Concepts in Chapter ", value=st.session_state.Concepts, key="Concepts")

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
    allowed = get_taxonomies_for_dok(s_dok) or ["Recall"]
    # ensure current selection is allowed
    # Clean invalid taxonomy values BEFORE widget renders
    old_tax = st.session_state.get(tax_key, [])
    cleaned_tax = [t for t in old_tax if t in allowed]

    if not cleaned_tax:
        cleaned_tax = [allowed[0]]

    # Update session_state BEFORE rendering widget
    st.session_state[tax_key] = cleaned_tax

    s_tax = c3.multiselect(
        f"tax_{i}",
        options=allowed,
        default=cleaned_tax,
        key=tax_key
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
st.subheader("🔑 Gemini API Key")
api_key = st.text_input("Enter your Gemini API Key (won't be sent until you click Generate)", type="password", key="gemini_api_key")

if st.button("🚀 Generate questions", use_container_width=True):
    if not api_key:
        st.error("Please enter your Gemini API key.")
        st.stop()

    # Build the state snapshot at the moment of generation
    state = {
        "Grade": st.session_state.Grade,
        "Curriculum": st.session_state.Curriculum,
        "Subject": st.session_state.Subject,
        "Chapter": st.session_state.Chapter,
        "Topic": st.session_state.Topic,
        "Concepts": st.session_state.Concepts,
        "Number_of_questions": int(st.session_state.Number_of_questions),
        "Number_of_subparts": int(st.session_state.Number_of_subparts),
        "subparts": st.session_state.subparts.copy()
    }

    prompt = assemble_prompt(state)
    with st.spinner("Generating questions..."):
        output = generate_questions_with_gemini(prompt, api_key)

    st.success("Done!")
    st.markdown(output)

st.caption("Please wait for the questions to be generated. This may take a few minutes....")