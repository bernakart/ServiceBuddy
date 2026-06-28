from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"
LOCAL_PATH = "./modeller/intfloat_multilingual-e5-small"

print("Embedding modeli indiriliyor...")
model = SentenceTransformer(MODEL_NAME)
model.save(LOCAL_PATH)
print(f"Model başarıyla kaydedildi: {LOCAL_PATH}")