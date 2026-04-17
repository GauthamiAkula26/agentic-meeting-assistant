from __future__ import annotations

from openai import OpenAI


def llm_answer(question: str, context: str, api_key: str) -> str:
    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a meeting intelligence agent. "
                        "Answer only from the provided context. "
                        "If the answer is not supported, say the context is insufficient."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Question:\n{question}\n\nMeeting context:\n{context}",
                },
            ],
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        return f"OpenAI answer failed: {e}"
