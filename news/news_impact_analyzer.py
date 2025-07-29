# 建立 news_impact_analyzer.py 模組檔案
code = '''
import pandas as pd
import json
import boto3
import re
import os
import hashlib

class NewsImpactAnalyzer:
    def __init__(self, company_txt_path: str, news_parquet_path: str, region="us-east-1"):
        self.company_txt_path = company_txt_path
        self.news_parquet_path = news_parquet_path
        self.region = region
        self.cache_dir = "claude_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        self.prompt_template = """
你是一位資深金融分析師，正在分析以下新聞是否會對該公司股價產生影響。
請針對「股價重大性」從 0 到 1 進行評分，並說明理由。
---
新聞內容：
{news_content}

請輸出：
1. 簡短摘要（最多 80 字）
2. 是否對股價有明顯影響（是/否）
3. 影響屬性（利多 / 利空 / 中性）
4. 重大性分數（0~1，小數點2位）
"""
        self.company_list = self._load_companies()
        self.df_news = self._load_news()
        self.company_alias_dict = self._build_alias_dict()
        self.bedrock = boto3.client("bedrock-runtime", region_name=self.region)

    def _load_companies(self):
        df_companies = pd.read_csv(self.company_txt_path)
        return df_companies['company_name'].tolist()

    def _load_news(self):
        df_news = pd.read_parquet(self.news_parquet_path)
        df_news.columns = [col.lower() for col in df_news.columns]
        if "date" in df_news.columns:
            df_news["date"] = pd.to_datetime(df_news["date"])
        else:
            df_news["date"] = pd.NaT
        if "content" not in df_news.columns:
            df_news.rename(columns={df_news.columns[0]: "content"}, inplace=True)
        return df_news

    def _build_alias_dict(self):
        base_aliases = {
            "台積電": ["台積", "TSMC", "台灣積體電路"],
            "聯發科": ["MTK", "聯發", "Mediatek"],
            "世芯-KY": ["世芯", "Alchip"]
        }
        for company in self.company_list:
            if company not in base_aliases:
                base_aliases[company] = [company]
        return base_aliases

    def _hash_content(self, text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    def _call_claude(self, prompt: str) -> str:
        response = self.bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229",
            body=json.dumps({
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
                "temperature": 0.2
            }),
            contentType="application/json",
            accept="application/json"
        )
        result = json.loads(response['body'].read())
        return result['content'][0]['text']

    def _get_cached_response(self, news_text: str) -> str:
        cache_file = os.path.join(self.cache_dir, f"{self._hash_content(news_text[:300])}.json")
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)["text"]
        prompt = self.prompt_template.format(news_content=news_text[:1200])
        result_text = self._call_claude(prompt)
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"text": result_text}, f, ensure_ascii=False)
        return result_text

    def _analyze_news(self, news_text: str) -> dict:
        output_text = self._get_cached_response(news_text)
        lines = output_text.strip().split("\\n")
        result = {
            "摘要": lines[0].split("：")[-1].strip() if len(lines) > 0 else "",
            "影響": lines[1].split("：")[-1].strip() if len(lines) > 1 else "",
            "屬性": lines[2].split("：")[-1].strip() if len(lines) > 2 else "",
            "重大性評分": float(re.findall(r"\\d+\\.\\d+", lines[3])[0]) if len(lines) > 3 and re.findall(r"\\d+\\.\\d+", lines[3]) else 0.0
        }
        return result

    def run_analysis(self, output_path="news_impact_result.parquet"):
        results = []
        for company, aliases in self.company_alias_dict.items():
            pattern = '|'.join([re.escape(alias) for alias in aliases])
            filtered_news = self.df_news[self.df_news['content'].str.contains(pattern, case=False, na=False)].copy()
            for _, row in filtered_news.iterrows():
                analysis = self._analyze_news(row["content"])
                results.append({
                    "公司": company,
                    "日期": row["date"].strftime("%Y-%m-%d") if pd.notna(row["date"]) else "",
                    "摘要": analysis["摘要"],
                    "是否有影響": analysis["影響"],
                    "屬性": analysis["屬性"],
                    "重大性評分": analysis["重大性評分"],
                    "原始新聞": row["content"][:200] + "..."
                })
        df_result = pd.DataFrame(results)
        df_result.to_parquet(output_path, index=False)
        return df_result
'''

with open("news_impact_analyzer.py", "w", encoding="utf-8") as f:
    f.write(code)
