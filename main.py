import os
import json
import time
import base64
import hashlib
import tempfile
import asyncio
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import edge_tts
from groq import Groq

st.set_page_config(page_title="AI Interview Coach", page_icon="🎤", layout="wide")
GROQ_API_KEY = "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"  # Add your Groq API key here

client = Groq(api_key=GROQ_API_KEY)

MODES = ["HR Interview", "Technical Interview", "Final Mixed Simulation"]
PERSONALITIES = ["Friendly", "Professional"]
TOPICS = [
    "Python", "MySQL", "NumPy", "Pandas", "Matplotlib", "Seaborn", "Statistics",
    "EDA", "Machine Learning", "Deep Learning", "NLP", "Computer Vision",
    "Generative AI", "Excel", "Power BI", "Microsoft Office",
    "Communication skills", "Presentation", "Public speaking",
]
EDGE_VOICES = ["en-US-AriaNeural", "en-US-JennyNeural", "en-US-GuyNeural"]

if "boot" not in st.session_state:
    st.session_state.boot = True
    st.session_state.started = False
    st.session_state.finished = False
    st.session_state.mode = "HR Interview"
    st.session_state.level = "Level 1 - Beginner"
    st.session_state.personality = "Friendly"
    st.session_state.selected_topics = ["Communication skills"]
    st.session_state.voice = EDGE_VOICES[0]
    st.session_state.total_questions = 6
    st.session_state.questions_asked = 0
    st.session_state.current_q = None
    st.session_state.prev_q = None
    st.session_state.prev_a = None
    st.session_state.history = []
    st.session_state.weak_topics = []
    st.session_state.weak_questions = []
    # FIX BUG 1: removed `greeted` flag entirely — greeting lives only in generate_question()
    st.session_state.last_spoken_q = None       # tracks which question TTS was generated for
    st.session_state.question_audio_b64 = None  # base64 mp3 string
    st.session_state.last_result = None
    st.session_state.show_feedback_until = 0
    st.session_state.processed_audio_hash = None
    st.session_state.final_report_cache = None
    st.session_state.tts_cache = {}
    st.session_state.kpi = {"technical": 0, "grammar": 0, "communication": 0, "confidence": 0}
    st.session_state.answer_score = 0
    st.session_state.mic_key = 0

