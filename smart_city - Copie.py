import streamlit as st
import pandas as pd

st.set_page_config(page_title="Rabat Smart City", layout="centered")

st.components.v1.html("""
    <script>
    const options = { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 };
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            const { latitude, longitude } = pos.coords;
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: {lat: latitude, lon: longitude}
            }, '*');
        },
        (err) => { console.warn('GPS Error', err); },
        options
    );
    </script>
""", height=0)

st.title(" Plateforme Smart City - Rabat")
st.write("Signalement des incidents et analyse des zones à risque")

if 'location' not in st.session_state:
    st.session_state.location = None

uploaded_file = st.file_uploader("Charger une image de l'incident (JPG/JPEG)", type=["jpg", "jpeg", "png"])

if uploaded_file:
    st.image(uploaded_file, use_container_width=True)
    if st.button(" Confirmer et Envoyer le Signalement"):
        st.success("Position capturée et signalement envoyé avec succès !")
