"""
NetraAI — AI Health Assistant Service
Powered by Google Gemini API.
Provides patient-facing DR education, report explanation, symptom pre-screening,
and referral guidance. NOT a replacement for clinical doctor review.
"""
import os

# System prompt that scopes the AI strictly to ophthalmic patient help
NETRA_SYSTEM_PROMPT = """You are **Netra Assistant**, a friendly, empathetic AI health guide integrated into NetraAI — India's national tele-ophthalmology platform for Diabetic Retinopathy (DR) screening.

Your ONLY purpose is to help patients in the following areas:
1. **Explain DR screening results** — Translate ICDR Grade 0-4 into simple, non-alarming plain language (in English or Hindi depending on the patient message)
2. **Educate about Diabetic Retinopathy** — Causes, stages, progression, treatment options
3. **Symptom guidance** — Help patients understand symptoms like blurred vision, floaters, dark spots, halos; advise whether to seek urgent screening
4. **Screening procedure** — Explain what happens during a fundus camera scan, how to prepare
5. **Lifestyle & prevention** — HbA1c control, diet tips for diabetic eye health, regular monitoring importance
6. **Referral readiness** — Help patients understand if their grade means they need an in-person ophthalmologist visit
7. **Report understanding** — Explain microaneurysms, hard exudates, cotton wool spots in simple terms

STRICT RULES you MUST follow:
- NEVER give specific drug dosage, prescriptions, or treatment decisions
- NEVER diagnose any condition beyond interpreting the AI-generated ICDR grade shown to the patient
- If asked about non-eye/non-diabetes topics, politely redirect: "I'm specialized only in diabetic eye health. For other concerns, please consult your doctor."
- Always end answers about serious grades (Grade 3 or 4) with: "Please consult your assigned ophthalmologist or visit a specialist immediately."
- Keep answers concise, warm, and easy to understand — avoid medical jargon unless explaining it
- For Hindi messages, respond in Hindi (Devanagari or Romanized, matching user style)
- Add a brief disclaimer at the end of medical advice: "This is for educational guidance only. Always follow your doctor's clinical advice."

ICDR Grade Reference (use this when explaining results):
- Grade 0: No DR — retina appears healthy
- Grade 1: Mild NPDR — tiny microaneurysms, close monitoring needed
- Grade 2: Moderate NPDR — more lesions, 6-month review recommended
- Grade 3: Severe NPDR — many lesions, urgent specialist referral needed
- Grade 4: PDR (Proliferative DR) — new blood vessel growth, emergency ophthalmology care required

If the patient shares their grade or report details, use that context to personalize your response."""


def get_ai_response(user_message: str, conversation_history: list, patient_context: dict = None) -> dict:
    """
    Get AI response from Gemini API.

    Args:
        user_message: The patient's current message
        conversation_history: List of {"role": "user"/"model", "parts": [{"text": "..."}]}
        patient_context: Optional dict with keys like severity_name, icdr_grade, diabetes_type, age

    Returns:
        {"reply": str, "disclaimer": str, "error": str|None}
    """
    try:
        from dotenv import load_dotenv
        env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(env_file):
            load_dotenv(env_file, override=True)
    except Exception:
        pass

    api_key = os.environ.get("GEMINI_API_KEY", "")

    if not api_key or api_key == "YOUR_GEMINI_API_KEY_HERE":
        return {
            "reply": None,
            "disclaimer": None,
            "error": "GEMINI_API_KEY is not configured. Please add your key to backend/.env and restart the server. Get a free key at https://aistudio.google.com/app/apikey"
        }

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)

        # Build patient context prefix if available
        context_prefix = ""
        if patient_context:
            parts = []
            if patient_context.get("severity_name"):
                parts.append(f"DR Severity: {patient_context['severity_name']} (ICDR Grade {patient_context.get('icdr_grade', '?')})")
            if patient_context.get("diabetes_type"):
                parts.append(f"Diabetes Type: {patient_context['diabetes_type']}")
            if patient_context.get("age"):
                parts.append(f"Age: {patient_context['age']}")
            if parts:
                context_prefix = f"[Patient Context - {', '.join(parts)}]\n\n"

        model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=NETRA_SYSTEM_PROMPT,
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 600,
                "top_p": 0.85,
            },
            safety_settings=[
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
        )

        chat = model.start_chat(history=conversation_history)
        full_message = context_prefix + user_message
        response = chat.send_message(full_message)

        reply_text = response.text.strip()

        return {
            "reply": reply_text,
            "disclaimer": "Netra Assistant provides educational guidance only and does not replace clinical advice from your assigned ophthalmologist.",
            "error": None
        }

    except ImportError:
        return {
            "reply": None,
            "disclaimer": None,
            "error": "google-generativeai package not installed. Run: pip install google-generativeai"
        }
    except Exception as e:
        err_str = str(e)
        if "leaked" in err_str.lower():
            return {
                "reply": None,
                "disclaimer": None,
                "error": "Your Google Gemini API key was reported as leaked and revoked by Google. Please generate a new free key at https://aistudio.google.com/app/apikey, paste it in backend/.env, and restart the backend server."
            }
        if "not found" in err_str.lower() or "permissiondenied" in err_str.lower() or "403" in err_str:
            return {
                "reply": None,
                "disclaimer": None,
                "error": "Gemini API rejected the request (key revoked or reported as leaked). Please generate a fresh free key at https://aistudio.google.com/app/apikey and paste it into backend/.env."
            }
        if "API_KEY" in err_str.upper() or "api key" in err_str.lower() or "invalid" in err_str.lower():
            return {
                "reply": None,
                "disclaimer": None,
                "error": "Invalid or missing Gemini API key. Please check GEMINI_API_KEY in backend/.env."
            }
        return {
            "reply": None,
            "disclaimer": None,
            "error": f"AI service temporarily unavailable: {err_str}"
        }
