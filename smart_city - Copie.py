import streamlit as st
import pandas as pd
from PIL import Image

st.set_page_config(page_title="Rabat Smart City", layout="centered")

st.components.v1.html("""
    <script>
    navigator.geolocation.getCurrentPosition(
        (pos) => {
            window.parent.postMessage({
                type: 'streamlit:setComponentValue',
                value: {lat: pos.coords.latitude, lon: pos.coords.longitude}
            }, '*');
        },
        (err) => { console.error(err); },
        { enableHighAccuracy: true }
    );
    </script>
""", height=0)

st.title(" Plateforme Smart City - Rabat")

uploaded_file = st.file_uploader("Étape 1: Charger une image", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file)
    img.thumbnail((800, 800)) 
    st.image(img, caption="Aperçu optimisé", use_container_width=True)

st.write("---")
st.write("### Étape 2: Localisation")
if st.button(" Cliquer ici pour valider votre Position GPS"):
    st.info("Veuillez autoriser l'accès à la position dans votre navigateur.")

if st.button(" Envoyer le Signalement"):
    if uploaded_file:
        st.success("Signalement envoyé avec succès à la commune de Rabat !")
    else:
        st.error("Veuillez d'abord charger une photo.")