CSS = """
<style>
.stApp{background:radial-gradient(circle at top,#22315f 0%,#0b1020 45%,#050816 100%);color:#e5eefc}
[data-testid="stSidebar"]{background:rgba(10,16,32,.72);border-right:1px solid rgba(255,255,255,.08)}
.glass{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);border-radius:18px;
       box-shadow:0 10px 30px rgba(0,0,0,.25);backdrop-filter:blur(10px)}
.hero{text-align:center;padding:.6rem 0 .2rem}
.hero h1{margin:0;font-size:2.1rem;font-weight:800}
.hero p{margin:.3rem 0 0;color:#c6d4f3;font-size:1.02rem}
.questionbox{text-align:center;padding:1.3rem 1rem}
.questionbox h2{margin:.2rem 0;font-size:1.45rem;line-height:1.5}
.micwrap{display:flex;align-items:center;justify-content:center;padding:1rem 0 .3rem}
.mic{width:120px;height:120px;border-radius:50%;
     background:radial-gradient(circle at 30% 30%,#7fd7ff 0%,#1d78ff 45%,#0f234a 100%);
     box-shadow:0 0 30px rgba(99,180,255,.55),inset 0 0 20px rgba(255,255,255,.12);
     display:flex;align-items:center;justify-content:center;font-size:3rem;
     animation:pulse 1.8s infinite ease-in-out}
@keyframes pulse{
  0%{transform:scale(1);box-shadow:0 0 24px rgba(99,180,255,.35)}
  50%{transform:scale(1.04);box-shadow:0 0 44px rgba(99,180,255,.75)}
  100%{transform:scale(1);box-shadow:0 0 24px rgba(99,180,255,.35)}}
.footerline{text-align:center;color:#d5ddf5;font-size:1.02rem;font-weight:600;margin-top:.4rem}
.report-header{text-align:center;padding:1.5rem 0 1rem}
.report-header h1{margin:0;font-size:2.2rem;font-weight:800;background:linear-gradient(135deg,#ffd700,#ff9800);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.report-header p{margin:.4rem 0 0;color:#c6d4f3;font-size:1rem}
.grade-badge{display:inline-block;padding:12px 32px;border-radius:50%;font-size:2.5rem;font-weight:900;
             background:linear-gradient(135deg,#1d78ff,#7fd7ff);box-shadow:0 0 40px rgba(99,180,255,.5);margin:10px 0}
.grade-A{background:linear-gradient(135deg,#00c853,#69f0d0);box-shadow:0 0 40px rgba(0,200,83,.5)}
.grade-B{background:linear-gradient(135deg,#2196f3,#64b5f6);box-shadow:0 0 40px rgba(33,150,243,.5)}
.grade-C{background:linear-gradient(135deg,#ff9800,#ffb74d);box-shadow:0 0 40px rgba(255,152,0,.5)}
.grade-D{background:linear-gradient(135deg,#f44336,#ef9a9a);box-shadow:0 0 40px rgba(244,67,54,.5)}
.insight-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:14px;padding:18px 20px;margin:8px 0}
.strength-item{display:flex;align-items:flex-start;gap:12px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.06)}
.strength-item:last-child{border-bottom:none}
.strength-icon{font-size:1.4rem;min-width:30px;text-align:center}
.strength-text{color:#e5eefc;font-size:.95rem;line-height:1.5}
.weakness-item{display:flex;align-items:flex-start;gap:12px;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.06)}
.weakness-item:last-child{border-bottom:none}
.weakness-icon{font-size:1.4rem;min-width:30px;text-align:center}
.weakness-text{color:#e5eefc;font-size:.95rem;line-height:1.5}
.day-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:12px;padding:14px 18px;margin:6px 0;
          display:flex;align-items:flex-start;gap:14px;transition:transform .2s}
.day-card:hover{transform:translateX(4px)}
.day-num{background:linear-gradient(135deg,#1d78ff,#7fd7ff);color:#fff;border-radius:10px;
         min-width:44px;height:44px;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:.95rem}
.day-text{color:#d5ddf5;font-size:.93rem;line-height:1.55;padding-top:8px}
.score-bar{height:8px;border-radius:4px;background:rgba(255,255,255,.1);overflow:hidden;margin-top:6px}
.score-fill{height:100%;border-radius:4px;transition:width .8s ease}
.report-section-title{font-size:1.2rem;font-weight:700;margin:1.2rem 0 .6rem;padding-left:4px;
                       border-left:4px solid #1d78ff;padding-left:12px}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def safe_metric(v):
    try:
        return float(v)
    except Exception:
        return 0.0


def level_difficulty(level):
    return "easy" if "Beginner" in level else "medium" if "Intermediate" in level else "hard"


def sha_audio(b):
    return hashlib.sha256(b).hexdigest()


def tts_b64_cached(text, voice):


    key = f"{voice}::{text}"
    if key in st.session_state.tts_cache:
        return st.session_state.tts_cache[key]

    result = {"b64": None}

    def run_in_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
                path = tmp.name
            async def _generate():
                communicate = edge_tts.Communicate(text=text, voice=voice)
                await communicate.save(path)
            loop.run_until_complete(_generate())
            with open(path, "rb") as f:
                result["b64"] = base64.b64encode(f.read()).decode()
            os.remove(path)
        except Exception as e:
            result["error"] = str(e)
        finally:
            loop.close()

    import threading
    t = threading.Thread(target=run_in_thread, daemon=True)
    t.start()
    t.join()

    st.session_state.tts_cache[key] = result["b64"]
    return result["b64"]


def autoplay_audio_b64(b64: str):

    if not b64:
        return

    unique_id = str(int(time.time() * 1000))

    audio_html = f"""
    <audio id="audio_{unique_id}" autoplay>
        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
    </audio>

    <script>
    const audio = document.getElementById("audio_{unique_id}");

    async function forcePlay() {{
        try {{

            // Chrome autoplay fix
            audio.muted = true;

            await audio.play();

            audio.muted = false;

            console.log("Autoplay success");

        }} catch(err) {{

            console.log("Autoplay blocked:", err);

            // Retry after user interaction
            document.addEventListener("click", () => {{
                audio.play();
            }}, {{ once: true }});

        }}
    }}

    </script>
    """

    st.html(audio_html)


def transcribe_audio(audio_bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(audio_bytes)
        path = tmp.name
    try:
        with open(path, "rb") as f:
            tr = client.audio.transcriptions.create(
                model="whisper-large-v3-turbo",
                file=f,
                response_format="json",
                language="en",
            )
        return tr.text
    finally:
        try:
            os.remove(path)
        except Exception:
            pass


# FIX BUG 1: generate_question() is the ONLY place that sets the greeting.
# The original code had a second `greeted` block OUTSIDE this function that
# also set current_q to the greeting — causing Q1 to render twice.
def generate_question():
    if st.session_state.questions_asked == 0 and st.session_state.mode == "HR Interview":
        return {
            "question": "Hi, welcome! Take a breath. How are you feeling today? Before we begin, tell me a little about yourself.",
            "focus_area": "hr",
            "difficulty": "easy",
            "time_limit_seconds": 45,
        }
    prompt = f"""
