import requests
from openai import OpenAI
from typing import List, Dict
from datetime import datetime
import re
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

class CompanyPipeline:
    def __init__(self, openai_key: str, alias_dict: Dict[str, str] = None):
        self.openai_key = openai_key
        self.alias_dict = alias_dict or {}
        self.client = OpenAI(api_key=self.openai_key)

    def resolve_alias(self, name: str) -> str:
        return self.alias_dict.get(name, name)

    def search_company_profile(self, query_name: str) -> str:
        url = "http://localhost:4000/search"
        params = {
            "q": f"{query_name} 公司簡介 經營項目 產品 上下游",
            "format": "json",
            "language": "zh",
            "sites": "zh.wikipedia.org ,104.com.tw, businessweekly.com.tw"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            results = response.json().get("results", [])

            combined_text = ""
            for res in results:
                snippet = res.get("content") or res.get("title") or ""
                combined_text += snippet + "\n"
            return combined_text.strip()

        except Exception as e:
            print(f"⚠️ 查詢公司簡介失敗：{e}")
            return ""

    def search_company_news(self, query_name: str, num_articles: int = 10) -> list:
        url = "http://localhost:4000/search"
        params = {
            "q": f"{query_name} 相關新聞",
            "format": "json",
            "language": "zh",
            "categories": "news"
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            results = response.json()
            return [{
                "title": r.get("title", ""),
                "content": r.get("content", r.get("url", "")),
                "published": r.get("published", ""),
                "url": r.get("url", "")
            } for r in results.get("results", [])]
        except Exception as e:
            print(f"⚠️ 本地 Perplexica 查詢錯誤：{e}")
            return []
        
    def summarize_profile_info(self, profile_text: str) -> Dict[str, List[str]]:
        """
        使用 OpenAI 摘要公司經營項目，萃取產品、技術與上下游合作對象。
        """
        prompt = (
            "以下是某公司在新聞與網頁上的經營項目與產品資訊描述，請根據內容產出：\n"
            "1. 三項主要產品\n"
            "2. 兩項關鍵技術\n"
            "3. 三個可能的上下游合作對象\n"
            "請以列表方式列出，使用繁體中文。\n\n"
            f"{profile_text}"
        )

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            result_text = response.choices[0].message.content.strip()

            # 嘗試使用正則表達式來萃取項目
            result = {
                "產品": re.findall(r"(?:產品|一)[\s:：\-]*([^\n]+)", result_text),
                "技術": re.findall(r"(?:技術|二)[\s:：\-]*([^\n]+)", result_text),
                "上下游": re.findall(r"(?:合作對象|三)[\s:：\-]*([^\n]+)", result_text),
            }

            return result
        except Exception as e:
            print(f"⚠️ OpenAI 摘要公司資料失敗：{e}")
            return {"產品": [], "技術": [], "上下游": []}

    def summarize_with_openai(self, content: str) -> Dict[str, str]:
        prompt = f"以下是一篇關於某家公司的新聞，請用繁體中文產出：\n1. 三句話摘要；\n2. 是否可能影響該公司股價（是/否 + 理由）：\n\n{content}"
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        summary = response.choices[0].message.content
        lines = summary.strip().split("\n")
        result = {"摘要": "", "重大性": ""}
        for line in lines:
            if "摘要" in line:
                result["摘要"] += line + "\n"
            elif "影響" in line or "是" in line or "否" in line:
                result["重大性"] = line
        return result
    
    def infer_supply_chain_role(self, summary_info: Dict[str, List[str]]) -> str:
        """
        根據產品、技術、上下游對象推論供應鏈角色。
        """
        role_keywords = {
            "上游（IC設計/製造）": ["IC", "晶圓", "封裝", "半導體製程", "ASIC", "晶片", "EDA", "光罩","AI 加速卡"],
            "中游（模組/組裝）": ["模組", "PCB", "散熱", "封裝模組", "控制器", "電源管理", "組裝"],
            "下游（品牌/應用）": ["終端產品", "品牌", "筆電", "手機", "資料中心", "車用", "伺服器"],
            "通路或整合商": ["代理", "經銷", "整合", "ODM", "OEM"]
        }

        combined_text = " ".join(summary_info.get("產品", []) + summary_info.get("技術", []) + summary_info.get("上下游", []))

        # 關鍵字簡易判斷
        role_scores = {role: sum(kw in combined_text for kw in kws) for role, kws in role_keywords.items()}
        sorted_roles = sorted(role_scores.items(), key=lambda x: x[1], reverse=True)

        if sorted_roles[0][1] == 0:
            # 若無法明確判斷，改用 LLM 幫忙補推論
            prompt = (
                "以下是某家公司提供的產品、技術與上下游合作對象資訊，"
                "請推論該公司在供應鏈中最可能的角色（上游、中游、下游、通路/整合商）：\n\n"
                f"{combined_text}\n\n"
                "請直接回覆一種角色，並加一句理由。"
            )
            try:
                response = self.client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"⚠️ OpenAI 判斷供應鏈角色失敗：{e}")
                return "未知"
        else:
            # 回傳關鍵字命中最高者
            return f"{sorted_roles[0][0]}（依關鍵詞推論）"

    def classify_industry(self, combined_text: str) -> str:
        from sentence_transformers import SentenceTransformer, util

        industry_keywords = {
            "AI 伺服器": ["GPU", "AI 加速卡", "資料中心", "液冷散熱", "邊緣運算","ASIC","晶片"],
            "電動車": ["電池", "充電樁", "電機", "電驅", "動力模組"],
            "人形機器人": ["伺服器驅動器", "機器視覺", "人機協作", "SLAM", "AI 運動控制"],
            "光電產業": ["面板", "光學", "投影", "光學雷達"],
            "太陽能發電產業": ["太陽能模組", "矽晶圓", "逆變器"],
            "汽油車用零組件": ["缸體", "曲軸", "汽缸", "排氣管", "油壓"],
            "營建業、建商": ["營建工程", "建案", "建築師", "土地開發"],
            "工具機": ["CNC", "切削", "鑽孔", "加工中心", "自動化機台"],
            "半導體": ["晶圓", "IC", "製程", "光罩", "封裝測試"],
            "被動元件": ["電容", "電阻", "電感", "MLCC"],
            "電腦相關電子零組件": ["主機板", "散熱模組", "滑鼠", "鍵盤", "SSD"],
            "手機電子零組件": ["觸控面板", "螢幕", "指紋辨識", "相機模組"]
        }

        model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
        input_vec = model.encode(combined_text, convert_to_tensor=True)
        scores = {}
        for industry, keywords in industry_keywords.items():
            keywords_str = " ".join(keywords)
            kw_vec = model.encode(keywords_str, convert_to_tensor=True)
            sim = util.cos_sim(input_vec, kw_vec).item()
            scores[industry] = sim

        best_match = max(scores.items(), key=lambda x: x[1])
        return f"{best_match[0]}（相似度 {best_match[1]:.4f}）"

    def run(self, company_name: str) -> Dict:
        print(f"🧾 原始輸入名稱：{company_name}")
        query_name = self.resolve_alias(company_name)
        print(f"🔍 使用別名/查詢詞：{query_name}")

        # 查公司介紹文字（經營項目 + 上下游）
        profile_text = self.search_company_profile(query_name)
        print(f"📘 公司基本資料擷取長度：{len(profile_text)}")

        # 查新聞
        news_list = self.search_company_news(query_name)
        all_news_text = "\n".join([n.get("content", "") for n in news_list])

        # 分類產業（混合資料源）
        all_content = profile_text + "\n" + "\n".join([n.get("content", "") for n in news_list])
        industry = self.classify_industry(all_content)

        profile_info = self.search_company_profile(query_name)
        profile_summary = self.summarize_profile_info(profile_info)
        role = self.infer_supply_chain_role(profile_summary)
        print(f"📘 透過搜尋的公司資料來公司產業地位推論：{role}")
        
        
        # 新聞摘要 + 評分排序
        summarized_news = []
        for n in news_list:
            title = n.get("title")
            content = n.get("content")
            date = n.get("published", "")
            url = n.get("url")
            if not content:
                continue
            result = self.summarize_with_openai(content)
            summarized_news.append({
                "標題": title,
                "摘要": result["摘要"].strip(),
                "重大性": result["重大性"],
                "日期": date,
                "來源": url,
                "全文": content[:300] + "..."
            })

        # 依重大性排序（先列出有「是 + 理由」的）
        sorted_news = sorted(summarized_news, key=lambda x: ("是" not in x["重大性"], x["日期"]), reverse=False)

        return {
            "公司名稱": company_name,
            "實際查詢名稱": query_name,
            "所屬產業分類": industry,
            "供應鏈角色": role,
            "經營摘要": profile_summary,
            "重要新聞摘要列表": sorted_news
                }
