from fastapi import FastAPI
from pydantic import BaseModel
import g4f
import re

app = FastAPI()

class MovieRequest(BaseModel):
    liked_titles: list

def extract_titles(text):
    matches = re.findall(r"^\s*(?:\d+|[۰-۹]+)[\.\-ـ]?\s*(.+)$", text, re.MULTILINE)
    titles = []

    for line in matches:
        line = line.strip()
        eng_title = re.search(r"\(([^()]+)\)", line)
        if eng_title:
            titles.append(eng_title.group(1))
        elif re.search(r"[a-zA-Z]", line) and len(line.split()) >= 2:
            titles.append(line)

    return titles[:5]

# ✅ لیست providerهایی که ترجیح می‌دیم استفاده کنیم
preferred_providers = [
    g4f.Provider.Chatgpt4o,
    g4f.Provider.ChatGpt,
    g4f.Provider.FreeGpt,
    g4f.Provider.MyShell,
    g4f.Provider.Acytoo,
    g4f.Provider.GetGpt,
]

# ✅ لیست مدل‌های deepseek با اولویت بالا
deepseek_models = [
    "deepseek-chat",
    "deepseek-v3",
    "deepseek-r1"
]

@app.on_event("startup")
def show_available_models_and_providers():
    print("🔍 Available models in g4f.models:")
    for attr in dir(g4f.models):
        if not attr.startswith("__"):
            print(f" - {attr} = {getattr(g4f.models, attr)}")

    print("\n🎯 Providers we’ll try:")
    for p in preferred_providers:
        print(f" - {p.__name__}")

@app.post("/recommend")
async def recommend_movies(req: MovieRequest):
    liked = ", ".join(req.liked_titles)

    prompt = f"""
    من کاربری هستم که از فیلم‌ها و سریال‌های زیر خیلی خوشم اومده:
    {liked}
    لطفاً فقط ۵ فیلم یا سریال بهم پیشنهاد بده که حس و فضای مشابهی داشته باشن. فقط اسم‌ها رو با عدد بنویس.
    مثال:
    1. اسم فیلم اول
    2. اسم فیلم دوم
    ...
    """

    print("🟡 Prompt sent to model:\n", prompt)

    # ✅ اول تست deepseek مدل‌ها
    for model_name in deepseek_models:
        try:
            print(f"🧪 Trying DeepSeek model: {model_name}")
            response = g4f.ChatCompletion.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": "تو یک پیشنهاددهنده حرفه‌ای فیلم هستی."},
                    {"role": "user", "content": prompt}
                ]
            )

            if hasattr(response, '__iter__') and not isinstance(response, str):
                response = ''.join(response)

            print("✅ Success with DeepSeek model:", model_name)
            print("📦 Raw response repr:\n", repr(response))

            titles = extract_titles(response)
            if titles:
                return {
                    "provider": "DeepSeek",
                    "model": model_name,
                    "recommendations_raw": response,
                    "titles": titles,
                    "message": "پیشنهادات با موفقیت از DeepSeek استخراج شدند."
                }

        except Exception as e:
            print(f"❌ DeepSeek model {model_name} failed:", e)

    # ❌ اگه DeepSeekها جواب ندادن، بریم سراغ providerها
    for provider in preferred_providers:
        try:
            print(f"🧪 Trying provider: {provider.__name__}")
            response = g4f.ChatCompletion.create(
                model=g4f.models.default,
                messages=[
                    {"role": "system", "content": "تو یک پیشنهاددهنده حرفه‌ای فیلم هستی."},
                    {"role": "user", "content": prompt}
                ],
                provider=provider
            )

            if hasattr(response, '__iter__') and not isinstance(response, str):
                response = ''.join(response)

            print("✅ Success with provider:", provider.__name__)
            print("📦 Raw response repr:\n", repr(response))

            titles = extract_titles(response)
            if titles:
                return {
                    "provider": provider.__name__,
                    "recommendations_raw": response,
                    "titles": titles,
                    "message": "پیشنهادات با موفقیت استخراج شدند."
                }

        except Exception as e:
            print(f"❌ Failed with provider {provider.__name__}:", e)

    return {
        "error": "هیچ مدلی یا providerی پاسخ نداد یا خروجی قابل استفاده نبود.",
        "message": "لطفاً اتصال اینترنت و VPN رو بررسی کن یا بعداً امتحان کن."
    }
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("Main:app", host="0.0.0.0", port=port)