You are a real interviewer in a voice interview app.
Generate ONE next interview question dynamically.
Mode: {st.session_state.mode}
Level: {st.session_state.level}
Personality: {st.session_state.personality}
Topics: {st.session_state.selected_topics}
Difficulty: {level_difficulty(st.session_state.level)}
Previous question: {st.session_state.prev_q}
Previous answer: {st.session_state.prev_a}
Weak topics: {st.session_state.weak_topics[-5:]}
Questions asked so far: {st.session_state.questions_asked}
Return JSON only:
{{"question":"...","focus_area":"technical|hr|behavioral|communication","difficulty":"easy|medium|hard","time_limit_seconds":60}}
"""
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.85,
        max_completion_tokens=450,
    )
    return json.loads(r.choices[0].message.content)


def evaluate_answer(question, answer):
    prompt = f"""
You are a strict interview evaluator. Always provide feedback.

Question: {question}
Candidate answer: "{answer}"

RULES:
- For short greetings/thank you (e.g. "Thank you", "I'm fine", "Good"): verdict "correct", grammar_issues=[], right_answer="Nice warmup — a stronger answer would be: [write 2-3 sentences]", suggestions=["Elaborate more on your response"], answer_score=7, scores={{"technical":7,"grammar":8,"communication":8,"confidence":8}}
- For actual answers: evaluate fully. ALWAYS provide grammar_issues (list actual errors found, or list specific areas to improve grammar style). ALWAYS provide right_answer (2-4 sentences ideal answer).
- grammar_issues must be ACTUAL errors in their exact words (e.g. "Used 'I completed' should be 'I have completed'"). If no errors, list style improvements like "Could use more specific examples" or "Consider using past tense for completed work".
- right_answer is ALWAYS required — the ideal response the candidate should give.

