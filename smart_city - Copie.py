import streamlit as st
from PIL import Image
from streamlit_js_eval import get_geolocation # type: ignore

st.set_page_config(page_title="Rabat Smart City", layout="centered")

if "location" not in st.session_state:
    st.session_state.location = None

st.title(" Plateforme Smart City - Rabat")


st.subheader("Étape 1 : Charger une image")
uploaded_file = st.file_uploader("Sélectionnez une photo", type=["jpg", "jpeg", "png"])

if uploaded_file:
    img = Image.open(uploaded_file)
    img.thumbnail((800, 800))
    st.image(img, caption="Aperçu de la photo", use_container_width=True)

st.write("---")


st.subheader("Étape 2 : Localisation GPS")

if st.button(" Obtenir ma position GPS"):
    location = get_geolocation()  
    if location:
        lat = location["coords"]["latitude"]
        lon = location["coords"]["longitude"]
        st.session_state.location = {"lat": lat, "lon": lon}

if st.session_state.location:
    loc = st.session_state.location
    st.success(f" Position : {loc['lat']:.6f}, {loc['lon']:.6f}")
    st.map({"lat": [loc["lat"]], "lon": [loc["lon"]]})
else:
    st.info("Position GPS non encore enregistrée.")

st.write("---")


st.subheader("Étape 3 : Envoyer le signalement")

description = st.text_area("Description du problème", 
                            placeholder="Ex: Nid-de-poule, éclairage défaillant...")

if st.button(" Envoyer le Signalement"):
    if not uploaded_file:
        st.error(" Veuillez charger une photo.")
    elif not st.session_state.location:
        st.error(" Veuillez confirmer votre position GPS.")
    else:
        st.success(" Signalement envoyé avec succès à la commune de Rabat!")
        st.balloons()
