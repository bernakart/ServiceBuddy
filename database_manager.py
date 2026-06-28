from langchain_community.vectorstores import Chroma

def veri_tabanina_kaydet(parcalar, embedding_modeli, koleksiyon_adi, db_yolu="./kilavuzlar.db"):
    
    vector_db = Chroma.from_documents(
        documents=parcalar,
        embedding=embedding_modeli,
        persist_directory=db_yolu,
        collection_name=koleksiyon_adi
    )
    return vector_db