Return JSON only:
{{
  "verdict": "correct|partial|wrong",
  "right_answer": "2-4 sentence ideal answer — ALWAYS provide this, never empty",
  "grammar_issues": ["specific issue 1", "specific issue 2"],
  "suggestions": ["tip 1", "tip 2"],
  "answer_score": 7,
  "scores": {{"technical":7,"grammar":7,"communication":8,"confidence":7}},
  "weak_topic": "topic or empty string",
  "weak_question_note": "note or empty string"
}}
"""
    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a strict interview evaluator. Always provide detailed feedback. Return valid JSON only."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
        max_completion_tokens=800,
    )
    return json.loads(r.choices[0].message.content)


def final_report():
    fallback = {
        "technical_score": 0, "grammar_score": 0,
        "communication_score": 0, "confidence_level": 0,
        "answer_score": 0, "overall_grade": "C",
        "strengths": ["Completed the interview session"], "weaknesses": ["Insufficient data for detailed analysis"],
        "next_7_day_plan": [
            "Review core concepts and fundamentals",
            "Practice mock interviews with a friend",
            "Work on communication and clarity",
            "Study technical topics in depth",
            "Practice answering under time pressure",
            "Review grammar and professional language",
            "Do a full mock interview simulation"
        ],
    }
    if not st.session_state.history:
        return fallback
    df = pd.DataFrame([x["scores"] for x in st.session_state.history])
    avg_tech = round(df["technical"].mean(), 1)
    avg_gram = round(df["grammar"].mean(), 1)
    avg_comm = round(df["communication"].mean(), 1)
    avg_conf = round(df["confidence"].mean(), 1)
    avg_ans = round(st.session_state.answer_score, 1)
    overall = round((avg_tech + avg_gram + avg_comm + avg_conf + avg_ans) / 5, 1)
    summary_lines = []
    for i, h in enumerate(st.session_state.history, 1):
        q = h["question"][:100]
        a = h["answer"][:100]
        r = h.get("result", {})
        verdict = r.get("verdict", "unknown")
        grammar = r.get("grammar_issues", [])
        grammar_str = "; ".join(grammar[:2]) if grammar else "none"
        summary_lines.append(
            f"Q{i}: {q}\nA{i}: {a}\nVerdict: {verdict} | Grammar: {grammar_str}\nScores: tech={h['scores'].get('technical',0)}, gram={h['scores'].get('grammar',0)}, comm={h['scores'].get('communication',0)}, conf={h['scores'].get('confidence',0)}"
        )
    summaries = "\n\n".join(summary_lines)
    weak_str = ", ".join(st.session_state.weak_topics[-10:]) if st.session_state.weak_topics else "none"
    prompt = f"""You are an expert interview coach. Analyze this interview session and generate a detailed report.

INTERVIEW INFO:
- Mode: {st.session_state.mode}
- Level: {st.session_state.level}
- Total Questions: {st.session_state.questions_asked}
- Personality: {st.session_state.personality}

SCORE AVERAGES (out of 10):
- Technical: {avg_tech}
- Grammar: {avg_gram}
- Communication: {avg_comm}
- Confidence: {avg_conf}
- Answer Score: {avg_ans}
- Overall: {overall}

WEAK TOPICS: {weak_str}

QUESTION-BY-QUESTION BREAKDOWN:
{summaries}

