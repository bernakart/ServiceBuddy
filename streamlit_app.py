import os
import uuid
import requests
import streamlit as st


API_URL = os.getenv("API_URL", "http://localhost:8000")


st.set_page_config(
    page_title="ServiceBuddy",
    page_icon="🤖",
    layout="centered"
)


# -----------------------------
# OTURUM AYARLARI
# -----------------------------
if "session_id" not in st.session_state:
    st.session_state.session_id = f"streamlit_{uuid.uuid4().hex[:8]}"

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "Teknik sorunuzu yazabilirsiniz. "
                "İsterseniz kılavuz veya cihaz ekranı görseli de yükleyebilirsiniz."
            )
        }
    ]


# -----------------------------
# YARDIMCI FONKSİYONLAR
# -----------------------------
def chat_gonder(soru):
    """
    Kullanıcının metin sorusunu FastAPI /chat endpointine gönderir.
    """
    payload = {
        "session_id": st.session_state.session_id,
        "question": soru
    }

    response = requests.post(
        f"{API_URL}/chat",
        json=payload,
        timeout=180
    )

    response.raise_for_status()
    return response.json()


def gorsel_gonder(uploaded_file):
    """
    Kullanıcının yüklediği görseli FastAPI /image endpointine gönderir.
    Cihaz türü arayüzden seçilmez; backend router kendisi anlamaya çalışır.
    """
    files = {
        "file": (
            uploaded_file.name,
            uploaded_file.getvalue(),
            uploaded_file.type
        )
    }

    data = {
        "session_id": st.session_state.session_id
    }

    response = requests.post(
        f"{API_URL}/image",
        data=data,
        files=files,
        timeout=180
    )

    response.raise_for_status()
    return response.json()


def hafizayi_temizle():
    """
    Redis oturum hafızasını temizler.
    """
    response = requests.post(
        f"{API_URL}/reset/{st.session_state.session_id}",
        timeout=60
    )

    response.raise_for_status()


# -----------------------------
# ARAYÜZ
# -----------------------------
st.title("🤖 ServiceBuddy ")
st.caption("🤖 ServiceBuddy")

with st.sidebar:
    st.subheader("Sistem Bilgisi")
    st.write("Oturum ID:")
    st.code(st.session_state.session_id)

    if st.button("Hafızayı Temizle"):
        try:
            hafizayi_temizle()

            st.session_state.messages = [
                {
                    "role": "assistant",
                    "content": "Hafıza temizlendi. Yeni sorunuzu yazabilirsiniz."
                }
            ]

            st.success("Hafıza temizlendi.")
            st.rerun()

        except Exception as e:
            st.error(f"Hafıza temizlenemedi: {e}")

    st.divider()

    st.subheader("Görsel Yükleme")
    uploaded_file = st.file_uploader(
        "Cihaz ekranı veya kılavuz görseli yükleyin",
        type=["png", "jpg", "jpeg"]
    )

    if st.button("Görselden Sor"):
        if uploaded_file is None:
            st.warning("Lütfen önce bir görsel seçin.")
        else:
            st.session_state.messages.append(
                {
                    "role": "user",
                    "content": f"Görsel yüklendi: {uploaded_file.name}"
                }
            )

            with st.spinner("Görsel OCR ile analiz ediliyor..."):
                try:
                    result = gorsel_gonder(uploaded_file)

                    answer = result.get("answer", "Cevap alınamadı.")
                    collection = result.get("collection", "bilinmiyor")

                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": f"{answer}\n\nSeçilen koleksiyon: {collection}"
                        }
                    )

                    st.rerun()

                except Exception as e:
                    st.session_state.messages.append(
                        {
                            "role": "assistant",
                            "content": f"Görüntü işleme sırasında hata oluştu: {e}"
                        }
                    )

                    st.rerun()


# -----------------------------
# MESAJLARI GÖSTER
# -----------------------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])


# -----------------------------
# METİN SORUSU
# -----------------------------
prompt = st.chat_input("Sorununuzu yazın... ")

if prompt:
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Teknik dökümanlar analiz ediliyor..."):
            try:
                result = chat_gonder(prompt)

                answer = result.get("answer", "Cevap alınamadı.")
                collection = result.get("collection", "bilinmiyor")

                st.write(answer)

                with st.expander("Teknik detay"):
                    st.write(f"Seçilen koleksiyon: `{collection}`")
                    st.write(f"Oturum: `{st.session_state.session_id}`")

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer
                    }
                )

            except Exception as e:
                hata_mesaji = f"Sistem hatası oluştu: {e}"
                st.error(hata_mesaji)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": hata_mesaji
                    }
                )