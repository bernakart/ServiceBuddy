import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")


def openai_aktif_mi() -> bool:
    return bool(OPENAI_API_KEY)


def openai_yanit_uret(sistem_mesaji: str, kullanici_mesaji: str) -> str:
    if not openai_aktif_mi():
        raise RuntimeError("OPENAI_API_KEY bulunamadı. .env dosyasını kontrol et.")

    client = OpenAI(api_key=OPENAI_API_KEY)

    response = client.responses.create(
        model=OPENAI_MODEL,
        instructions=sistem_mesaji,
        input=kullanici_mesaji,
        max_output_tokens=700
    )

    return response.output_text.strip()