Generate a JSON report with EXACTLY these keys:
{{
  "overall_grade": "A/B/C/D/F based on overall score (A=8+, B=6.5-7.9, C=5-6.4, D=3.5-4.9, F=below 3.5)",
  "strengths": ["3-5 specific strengths with examples from the interview"],
  "weaknesses": ["3-5 specific weaknesses with examples from the interview"],
  "next_7_day_plan": [
    "Day 1: specific actionable task",
    "Day 2: specific actionable task",
    "Day 3: specific actionable task",
    "Day 4: specific actionable task",
    "Day 5: specific actionable task",
    "Day 6: specific actionable task",
    "Day 7: specific actionable task with full mock interview"
  ]
}}"""
    try:
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an expert interview coach. Return valid JSON only, no markdown, no extra text."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_completion_tokens=1500,
        )
        report = json.loads(r.choices[0].message.content)
        report.setdefault("overall_grade", "C")
        report.setdefault("strengths", ["Completed the interview"])
        report.setdefault("weaknesses", ["Needs more practice"])
        report.setdefault("next_7_day_plan", [
            "Review core concepts", "Practice mock interviews", "Work on communication",
            "Study technical topics", "Practice under time pressure", "Review grammar", "Full mock interview"
        ])
        report["technical_score"] = avg_tech
        report["grammar_score"] = avg_gram
        report["communication_score"] = avg_comm
        report["confidence_level"] = avg_conf
        report["answer_score"] = avg_ans
        report["overall_score"] = overall
        return report
    except Exception as e:
        st.warning(f"Report generation failed: {e}")
        fallback["technical_score"] = avg_tech
        fallback["grammar_score"] = avg_gram
        fallback["communication_score"] = avg_comm
        fallback["confidence_level"] = avg_conf
        fallback["answer_score"] = avg_ans
        fallback["overall_score"] = overall
        return fallback


def gauge(title, value, color):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=safe_metric(value),
        number={"suffix": "/10", "font": {"size": 34, "color": "#eaf2ff"}},
        title={"text": title, "font": {"size": 18, "color": "#eaf2ff"}},
        gauge={
            "axis": {"range": [0, 10]},
            "bar": {"color": color},
            "bgcolor": "rgba(255,255,255,0.08)",
            "steps": [{"range": [0, 10], "color": "rgba(255,255,255,0.06)"}],
        },
    ))
    fig.update_layout(margin=dict(l=8, r=8, t=40, b=8), height=160,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="hero"><h1>🤖 AI Interview Coach</h1>'
    '<p>AI asks → You answer by voice → Grammar feedback + Answer Score → Master interviews</p></div>',
    unsafe_allow_html=True,
)

# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="glass" style="padding:16px;">', unsafe_allow_html=True)
    st.markdown("### 🎯 Prep Settings")
    st.session_state.selected_topics = st.multiselect("Topic", TOPICS, default=st.session_state.selected_topics)
    lvl = st.radio("Level", ["1", "2", "3"],
                   index=["Level 1 - Beginner", "Level 2 - Intermediate", "Level 3 - Advanced"]
                   .index(st.session_state.level), horizontal=True)
    st.session_state.level = {"1": "Level 1 - Beginner", "2": "Level 2 - Intermediate",
                               "3": "Level 3 - Advanced"}[lvl]
    st.session_state.mode = st.selectbox("Mode", MODES, index=MODES.index(st.session_state.mode))
    st.session_state.personality = st.selectbox("Persona", PERSONALITIES,
                                                index=PERSONALITIES.index(st.session_state.personality))
    st.session_state.voice = st.selectbox("Edge Voice", EDGE_VOICES,
                                          index=EDGE_VOICES.index(st.session_state.voice))
    st.session_state.total_questions = st.slider("Questions", 4, 12, st.session_state.total_questions)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 Start Interview", use_container_width=True):
            st.session_state.started = True
            st.session_state.finished = False
            st.session_state.questions_asked = 0
            st.session_state.current_q = None        # will call generate_question() fresh
            st.session_state.prev_q = None
            st.session_state.prev_a = None
            st.session_state.history = []
            st.session_state.weak_topics = []
            st.session_state.weak_questions = []
            st.session_state.last_spoken_q = None    # force TTS re-generation
            st.session_state.question_audio_b64 = None
            st.session_state.last_result = None
            st.session_state.show_feedback_until = 0
            st.session_state.processed_audio_hash = None
            st.session_state.final_report_cache = None
            st.session_state.processed_audio_hash = None
            st.session_state.audio_played_for_question = False
            st.session_state.tts_cache = {}
            st.session_state.kpi = {"technical": 0, "grammar": 0, "communication": 0, "confidence": 0}
            st.session_state.answer_score = 0
            st.session_state.mic_key = 0
            st.rerun()
    with c2:
        if st.button("Reset", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ─── KPI Gauges ───────────────────────────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
for col, (title, value, color) in zip(
    [k1, k2, k3, k4, k5],
    [
        ("Technical",     st.session_state.kpi["technical"],     "#3ba5ff"),
        ("Grammar",       st.session_state.kpi["grammar"],       "#69f0d0"),
        ("Communication", st.session_state.kpi["communication"], "#ffc86b"),
        ("Confidence",    st.session_state.kpi["confidence"],    "#be7dff"),
        ("Answer",        st.session_state.answer_score,         "#ffeb3b"),
    ],
):
    with col:
        st.markdown('<div class="glass">', unsafe_allow_html=True)
        st.plotly_chart(gauge(title, value, color), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ─── Interview Flow ───────────────────────────────────────────────────────────
if st.session_state.get("started") and not st.session_state.get("finished"):


    if st.session_state.current_q is None:
        st.session_state.current_q = generate_question()

    q_text = st.session_state.current_q["question"]

    # Generate TTS only once per question
    if st.session_state.last_spoken_q != q_text:
        st.session_state.question_audio_b64 = tts_b64_cached(
            q_text,
            st.session_state.voice
        )

        st.session_state.last_spoken_q = q_text
        st.session_state.audio_played_for_question = False

    # Play audio only once
    if (
            st.session_state.question_audio_b64
            and not st.session_state.audio_played_for_question
    ):
        autoplay_audio_b64(
            st.session_state.question_audio_b64
        )

        st.session_state.audio_played_for_question = True


    # Progress bar
    st.progress(min(1.0, st.session_state.questions_asked / max(1, st.session_state.total_questions)))
    st.markdown(
        f'<div style="text-align:center;color:#d7e2ff;margin-top:4px;">'
        f'Question {st.session_state.questions_asked + 1} of {st.session_state.total_questions}</div>',
        unsafe_allow_html=True,
    )

    # Question card
    st.markdown('<div class="glass questionbox">', unsafe_allow_html=True)
    st.markdown(f"<h2>Q{st.session_state.questions_asked + 1}: {q_text}</h2>", unsafe_allow_html=True)
    st.markdown('<div class="micwrap"><div class="mic">🎙️</div></div>', unsafe_allow_html=True)
    st.markdown('<div class="footerline">Listening… record your answer below</div>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # Mic input — mic_key resets the widget after Next/Retry so old audio is cleared
    audio = st.audio_input("🎤 Record your answer", key=f"mic_{st.session_state.mic_key}")

    if audio is not None:
        raw = audio.getvalue()
        h = sha_audio(raw)
        if st.session_state.processed_audio_hash != h:
            st.session_state.processed_audio_hash = h
            try:
                with st.spinner("Transcribing & evaluating…"):
                    ans = transcribe_audio(raw)
                    result = evaluate_answer(q_text, ans)
                scores = result.get("scores", {})
                st.session_state.kpi["technical"]     = safe_metric(scores.get("technical", 0))
                st.session_state.kpi["grammar"]        = safe_metric(scores.get("grammar", 0))
                st.session_state.kpi["communication"]  = safe_metric(scores.get("communication", 0))
                st.session_state.kpi["confidence"]     = safe_metric(scores.get("confidence", 0))
                st.session_state.answer_score          = safe_metric(result.get("answer_score", 0))
                st.session_state.history.append(
                    {"question": q_text, "answer": ans, "result": result, "scores": scores}
                )
                if result.get("weak_topic"):
                    st.session_state.weak_topics.append(result["weak_topic"])
                if result.get("weak_question_note"):
                    st.session_state.weak_questions.append(q_text)
                st.session_state.prev_q = q_text
                st.session_state.prev_a = ans
                st.session_state.last_result = result
                st.session_state.show_feedback_until = time.time() + 30
                st.session_state.final_report_cache = None
                st.rerun()
            except Exception as e:
                st.error(f"Processing failed: {e}")

    # ── Feedback panel ────────────────────────────────────────────────────────
    if st.session_state.last_result and time.time() < st.session_state.show_feedback_until:
        r = st.session_state.last_result
        ans_text = st.session_state.history[-1]["answer"] if st.session_state.history else ""

        st.markdown('<div class="glass" style="padding:20px;margin-top:12px;">', unsafe_allow_html=True)
        st.subheader("🔍 Live Feedback")

        kk1, kk2, kk3, kk4, kk5 = st.columns(5)
        with kk1: st.metric("Technical",     st.session_state.kpi["technical"])
        with kk2: st.metric("Grammar",        st.session_state.kpi["grammar"])
        with kk3: st.metric("Communication",  st.session_state.kpi["communication"])
        with kk4: st.metric("Confidence",     st.session_state.kpi["confidence"])
        with kk5: st.metric("Answer Score",   f"{st.session_state.answer_score:.1f}/10")


        st.markdown("### 📝 Your Answer")
        st.markdown(
            f'<div style="background:rgba(255,255,255,0.05);padding:16px;border-radius:12px;'
            f'border-left:4px solid #ff9800;min-height:60px;line-height:1.7;white-space:pre-wrap;">'
            f'{ans_text}</div>',
            unsafe_allow_html=True,
        )

        # Grammar issues — always show
        grammar_issues = r.get("grammar_issues", [])
        st.markdown("**⚠️ Grammar Issues & Feedback:**")
        if grammar_issues:
            for issue in grammar_issues[:5]:
                st.markdown(f"- {issue}")
        else:
            st.markdown("- No grammar errors detected. Good job!")

        # Ideal answer — always show
        st.markdown("### ✅ Ideal Answer")
        correct_ans = r.get("right_answer", "")
        if not correct_ans or correct_ans.strip() == "":
            correct_ans = "Practice giving a more detailed response with specific examples."
        st.markdown(
            f'<div style="background:rgba(76,175,80,0.1);padding:16px;border-radius:12px;'
            f'border-left:4px solid #4caf50;line-height:1.7;">{correct_ans}</div>',
            unsafe_allow_html=True,
        )

        st.success(f"**Answer Score: {st.session_state.answer_score:.1f}/10**")
        st.caption("*Answer Score = Relevance + Completeness (0–10)*")

        if r.get("suggestions"):
            st.markdown("### 💡 Quick Improvements")
            for s in r["suggestions"][:3]:
                st.markdown(f"- {s}")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("➡️ Next Question", width="stretch"):
                st.session_state.questions_asked += 1
                if st.session_state.questions_asked >= st.session_state.total_questions:
                    st.session_state.finished = True
                else:
                    # Set current_q=None so generate_question() runs for next Q
                    # Clear last_spoken_q so TTS re-fires for the new question
                    st.session_state.current_q = None
                    st.session_state.last_spoken_q = None
                    st.session_state.question_audio_b64 = None
                    st.session_state.last_result = None
                    st.session_state.processed_audio_hash = None
                    st.session_state.processed_audio_hash = None
                    st.session_state.audio_played_for_question = False
                    st.session_state.mic_key += 1  # resets mic widget
                st.rerun()
        with c2:
            if st.button("🔄 Retry Question", use_container_width=True):
                # Keep current_q (same question), clear last_spoken_q so TTS re-fires
                st.session_state.last_spoken_q = None
                st.session_state.question_audio_b64 = None
                st.session_state.last_result = None
                st.session_state.processed_audio_hash = None
                st.session_state.processed_audio_hash = None
                st.session_state.audio_played_for_question = False
                st.session_state.mic_key += 1
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    elif st.session_state.last_result and time.time() >= st.session_state.show_feedback_until:
        st.session_state.last_result = None

# ─── Final Report ─────────────────────────────────────────────────────────────
elif st.session_state.get("finished"):
    if st.session_state.final_report_cache is None:
        with st.spinner("Generating your final report…"):
            st.session_state.final_report_cache = final_report()
    fb = st.session_state.final_report_cache

    grade = fb.get("overall_grade", "C").upper().strip()
    if grade not in ("A", "B", "C", "D", "F"):
        grade = "C"
    overall = fb.get("overall_score", 0)
    tech = fb.get("technical_score", 0)
    gram = fb.get("grammar_score", 0)
    comm = fb.get("communication_score", 0)
    conf = fb.get("confidence_level", 0)
    ans = fb.get("answer_score", 0)

    st.markdown('<div class="glass" style="padding:24px 28px;">', unsafe_allow_html=True)

    # Header
    st.markdown(
        f'<div class="report-header">'
        f'<h1>🏆 Final Interview Report</h1>'
        f'<p>{st.session_state.mode} &bull; {st.session_state.level} &bull; {st.session_state.questions_asked} Questions</p>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Overall Grade Badge
    st.markdown(
        f'<div style="text-align:center;margin:10px 0 20px;">'
        f'<div class="grade-badge grade-{grade}">{grade}</div>'
        f'<div style="font-size:1.1rem;color:#c6d4f3;margin-top:6px;">Overall Score: <b>{overall}/10</b></div>'
        f'</div>',
        unsafe_allow_html=True
    )

    # Score Bars
    def score_bar_html(label, value, color):
        pct = min(100, max(0, value * 10))
        return (
            f'<div style="margin:10px 0;">'
            f'<div style="display:flex;justify-content:space-between;margin-bottom:4px;">'
            f'<span style="color:#c6d4f3;font-size:.9rem;font-weight:600;">{label}</span>'
            f'<span style="color:#e5eefc;font-size:.9rem;font-weight:700;">{value}/10</span></div>'
            f'<div class="score-bar"><div class="score-fill" style="width:{pct}%;background:{color};"></div></div>'
            f'</div>'
        )

    st.markdown(
        '<div class="report-section-title">Score Breakdown</div>'
        '<div class="insight-card">'
        + score_bar_html("Technical", tech, "#3ba5ff")
        + score_bar_html("Grammar", gram, "#69f0d0")
        + score_bar_html("Communication", comm, "#ffc86b")
        + score_bar_html("Confidence", conf, "#be7dff")
        + score_bar_html("Answer Score", ans, "#ffeb3b")
        + '</div>',
        unsafe_allow_html=True
    )

    # Strengths
    strengths = fb.get("strengths", [])
    if strengths:
        items = ""
        for s in strengths:
            items += f'<div class="strength-item"><span class="strength-icon">✅</span><span class="strength-text">{s}</span></div>'
        st.markdown(
            '<div class="report-section-title">Strengths</div>'
            f'<div class="insight-card">{items}</div>',
            unsafe_allow_html=True
        )

    # Weaknesses
    weaknesses = fb.get("weaknesses", [])
    if weaknesses:
        items = ""
        for w in weaknesses:
            items += f'<div class="weakness-item"><span class="weakness-icon">⚠️</span><span class="weakness-text">{w}</span></div>'
        st.markdown(
            '<div class="report-section-title">Areas to Improve</div>'
            f'<div class="insight-card">{items}</div>',
            unsafe_allow_html=True
        )

    # 7-Day Plan
    plan = fb.get("next_7_day_plan", [])
    if plan:
        cards = ""
        for i, day in enumerate(plan, 1):
            day_label = day
            if day.lower().startswith("day"):
                parts = day.split(":", 1)
                if len(parts) == 2:
                    day_label = parts[1].strip()
            cards += f'<div class="day-card"><div class="day-num">D{i}</div><div class="day-text">{day_label}</div></div>'
        st.markdown(
            '<div class="report-section-title">7-Day Improvement Plan</div>'
            f'{cards}',
            unsafe_allow_html=True
        )

    # Weak Topics
    if st.session_state.weak_topics:
        topic_badges = " ".join([f'<span style="background:rgba(244,67,54,.2);color:#ef9a9a;padding:4px 12px;border-radius:20px;font-size:.85rem;margin:3px;display:inline-block;">{t}</span>' for t in st.session_state.weak_topics[-8:]])
        st.markdown(
            '<div class="report-section-title">Weak Topics Detected</div>'
            f'<div style="padding:8px 0;">{topic_badges}</div>',
            unsafe_allow_html=True
        )

    st.markdown("</div>", unsafe_allow_html=True)

# ─── Not started ──────────────────────────────────────────────────────────────
else:
    st.markdown(
        '<div class="glass" style="padding:24px;text-align:center;">'
        '🎯 Choose settings in the sidebar & click <b>Start Interview</b><br>'
        '<small>Voice → Grammar feedback → Answer Score → Perfect answers</small></div>',
        unsafe_allow_html=True,
    )
