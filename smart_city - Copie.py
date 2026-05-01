import streamlit as st
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

st.set_page_config(page_title="Smart City - Rabat", layout="centered")
st.title("Plateforme Smart City - Rabat")
st.subheader("Analyse des zones urbaines à risque")

def get_geotagging(exif):
    if not exif:
        return None
    geotagging = {}
    for (idx, tag) in TAGS.items():
        if tag == 'GPSInfo':
            if idx not in exif:
                return None
            for (key, val) in GPSTAGS.items():
                if key in exif[idx]:
                    geotagging[val] = exif[idx][key]
    return geotagging

uploaded_file = st.file_uploader("Charger une image (JPG/JPEG)...", type=["jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, use_container_width=True)
    
    exif_data = image._getexif()
    geodata = get_geotagging(exif_data)
    
    if geodata:
        st.success(" Coordonnées GPS extraites avec succès")
        st.json(geodata)
    else:
        st.error(" Aucune donnée de localisation trouvée")