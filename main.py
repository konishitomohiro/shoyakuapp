import streamlit as st
import pandas as pd
import json
import requests
from rdkit import Chem
from rdkit.Chem import Draw

# ページ設定
st.set_page_config(layout="wide", page_title="生薬ビジュアル暗記アプリ", page_icon="🌿")

st.title("🌿 生薬・構造式ビジュアル暗記アプリ")
st.markdown("生薬名から、主要成分の構造式（RDKitで描画）と、起源植物の写真を確認します。")

# --- データ読み込み ---
@st.cache_data
def load_data():
    try:
        return pd.read_csv("structures_by_生薬名_tagged.csv")
    except FileNotFoundError:
        st.error("エラー: 'structures_by_生薬名_tagged.csv' が同じフォルダに見つかりません。")
        return pd.DataFrame()

df = load_data()

# --- Web APIからデータを取得する関数 ---
@st.cache_data
def get_smiles_from_pubchem(cid):
    if not cid: return None
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/property/CanonicalSMILES/TXT"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            return res.text.strip()
    except:
        pass
    return None

@st.cache_data
def get_wikipedia_image(query):
    """Wikipediaから検索語句に関連する代表画像を取得"""
    url = f"https://ja.wikipedia.org/w/api.php?action=query&titles={query}&prop=pageimages&format=json&pithumbsize=500"
    try:
        res = requests.get(url, timeout=5).json()
        pages = res['query']['pages']
        for page_id in pages:
            if 'thumbnail' in pages[page_id]:
                return pages[page_id]['thumbnail']['source']
    except:
        pass
    return None

# --- UI部分 ---
if not df.empty:
    # サイドバーで生薬を選択
    syoyaku_list = df['生薬名'].tolist()
    selected_syoyaku = st.sidebar.selectbox("📖 学習する生薬を選んでください", syoyaku_list)
    
    # 選択された生薬のデータを抽出
    row = df[df['生薬名'] == selected_syoyaku].iloc[0]
    st.header(f"💊 {selected_syoyaku}")
    
    # レイアウト作成（左：写真、右：成分と構造式）
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📸 関連写真 (Wikipediaより自動取得)")
        # 検索用のキーワード（生薬名から「末」などを除外）
        search_keyword = selected_syoyaku.replace("（末）", "").replace("コン", "")
        img_url = get_wikipedia_image(search_keyword)
        
        if img_url:
            st.image(img_url, caption=f"{search_keyword} の関連画像", use_container_width=True)
        else:
            st.info("写真が見つかりませんでした。別のキーワードで検索するか、手元の図鑑を参照してください。")

    with col2:
        st.subheader("🔬 主要成分と構造式")
        try:
            structs = json.loads(row['structures_json'])
            for s in structs:
                comp_name = s.get('構造対象', '不明')
                cid = s.get('PubChem CID', '')
                classes = ", ".join(s.get('class_tags', []))
                
                with st.expander(f"🧪 {comp_name} ({classes})", expanded=True):
                    if cid:
                        smiles = get_smiles_from_pubchem(cid)
                        if smiles:
                            # RDKitでSMILESから画像を生成
                            mol = Chem.MolFromSmiles(smiles)
                            if mol:
                                img = Draw.MolToImage(mol, size=(300, 300))
                                st.image(img, caption=f"IUPAC SMILES: {smiles[:30]}...")
                            else:
                                st.warning("構造式の描画に失敗しました。")
                        else:
                            st.warning("PubChemからSMILESを取得できませんでした。")
                    else:
                        st.info("PubChem CIDが登録されていないため、構造式を表示できません。")
        except Exception as e:
            st.error(f"データの解析エラー: {e}")