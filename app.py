import streamlit as st
import torch
import numpy as np
import pandas as pd
from PIL import Image
import torchvision.transforms as T

st.set_page_config(page_title="Irfan Locator", layout="wide")
st.title(" Localisateur Visuel - Cité Al Irfan")

@st.cache_resource
def load_model():
    model = torch.hub.load('facebookresearch/dinov2', 'dinov2_vits14')
    model.eval()
    return model

@st.cache_data
def load_data():
    features = np.load('irfan_features.npy', allow_pickle=True)
    names = np.load('image_names.npy', allow_pickle=True)
    df = pd.read_csv('irfan_locations.csv')
    return features, names, df

try:
    model = load_model()
    features, names, df = load_data()
    st.success(" Système Prêt")
except Exception as e:
    st.error(f"Erreur : {e}")

uploaded_file = st.file_uploader("Photo...", type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert('RGB')
    st.image(image, width=300)
    
    with st.spinner('Recherche...'):
        transform = T.Compose([
            T.Resize(224), T.CenterCrop(224), T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        img_t = transform(image).unsqueeze(0)
        
        with torch.no_grad():
            query_feat = model(img_t).cpu().numpy().flatten().astype(np.float32)
        
        distances = []
        for f in features:
            f_clean = np.array(f).flatten().astype(np.float32)
            if f_clean.shape == query_feat.shape:
                dist = np.linalg.norm(f_clean - query_feat)
                distances.append(dist)
            else:
                distances.append(float('inf')) 
        
        best_match_idx = np.argmin(distances)
        matched_img_name = names[best_match_idx]
        
        location = df[df['image_id'] == matched_img_name].iloc[0]
        lat = location['latitude']
        lon = location['longitude']
        
        st.info(f" Coordonnées : {lat}, {lon}")
        
        google_maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        st.link_button(" Google Maps", google_maps_url, type="primary")
        
        map_df = pd.DataFrame({'lat': [lat], 'lon': [lon]})
        st.map(map_df)
