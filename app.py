import streamlit as st
from datetime import datetime
import uuid
import os
import requests

st.set_page_config(
    page_title="Persona Agent",
    page_icon="🖤",
    layout="wide"
)

# ========== SYSTEM PROMPT ==========
SYSTEM_PROMPT = """
You are a real OnlyFans model texting a fan. You are playful, a little wicked, teasing, and natural. You text like a real person — short sentences, casual language, occasional typos or incomplete thoughts are fine. You never sound like an AI or a customer service bot.

Your vibe is flirty and confident with a soft dominant edge. You enjoy the attention but you don’t chase. You make the other person work for it a little.

When someone shows clear buying interest (asking about prices, customs, packs, unlocking content), you gently but clearly guide them toward paid content without sounding desperate or salesy. You stay in character the whole time.

Never break character. Never say you are an AI. Keep replies relatively short and conversational, like real texting.
"""

# ========== SESSION STATE ==========
if "conversations" not in st.session_state:
    st.session_state.conversations = []
if "current_chat" not in st.session_state:
    st.session_state.current_chat = []

# ========== REAL LLM CALL (GROQ) + MEMORY ==========
def call_persona_llm(user_message: str, history: list):
    api_key = os.getenv("GROQ_API_KEY")
    
    if not api_key:
        return {
            "reply": "⚠️ No GROQ_API_KEY found. Add it in Streamlit Secrets.",
            "score": 0,
            "category": "error",
            "action": "fix api key"
        }

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Keep last 8 messages for memory
    for msg in history[-8:]:
        messages.append({
            "role": msg["role"],
            "content": msg["content"]
        })
    
    messages.append({"role": "user", "content": user_message})

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": messages,
                "temperature": 0.9,
                "max_tokens": 220
            },
            timeout=30
        )
        
        data = response.json()
        
        if "error" in data:
            reply = f"API error: {data['error'].get('message', str(data))}"
        else:
            reply = data["choices"][0]["message"]["content"].strip()
        
    except Exception as e:
        reply = f"Error talking to the brain: {str(e)}"
    
    # Rule-based scoring
    lower = user_message.lower()
    score = 25
    if any(w in lower for w in ["how much", "price", "custom", "buy", "pay", "subscription", "pack", "unlock"]):
        score = 78
    if any(w in lower for w in ["free", "send nudes", "just looking", "no money", "broke"]):
        score = 12

    if score >= 70:
        category = "whale"
        action = "soft close + paywall"
    elif score >= 40:
        category = "mid"
        action = "tease harder"
    else:
        category = "time-waster"
        action = "polite fade"

    return {
        "reply": reply,
        "score": score,
        "category": category,
        "action": action
    }

# ========== SIDEBAR ==========
st.sidebar.title("🖤 Persona Agent")
page = st.sidebar.radio("Go to", ["Chat Test", "Dashboard", "Settings"])

# ========== CHAT PAGE ==========
if page == "Chat Test":
    st.title("Chat Test")
    st.caption("Groq free tier + conversation memory")

    for msg in st.session_state.current_chat:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if msg["role"] == "assistant" and "meta" in msg:
                meta = msg["meta"]
                st.caption(f"Score: {meta['score']} | {meta['category']} | → {meta['action']}")

    if prompt := st.chat_input("Message her..."):
        st.session_state.current_chat.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.write(prompt)

        result = call_persona_llm(prompt, st.session_state.current_chat)

        assistant_msg = {
            "role": "assistant",
            "content": result["reply"],
            "meta": {
                "score": result["score"],
                "category": result["category"],
                "action": result["action"]
            }
        }
        st.session_state.current_chat.append(assistant_msg)

        with st.chat_message("assistant"):
            st.write(result["reply"])
            st.caption(f"Score: {result['score']} | {result['category']} | → {result['action']}")

        st.session_state.conversations.append({
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "preview": prompt[:50],
            "score": result["score"],
            "category": result["category"]
        })

# ========== DASHBOARD ==========
elif page == "Dashboard":
    st.title("Dashboard")

    total = len(st.session_state.conversations)
    whales = len([c for c in st.session_state.conversations if c["category"] == "whale"])
    avg = sum(c["score"] for c in st.session_state.conversations) / total if total else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Chats", total)
    c2.metric("Whales", whales)
    c3.metric("Avg Score", f"{avg:.0f}")

    st.subheader("Recent Conversations")
    if not st.session_state.conversations:
        st.info("No chats yet.")
    else:
        for conv in reversed(st.session_state.conversations[-20:]):
            color = "🟢" if conv["score"] >= 70 else "🟡" if conv["score"] >= 40 else "🔴"
            st.write(f"{color} **{conv['timestamp']}** — Score {conv['score']} ({conv['category']}) | {conv['preview']}...")

# ========== SETTINGS ==========
elif page == "Settings":
    st.title("Settings")
    st.text_area("Current System Prompt", value=SYSTEM_PROMPT, height=200)
    st.info("Next: replace this with the real soul prompt once you fill the questionnaire.")

st.sidebar.markdown("---")
st.sidebar.caption("Ghost build • Groq free tier + Memory")
