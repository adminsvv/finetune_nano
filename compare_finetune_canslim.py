import streamlit as st
import pandas as pd
from openai import OpenAI

# Load API key and setup OpenAI client
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

# Load stock data
df_canslim = pd.read_csv('canslim_data_st.csv')
all_stocks = df_canslim['nsesymbol'].unique()

st.set_page_config(
    layout="wide",  # 👈 enables wide mode
    page_title="Finetuning test"

)



CREDENTIALS = {
    "finetune": "finetune_ib"

}



def login_block():
    """Returns True when user is authenticated."""
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if st.session_state["authenticated"]:
        return True

    # ── Login form ──
    st.title("🔐 Login required")
    with st.form("login_form", clear_on_submit=False):
        user = st.text_input("Username")
        pwd  = st.text_input("Password", type="password")
        submit = st.form_submit_button("Log in")

    if submit:
        if user in CREDENTIALS and pwd == CREDENTIALS[user]:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("❌ Incorrect username or password")
    return False
if not login_block():
    st.stop()



# Streamlit UI
st.title("CANSLIM Stock Analysis (Streaming Output)")
# selected_stock = st.selectbox("Select a Stock", options=all_stocks)
selected_stocks = st.multiselect("Select Stock(s)", options=all_stocks)
user_query = st.text_area("Enter your query", value="Analyze the company for me")
run_button = st.button("Run Analysis")

def get_text_data(selected_stock):
    # df_company = df_canslim[df_canslim['nsesymbol'] == selected_stock]
    df_company = df_canslim[df_canslim['nsesymbol'].isin(selected_stocks)]
    st.dataframe(df_company)
    return df_company.to_json(orient='records', lines=True)

system_content = (
    "You are an expert stock analyst. Always use CANSLIM principles as your analytical framework for all analysis. "
    "If the user's question is general or holistic, provide a comprehensive CANSLIM-style analysis by explicitly discussing each pillar (Current earnings, Annual earnings, New products/events, Supply & demand, Leadership, Institutional sponsorship, Market direction).Mention how and where it fits based on what the CANSLIM framework recommends "
    "In all such general analyses, always end with a clear investment verdict—Buy, Hold, Sell, or Avoid—along with a concise summary rationale for your recommendation. "
    "If the user's question is focused on a specific aspect (for example, earnings), analyze that aspect through the relevant CANSLIM pillars only (e.g., earnings should reference C and A), and base your response strictly on the provided data. "
    "Never provide information beyond the supplied data. Always align your response to the user's actual question, but connect your analysis to the appropriate CANSLIM pillar(s) where possible."
)

# --- Streaming functions for each model ---
def stream_openai_response(model, text_data, user_query, system_content=None):
    if model == "ft:gpt-4.1-nano-2025-04-14:personal:canslim-finetune-nano-ver2:BoBqF8KX":
        messages = [
            {"role": "system", "content": "You are an financial analyst."},
            {"role": "user", "content": f""""For the company {selected_stocks}. {user_query} based on   {text_data}
            
"""}
        ]
    elif model == "gpt-4.1-nano":
        messages = [
            {"role": "system", "content": "You are an financial analyst."},
            {"role": "user", "content": f""""For the company {selected_stocks}. {user_query} based on   {text_data}"""}
        ]
    elif model == "gpt-4.1":
        user_content = (
            f"You are given the financial data of a company: {selected_stocks}: {text_data}\n"
            f"""Based on it provide answer for the user query: {user_query}. Make sure the answer only uses the provided data.

            """
        )
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
    else:
        raise ValueError("Unknown model")
    
    response = client.responses.create(
        model=model,
        input=messages,
        stream=True
    )
    # Streaming: yield each text delta as it arrives
    for event in response:
        if hasattr(event, "delta"):
            yield event.delta

# --- Main UI/Logic ---
if run_button:
    text_data = get_text_data(selected_stocks)

    
    st.subheader("Base Model (Nano) Streaming Output")
    base_placeholder = st.empty()
    st.subheader("Finetuned Model (Nano) Streaming Output")
    finetune_placeholder = st.empty()
    st.subheader("Main Model (4.1) Streaming Output")
    model4_placeholder = st.empty()

    # For Streamlit, must run in sequence; for parallel output, you'd use threads or async.
    # Finetune model output
    
    # Base model output
    output_base = ""
    for delta in stream_openai_response(
        "gpt-4.1-nano",
        text_data, user_query):
        output_base += delta
        base_placeholder.markdown(output_base)
    
    output_finetune = ""
    for delta in stream_openai_response(
        "ft:gpt-4.1-nano-2025-04-14:personal:canslim-finetune-nano-ver2:BoBqF8KX",
        text_data, user_query):
        output_finetune += delta
        finetune_placeholder.markdown(output_finetune)


    # 4.1 model output
    output_model4 = ""
    for delta in stream_openai_response(
        "gpt-4.1",
        text_data, user_query, system_content):
        output_model4 += delta
        model4_placeholder.markdown(output_model4)
