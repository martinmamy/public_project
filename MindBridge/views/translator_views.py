import json
import requests
from django.conf import settings
from django.http import JsonResponse
from django.views import View


class TranslateContentView(View):

    def post(self, request):

        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid json"}, status=400)

        text = data.get("text", "").strip()

        if not text:
            return JsonResponse({"translated": ""})

        # 🌍 AUTO DETECT LANGUAGE FROM HEADER
        accept_language = request.headers.get("Accept-Language", "en")
        target_language = accept_language.split(",")[0].split("-")[0]

        # fallback safety
        if not target_language:
            target_language = "en"

        prompt = (
            f"Translate this text into {target_language}.\n\n"
            f"{text}\n\n"
            "Return ONLY translated text."
        )

        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "http://127.0.0.1:8000",
                    "X-Title": "FancyLearn",
                },
                json={
                    "model": "mistralai/mistral-7b-instruct",
                    "messages": [
                        {"role": "system", "content": "You are a professional translator."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.2,
                    "max_tokens": 500
                },
                timeout=20
            )

            response.raise_for_status()
            result = response.json()

            translated = (
                result.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )

            return JsonResponse({"translated": translated})

        except Exception as e:
            return JsonResponse({
                "error": "translation_failed",
                "details": str(e)
            }, status=500)