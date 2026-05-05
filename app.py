import streamlit as st
import torch
import numpy as np
import pandas as pd
from PIL import Image
import torchvision.transforms as T
import os

st.set_page_config(page_title="Irfan Visual Locator", layout="wide")

st.title("📍 Localisateur Visuel - Cité Al Irfan")
st.write("Système de positionnement par IA (DINOv2)")

@st.cache_resource
def load_model():
    # تحميل الموديل وضمان وضعه على الـ CPU للعمل في Streamlit Cloud
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
    st.success("✅ Base de données opérationnelle")
except Exception as e:
    st.error(f"Erreur technique : {e}")

uploaded_file = st.file_uploader("Télécharger une photo de la ville...", type=['jpg', 'jpeg', 'png'])

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert('RGB')
    col1, col2 = st.columns(2)
    
    with col1:
        st.image(image, caption="Votre photo", use_container_width=True)
    
    with st.spinner('Analyse spatiale en cours...'):
        transform = T.Compose([
            T.Resize(224),
            T.CenterCrop(224),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
        img_t = transform(image).unsqueeze(0)
        
        with torch.no_grad():
            # استخراج الميزات وتحويلها قسرياً لمتجه أحادي البعد
            query_feat = model(img_t).cpu().numpy().reshape(-1)
        
        # تحويل قاعدة البيانات لمصفوفة ثنائية الأبعاد نظيفة (N, Features)
        # هذا السطر هو الحل النهائي لمشكلة ValueError
        db_features = np.array([f.flatten() for f in features])
        
        # حساب المسافة الإقليدية
        distances = np.linalg.norm(db_features - query_feat, axis=1)
        best_match_idx = np.argmin(distances)
        
        matched_img_name = names[best_match_idx]
        location = df[df['image_id'] == matched_img_name].iloc[0]
        lat, lon = location['latitude'], location['longitude']
        
    with col2:
        st.subheader("🎯 Localisation Trouvée")
        st.metric("Latitude", lat)
        st.metric("Longitude", lon)
        
        maps_url = f"https://www.google.com/maps?q={lat},{lon}"
        st.markdown(f"### [🌍 Voir sur Google Maps]({maps_url})")
        
        map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
        st.map(map_data)
