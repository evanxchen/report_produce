# 📊 Company Intelligence & Industry Summary Pipeline

這是一個整合性情報系統，能夠針對公司名稱自動完成以下流程：

1. 擷取公司相關重大新聞
2. 自動摘要、分類與重大性判斷
3. 擷取公司經營項目、產品與上下游夥伴
4. 推論其所屬產業與供應鏈角色
5. 搜尋對應的產業分析報告 PDF，進行段落摘要與五維評分
6. 可結合專利爬蟲系統以擴充文字語料

---

## 🧠 技術架構

### 🔹 搜尋與摘要模組

* **新聞與公司資訊來源**：Perplexica 搜尋引擎（自架 SearXNG）
* **語言理解與摘要**：OpenAI GPT-3.5 / GPT-4
* **向量比對**：SentenceTransformer 模型進行語意相似度計算（產業分類、供應鏈推論）

### 🔹 產業分析模組

* **PDF 爬蟲與分析器**：從 AWS S3 載入產業報告
* **段落摘要 + 五維度評分**：由 LLM 評估產業報告的成長性、競爭力、風險性、投資價值、創新力

### 🔹 專利分析模組（選用）

* **爬蟲架構**：Flask + Celery + Redis + Selenium
* **每日排程與任務分配**：Celery Beat + AWS S3 紀錄歷史任務
* **擴充文字語料**：將專利摘要作為產業與產品判別依據

---

## 📦 模組總覽與路徑

```
company_analysis_pipeline/
├── company_pipeline.py            # 主流程控制器
├── alias_dict.json                # 公司別名對照表
├── industry_classifier.py         # 向量分類模組（SentenceTransformer）
├── profile_fetcher.py             # 公司簡介與上下游擷取
├── news_summarizer.py            # GPT 摘要與重大性判斷
├── supply_chain_identifier.py    # 供應鏈角色推論
├── industry_report_analyzer/     # ⬇︎ PDF 報告處理模組
│   ├── report_parser.py          # 讀取與解析產業報告
│   ├── summarizer.py             # 段落摘要
│   └── scorer.py                 # 五維度產業評分
├── patent_module/                # ⬇︎ 專利爬蟲子模組
│   ├── app.py                    # Flask REST API
│   ├── task.py                   # Celery 任務處理器
│   ├── patent_spider.py         # Selenium 爬蟲邏輯
│   ├── s3_utils.py              # 與 AWS S3 的互動
│   └── utils/                   # 任務載入與歷史追蹤
│       ├── target_loader.py
│       └── crawl_history.py
├── requirements.txt
└── README.md
```

---

## 🧪 使用方式

### Step 1️⃣ - 安裝依賴

```
pip install -r requirements.txt
```

### Step 2️⃣ - 設定 OpenAI Key (.env 或 config)

```
OPENAI_API_KEY=your-key
```

### Step 3️⃣ - 執行主流程

```python
from company_pipeline import CompanyPipeline
pipeline = CompanyPipeline(openai_key="your-key")
result = pipeline.run("世芯")
```

---

## 📬 Sample Output

```json
{
  "公司名稱": "世芯",
  "所屬產業分類": "AI 伺服器（相似度 0.5823）",
  "供應鏈角色": "上游（IC設計/製造）（依關鍵詞推論）",
  "經營摘要": {
    "產品": [...],
    "技術": [...],
    "上下游": [...]
  },
  "重要新聞摘要列表": [
    {
      "標題": "AWS 高峰會登台！...",
      "重大性": "是，進入 AWS 供應鏈具高度影響力",
      "摘要": "世芯-KY專注於 AI/伺服器應用...",
      "來源": "https://...",
      "日期": "2025-07-31"
    },
    ...
  ],
  "產業整體評分": {
    "總分": 84,
    "總評": "成長潛力高，需注意技術競爭",
    "成長性": {"分數": 9, "說明": "AI 應用快速擴張"},
    "風險性": {"分數": 6, "說明": "競爭激烈、技術壽命短"},
    ...
  }
}
```

---

## 🤝 適用場景

* 🔍 金融單位：針對陌生公司快速建構「徵信摘要」與「新聞動向分析」
* 💼 投資研究：評估供應鏈角色、產業前景、是否具標的性
* 🧠 AI 助理應用：可搭配語音助手回應「幫我分析某某公司」
* 🧱 Hackathon：作為企業觀測與智能摘要的 MVP 系統

---

## 📬 延伸功能規劃

* PDF 報告自動搜尋與增強摘要
* S3 歷史記錄視覺化
* 支援自訂產業分類詞庫與公司評分維度
* Notion 自動推送公司摘要卡片

---

如需部署為 Web API，可搭配 FastAPI / Flask 套件擴充，或部署至 AWS Lambda + ECS Fargate。
