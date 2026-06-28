import os

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

from langchain_huggingface import HuggingFaceEmbeddings


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL_YOLU = os.path.join(
    BASE_DIR,
    "modeller",
    "intfloat_multilingual-e5-small"
)


def embedding_modelini_getir():
    model_kwargs = {
        "device": "cpu",
        "local_files_only": True
    }

    encode_kwargs = {
        "normalize_embeddings": True
    }

    print("[BİLGİ] Embedding modeli yerel klasörden yükleniyor...")
    print(f"[BİLGİ] Model yolu: {MODEL_YOLU}")

    if not os.path.isdir(MODEL_YOLU):
        raise FileNotFoundError(
            f"Embedding modeli bulunamadı: {MODEL_YOLU}"
        )

    model = HuggingFaceEmbeddings(
        model_name=MODEL_YOLU,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )

    return model


if __name__ == "__main__":
    test_model = embedding_modelini_getir()

    if test_model:
        print("[BAŞARILI] Embedding modeli yerel klasörden yüklendi.")