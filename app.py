import os
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File, Form
from pydantic import BaseModel
from langchain_chroma import Chroma

from embedding import embedding_modelini_getir
from llm_manager import (
    cevap_olustur,
    secimi_coz,
    arama_sorusunu_genislet,
    genel_soru_mu,
    netlestirme_olustur
)
from router import koleksiyon_sec
from memory_manager import (
    hafizaya_kaydet,
    baglam_getir,
    hafiza_temizle,
    secenekleri_kaydet,
    secenekten_soru_getir,
    secenekleri_temizle
)

try:
    from vision_manager import goruntu_sorgusunu_hazirla
    VISION_AKTIF = True
except Exception as e:
    print(f"⚠️ [GÖRÜNTÜ MODÜLÜ] vision_manager yüklenemedi: {e}")
    VISION_AKTIF = False


app = FastAPI(
    title="ServiceBuddy API",
    description="RAG + Redis + OCR destekli kullanım kılavuzu asistanı",
    version="1.0.0"
)

DB_YOLU = "./kilavuzlar.db"

embedding_model = None
db_cache = {}

# Web API stateless olduğu için aktif koleksiyonu session_id bazlı tutuyoruz.
session_koleksiyonlari = {}


class ChatRequest(BaseModel):
    session_id: str
    question: str


class ChatResponse(BaseModel):
    session_id: str
    collection: str
    answer: str


@app.on_event("startup")
def startup_event():
    global embedding_model

    print("[SİSTEM] Embedding modeli yükleniyor...")
    embedding_model = embedding_modelini_getir()
    print("[SİSTEM] ServiceBuddy API hazır.")


@app.get("/")
def root():
    return {
        "message": "ServiceBuddy API çalışıyor.",
        "docs": "http://localhost:8000/docs"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "vision_active": VISION_AKTIF
    }


@app.post("/reset/{session_id}")
def reset_session(session_id: str):
    hafiza_temizle(session_id)

    if session_id in session_koleksiyonlari:
        del session_koleksiyonlari[session_id]

    return {
        "status": "ok",
        "message": f"{session_id} oturumu temizlendi."
    }


def koleksiyon_db_getir(koleksiyon_adi):
    """
    Aynı koleksiyon tekrar tekrar yüklenmesin diye cache kullanıyoruz.
    """
    if koleksiyon_adi not in db_cache:
        db_cache[koleksiyon_adi] = Chroma(
            persist_directory=DB_YOLU,
            embedding_function=embedding_model,
            collection_name=koleksiyon_adi
        )

    return db_cache[koleksiyon_adi]


def soru_isle(session_id, soru):
    """
    Terminaldeki main1.py akışının web API versiyonu.
    """

    mevcut_koleksiyon = session_koleksiyonlari.get(session_id)

    yeni_koleksiyon = koleksiyon_sec(
        soru,
        mevcut_koleksiyon=mevcut_koleksiyon
    )

    if yeni_koleksiyon == "genel_koleksiyon":
        return {
            "collection": "genel_koleksiyon",
            "answer": (
                "Cihaz türü belirlenemedi. Lütfen çamaşır makinesi, "
                "hava nemlendirici veya robot süpürge olarak belirtin."
            )
        }

    # Cihaz değiştiyse hafızayı temizle
    if mevcut_koleksiyon is not None and yeni_koleksiyon != mevcut_koleksiyon:
        hafiza_temizle(session_id)

    session_koleksiyonlari[session_id] = yeni_koleksiyon

    gecmis_diyalog = baglam_getir(session_id)

    db = koleksiyon_db_getir(yeni_koleksiyon)

    # Kullanıcı önceki dinamik seçeneklerden 1, 2, 3, 4 seçti mi?
    secimden_gelen_soru = secenekten_soru_getir(session_id, soru)

    if secimden_gelen_soru:
        arama_sorusu = secimden_gelen_soru
        secenekleri_temizle(session_id)
    else:
        arama_sorusu = secimi_coz(
            soru,
            gecmis_diyalog,
            yeni_koleksiyon
        )

    rag_sorusu = arama_sorusunu_genislet(arama_sorusu)

    docs = db.similarity_search(rag_sorusu, k=4)

    # Genel soruysa RAG parçalarından dinamik seçenek üret
    if genel_soru_mu(soru) and not secimden_gelen_soru:
        netlestirme_metni, secenekler = netlestirme_olustur(
            soru,
            docs
        )

        if secenekler:
            secenekleri_kaydet(session_id, secenekler)

        hafizaya_kaydet(
            session_id,
            soru,
            netlestirme_metni
        )

        return {
            "collection": yeni_koleksiyon,
            "answer": netlestirme_metni
        }

    # Normal cevap üretimi
    tam_cevap = ""

    cevap_akisi = cevap_olustur(
        gecmis_diyalog,
        arama_sorusu,
        docs
    )

    for parca in cevap_akisi:
        tam_cevap += parca

    hafizaya_kaydet(
        session_id,
        arama_sorusu,
        tam_cevap
    )

    return {
        "collection": yeni_koleksiyon,
        "answer": tam_cevap
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    sonuc = soru_isle(
        session_id=request.session_id,
        soru=request.question
    )

    return ChatResponse(
        session_id=request.session_id,
        collection=sonuc["collection"],
        answer=sonuc["answer"]
    )


@app.post("/image", response_model=ChatResponse)
async def image_chat(
    session_id: str = Form(...),
    device_type: str = Form(None),
    file: UploadFile = File(...)
):
    """
    Görüntü yükleme endpointi.

    device_type alanına şunlardan biri yazılabilir:
    - camasir
    - hava
    - robot
    """

    if not VISION_AKTIF:
        return ChatResponse(
            session_id=session_id,
            collection="vision_disabled",
            answer="Görüntü işleme modülü aktif değil."
        )

    os.makedirs("uploads", exist_ok=True)

    file_ext = os.path.splitext(file.filename)[1] or ".png"
    temp_path = os.path.join("uploads", f"{uuid.uuid4()}{file_ext}")

    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        goruntu_sonucu = goruntu_sorgusunu_hazirla(
            temp_path,
            cihaz_tipi=device_type
        )

        if not goruntu_sonucu["ocr_text"]:
            return ChatResponse(
                session_id=session_id,
                collection="ocr",
                answer="Görüntüden anlamlı metin okunamadı."
            )

        soru = goruntu_sonucu["query"]

        sonuc = soru_isle(
            session_id=session_id,
            soru=soru
        )

        return ChatResponse(
            session_id=session_id,
            collection=sonuc["collection"],
            answer=sonuc["answer"]
        )

    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass