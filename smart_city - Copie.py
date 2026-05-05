import streamlit as st
import torch # type: ignore
import numpy as np
import pandas as pd
from PIL import Image
import torchvision.transforms as T # type: ignore
import os

st.set_page_config(page_title="Irfan Visual Locator", layout="centered")

st.title("Localisateur Visuel - Cité Al Irfan")
st.write("Système de positionnement par IA (DINOv2 + AnyLoc)")

@st.cache_resource
def load_model():
    model = torch.hub.load('facebookresearch/dinov2', 'dinov2_vits14')
    model.eval()
    return model

@st.cache_data
def load_data():
    features = np.load('irfan_features.npy')
    names = np.load('image_names.npy')
    df = pd.read_csv('irfan_locations.csv')
    return features, names, df

try:
    model = load_model()
    features, names, df = load_data()
    st.success("Base de données chargée !")
except Exception as e:
    st.error(f"Erreur : {e}")

uploaded_file = st.file_uploader("Choisir une photo...", type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert('RGB')
    st.image(image, use_container_width=True)
    
    with st.spinner('Analyse...'):
        transform = T.Compose([
            T.Resize(224),
            T.CenterCrop(224),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        img_t = transform(image).unsqueeze(0)
        
        with torch.no_grad():
            query_feat = model(img_t).numpy()
        
        distances = np.linalg.norm(features - query_feat, axis=1)
        best_match_idx = np.argmin(distances)
        
        matched_img_name = names[best_match_idx]
        location = df[df['image_id'] == matched_img_name].iloc[0]
        lat, lon = location['latitude'], location['longitude']
        
        st.subheader("Résultat")
        st.info(f"Coordonnées : {lat}, {lon}")
        
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        st.markdown(f"### [ Google Maps]({maps_url})")
        
        map_df = pd.DataFrame({'lat': [lat], 'lon': [lon]})
        st.map(map_df)
