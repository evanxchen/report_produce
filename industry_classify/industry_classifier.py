# 建立 industry_classifier.py 模組，用於產業鏈分類
code = '''
from sentence_transformers import SentenceTransformer, util
import pandas as pd

# 預設產業鏈關鍵字資料庫
DEFAULT_INDUSTRY_DB = {
    "AI伺服器": "AI加速卡、GPU模組、機架伺服器、液冷散熱、資料中心、推論伺服器、高階HPC伺服器、AI訓練平台、NVLink、高速交換器",
    "電動車": "電池模組、動力電池、馬達控制器、電動驅動系統、電動車充電站、車載充電機、電動車逆變器、自駕車感測器、電池管理系統",
    "人形機器人": "關節模組、伺服驅動、3D視覺、語音互動、仿生結構、AI運動規劃、機器學習控制、機械手臂、人形感測器",
    "光電產業": "面板模組、感測器模組、光學鍍膜、液晶材料、OLED、Micro LED、顯示驅動IC、背光模組、光學透鏡",
    "太陽能發電產業": "矽晶圓、太陽能電池片、模組封裝、逆變器、太陽能電站、光伏系統、電力轉換、儲能設備",
    "汽油車用零組件": "引擎、燃油噴射系統、變速箱、汽車壓縮機、機油濾芯、曲軸、排氣系統、內燃機、冷卻系統",
    "營建業與建商": "建案開發、土地開發、營建工程、住宅建案、建築材料、預售屋、市地重劃、工程承包商、工地主任",
    "工具機": "CNC加工中心、車銑複合機、線切割、五軸加工、主軸、滾珠螺桿、自動換刀系統、工件夾具",
    "半導體": "晶圓製造、封裝測試、光罩、蝕刻設備、曝光機、晶圓代工、前段製程、後段製程、IC設計、EUV設備",
    "被動元件": "電容、電感、電阻、濾波器、晶體諧振器、積層陶瓷電容（MLCC）、繞線電感、保險絲",
    "電腦相關電子零組件": "主機板、顯示卡、記憶體模組、散熱器、電源供應器、機殼、儲存裝置、USB介面卡、顯示器",
    "手機電子零組件": "攝像頭模組、螢幕面板、觸控模組、電池模組、無線充電、天線模組、震動馬達、感測器IC"
}

class IndustryClassifier:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", ground_truth_db: dict = None):
        self.model = SentenceTransformer(model_name)
        self.ground_truth_db = ground_truth_db if ground_truth_db else DEFAULT_INDUSTRY_DB
        self._encode_ground_truth()

    def _encode_ground_truth(self):
        self.ground_truth_embeddings = {
            k: self.model.encode(v, convert_to_tensor=True)
            for k, v in self.ground_truth_db.items()
        }

    def classify(self, input_text: str, threshold: float = 0.5):
        query_embedding = self.model.encode(input_text, convert_to_tensor=True)
        scores = {
            k: float(util.cos_sim(query_embedding, emb))
            for k, emb in self.ground_truth_embeddings.items()
        }
        top_industry = max(scores.items(), key=lambda x: x[1])
        if top_industry[1] >= threshold:
            return top_industry[0], round(top_industry[1], 4)
        return "未分類", 0.0

    def classify_batch(self, texts: list, threshold: float = 0.5):
        return [self.classify(t, threshold) for t in texts]
'''

with open("industry_classifier.py", "w", encoding="utf-8") as f:
    f.write(code)
