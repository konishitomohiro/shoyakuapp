from pathlib import Path
import json

import pandas as pd
import requests
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "structures_by_生薬名_tagged.csv"

# ページ設定
st.set_page_config(layout="wide", page_title="生薬ビジュアル暗記アプリ", page_icon="🌿")

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }
        .app-shell {
            background: linear-gradient(180deg, rgba(245, 250, 244, 0.95), rgba(255, 255, 255, 1));
            border: 1px solid rgba(20, 60, 30, 0.08);
            border-radius: 18px;
            padding: 1.25rem 1.4rem;
            box-shadow: 0 18px 45px rgba(20, 40, 20, 0.08);
        }
        .muted-note {
            color: #5f6c66;
            font-size: 0.95rem;
        }
        .compound-card {
            border: 1px solid rgba(30, 60, 40, 0.12);
            border-radius: 14px;
            padding: 1rem 1rem 0.5rem 1rem;
            background: rgba(255, 255, 255, 0.9);
            margin-bottom: 0.75rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🌿 生薬・構造式ビジュアル暗記アプリ")
st.markdown("生薬名から、主要成分の構造式と起源植物の写真を確認します。")

# --- データ読み込み ---
@st.cache_data
def load_data():
    try:
        return pd.read_csv(DATA_PATH)
    except FileNotFoundError:
        st.error("エラー: 'structures_by_生薬名_tagged.csv' がアプリ本体と同じフォルダに見つかりません。")
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
def get_pubchem_structure_image_url(cid):
    if not cid:
        return None
    return f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/PNG?image_size=large"

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

# --- 生薬名から起源植物の「学名（ラテン名）」への変換辞書 ---
# 学名を使うことで、Wikipediaから最も正確に植物の画像を引っ張れます
SCIENTIFIC_NAME_MAPPING = {
    "べラドンナコン": "Atropa belladonna", 
    "アロエ（末）": "Aloe vera", # または Aloe ferox
    "ウイキョウ（末）": "Foeniculum vulgare",
    "ウワウルシ": "Arctostaphylos uva-ursi",
    "オウゴン（末）": "Scutellaria baicalensis",
    "オウバク（末）": "Phellodendron amurense",
    "カッコン": "Pueraria lobata",
    "センナ（末）": "Senna alexandrina",
    "マオウ": "Ephedra sinica",
    "オウレン（末）": "Coptis japonica",
    "ジギタリス（末）": "Digitalis purpurea"
}

# --- UI部分 ---
if not df.empty:
    st.markdown('<div class="app-shell">', unsafe_allow_html=True)

    # サイドバーで生薬を選択
    syoyaku_list = df['生薬名'].tolist()
    selected_syoyaku = st.sidebar.selectbox("📖 学習する生薬を選んでください", syoyaku_list)
    st.sidebar.caption(f"登録生薬数: {len(syoyaku_list)}")
    
    # 選択された生薬のデータを抽出
    row = df[df['生薬名'] == selected_syoyaku].iloc[0]
    st.header(f"💊 {selected_syoyaku}")
    st.markdown("<div class='muted-note'>PubChem の CID を使って、構造式画像を直接表示します。Cloud 上でも依存関係が軽くなる構成です。</div>", unsafe_allow_html=True)
    
    # レイアウト作成（左：写真、右：成分と構造式）
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("📸 起源植物 (Wikipediaより自動取得)")

        # 辞書に学名があればそれを検索キーワードにし、なければ生薬名をそのまま使う
        if selected_syoyaku in SCIENTIFIC_NAME_MAPPING:
            search_keyword = SCIENTIFIC_NAME_MAPPING[selected_syoyaku]
            display_name = f"{selected_syoyaku} ({search_keyword})"
        else:
            search_keyword = selected_syoyaku.replace("（末）", "").replace("コン", "")
            display_name = search_keyword

        img_url = get_wikipedia_image(search_keyword)

        if img_url:
            st.image(img_url, caption=display_name, use_container_width=True)
        else:
            st.info(f"「{display_name}」の写真が見つかりませんでした。")
    with col2:
        st.subheader("🔬 主要成分と構造式")
        try:
            structs = json.loads(row['structures_json'])
            for s in structs:
                comp_name = s.get('構造対象', '不明')
                cid = s.get('PubChem CID', '')
                classes = ", ".join(s.get('class_tags', []))
                
                with st.container():
                    st.markdown('<div class="compound-card">', unsafe_allow_html=True)
                    st.markdown(f"**🧪 {comp_name}**  ")
                    if classes:
                        st.caption(classes)

                    if cid:
                        structure_img_url = get_pubchem_structure_image_url(cid)
                        st.image(structure_img_url, use_container_width=True)
                        smiles = get_smiles_from_pubchem(cid)
                        if smiles:
                            st.caption(f"SMILES: {smiles}")
                        st.link_button("PubChem で開く", s.get('PubChem URL', f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}"))
                    else:
                        st.info("PubChem CIDが登録されていないため、構造式を表示できません。")
                    st.markdown('</div>', unsafe_allow_html=True)
        except Exception as e:
            st.error(f"データの解析エラー: {e}")

    st.markdown("</div>", unsafe_allow_html=True)
else:
    st.warning("表示できるデータがありません。CSV ファイルの配置と内容を確認してください。")