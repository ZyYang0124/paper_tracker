#!/usr/bin/env python3
# evol_paper_tracker.py
import requests
import datetime
import os
import json
import smtplib
import time
import xml.etree.ElementTree as ET
import argparse
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ========== 默认配置 ==========
DEFAULT_JOURNALS = [
    "Nature", "Science", "Proc Natl Acad Sci U S A", "Cell",
    "Syst Biol", "Nat Ecol Evol", "Nat Genet", "Mol Biol Evol",
    "Cladistics", "Curr Biol"
]

DEFAULT_KEYWORDS = [
    "phylogen*", "systematic*", "evolution*", "genom*",
    '"phenotypic plasticity"', "adaptive radiation", "speciation",
    "molecular clock", "ancestral state reconstruction",
    "comparative genomics", "gene family evolution"
]

DASHSCOPE_API_KEY = "sk-b4f203c2f81341abb3e8ea34445f9f0f"  # ← 替换为你自己的

EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",
    "port": 465,
    "sender_email": "1214631670@qq.com",
    "password": "uktytxqmrccnidjb",
    "receiver_email": "yangzy0124@gmail.com"
}

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"
MAX_RETRIES = 3


import dashscope
from dashscope import Generation
dashscope.api_key = DASHSCOPE_API_KEY


def retry_on_fail(func, max_retries=MAX_RETRIES, delay_base=1):
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                wait = delay_base * (2 ** attempt)
                if attempt == max_retries - 1:
                    print(f"❌ 最终失败: {e}")
                    return None
                else:
                    print(f"⚠️ 尝试 {attempt + 1}/{max_retries} 失败: {e}，{wait}秒后重试...")
                    time.sleep(wait)
        return None
    return wrapper


@retry_on_fail
def summarize_with_qwen(title, abstract):
    if not abstract.strip():
        return "无摘要，无法总结。"
    prompt = f"""你是一位进化生物学专家，请用一段简洁的中文（100字以内）总结以下论文的核心发现：

标题：{title}
摘要：{abstract[:1500]}
"""
    response = Generation.call(
        model="qwen-max",
        prompt=prompt,
        max_tokens=150,
        timeout=60
    )
    summary = response.output.text.strip()
    return summary if summary else "总结失败。"


def normalize_keyword(kw):
    kw = kw.strip()
    if kw.startswith('"') and kw.endswith('"'):
        kw = kw[1:-1]
    return kw


@retry_on_fail
def search_pubmed(journal, keywords, days=7):
    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=days)

    kw_parts = [f'({normalize_keyword(kw)}[TIAB])' for kw in keywords if normalize_keyword(kw)]
    keyword_str = " OR ".join(kw_parts) if kw_parts else ""
    term = f'"{journal}"[Journal]'
    if keyword_str:
        term += f" AND ({keyword_str})"

    params = {
        "db": "pubmed",
        "term": term,
        "retmax": 200,
        "retmode": "json",
        "datetype": "pdat",
        "mindate": start_date.strftime("%Y/%m/%d"),
        "maxdate": today.strftime("%Y/%m/%d"),
    }

    print(f"\n🔍 检索期刊: {journal}")
    r = requests.get(BASE_URL + "esearch.fcgi", params=params, timeout=20)
    r.raise_for_status()
    data = r.json()
    idlist = data.get("esearchresult", {}).get("idlist", [])
    print(f"✅ 找到 {len(idlist)} 篇")
    return idlist


@retry_on_fail
def fetch_article(pmid):
    r = requests.get(BASE_URL + "efetch.fcgi", params={"db": "pubmed", "id": pmid, "retmode": "xml"}, timeout=20)
    r.raise_for_status()
    root = ET.fromstring(r.text)

    title_el = root.find(".//ArticleTitle")
    title = "".join(title_el.itertext()).strip() if title_el is not None else ""

    abstract_parts = []
    for ab in root.findall(".//Abstract/AbstractText"):
        label = ab.attrib.get("Label", "")
        text = "".join(ab.itertext()).strip()
        abstract_parts.append(f"{label}: {text}" if label else text)
    abstract = "\n".join([p for p in abstract_parts if p])

    journal_el = root.find(".//Journal/Title")
    journal = journal_el.text.strip() if journal_el is not None and journal_el.text else ""

    doi = next((aid.text.strip() for aid in root.findall(".//ArticleId")
                if aid.attrib.get("IdType", "").lower() == "doi" and aid.text), "")

    return {"pmid": pmid, "title": title, "abstract": abstract, "journal": journal, "doi": doi}


def load_processed(cache_file):
    if not os.path.exists(cache_file):
        return set()
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return set(data) if isinstance(data, list) else set()
    except:
        print("⚠️ 缓存文件异常，从空集开始")
        return set()


def send_email(subject, body):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_CONFIG["sender_email"]
    msg["To"] = EMAIL_CONFIG["receiver_email"]
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["port"]) as server:
            server.login(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["password"])
            server.sendmail(EMAIL_CONFIG["sender_email"], EMAIL_CONFIG["receiver_email"], msg.as_string())
        print("📧 邮件发送成功！")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        raise


def parse_args():
    parser = argparse.ArgumentParser(
        description="🔬 进化生物学论文追踪器：从 PubMed 检索指定期刊/关键词的新论文，用 Qwen 总结并邮件推送。",
        epilog="示例：python evol_paper_tracker.py -j 'Nature,Science' -d 3 -n"
    )
    parser.add_argument("-j", "--journals", type=str,
                        help="指定期刊列表，逗号分隔（如：Nature,Science）")
    parser.add_argument("-k", "--keywords", type=str,
                        help="指定关键词，逗号分隔（支持通配符 * 和引号）")
    parser.add_argument("-d", "--days", type=int, default=7,
                        help="检索最近 N 天的论文（默认：7）")
    parser.add_argument("-n", "--no-email", action="store_true",
                        help="不发送邮件，仅生成报告文件")
    parser.add_argument("-c", "--cache-file", type=str, default="processed_pmids.json",
                        help="已处理 PMID 的缓存文件路径（默认：processed_pmids.json）")
    parser.add_argument("-o", "--report-file", type=str,
                        help="输出报告文件名（默认：evol_summary_YYYY-MM-DD.md）")

    args = parser.parse_args()

    # 解析 journals 和 keywords
    journals = [j.strip() for j in args.journals.split(",")] if args.journals else DEFAULT_JOURNALS
    keywords = [k.strip() for k in args.keywords.split(",")] if args.keywords else DEFAULT_KEYWORDS
    report_file = args.report_file or f"evol_summary_{datetime.date.today()}.md"

    return {
        "journals": journals,
        "keywords": keywords,
        "days": args.days,
        "no_email": args.no_email,
        "cache_file": args.cache_file,
        "report_file": report_file
    }


def main():
    config = parse_args()

    processed = load_processed(config["cache_file"])
    all_articles = {}
    new_pmids = []

    for journal in config["journals"]:
        pmids = search_pubmed(journal, config["keywords"], days=config["days"]) or []
        for pmid in pmids:
            if pmid in processed:
                continue
            art = fetch_article(pmid)
            if not art or not art["abstract"].strip():
                continue
            summary = summarize_with_qwen(art["title"], art["abstract"]) or "⚠️ 总结失败"
            art["summary"] = summary
            j = art["journal"]
            if j not in all_articles:
                all_articles[j] = []
            all_articles[j].append(art)
            new_pmids.append(pmid)

    # 生成报告
    lines = [f"# 🧬 进化生物学每日简报 ({datetime.date.today()})\n"]
    if not all_articles:
        lines.append("今日无相关新论文。")
    else:
        for journal, arts in all_articles.items():
            lines.append(f"## 📰 {journal}\n")
            for art in arts:
                url = f"https://doi.org/{art['doi']}" if art['doi'] else f"https://pubmed.ncbi.nlm.nih.gov/{art['pmid']}/"
                lines.append(f"### [{art['title']}]({url})")
                lines.append(f"**AI 总结**：{art['summary']}\n")
                lines.append(f"PMID: [{art['pmid']}](https://pubmed.ncbi.nlm.nih.gov/{art['pmid']}/)\n---\n")

    report = "\n".join(lines)
    with open(config["report_file"], "w", encoding="utf-8") as f:
        f.write(report)

    # 更新缓存
    processed.update(new_pmids)
    with open(config["cache_file"], "w", encoding="utf-8") as f:
        json.dump(list(processed), f)

    # 发送邮件
    if new_pmids and not config["no_email"]:
        send_email(f"【论文简报】{datetime.date.today()} - {len(new_pmids)} 篇新文章", report)
    elif config["no_email"]:
        print("📭 跳过邮件发送（--no-email 启用）")
    else:
        print("📭 今日无新文章，未发送邮件。")


if __name__ == "__main__":
    main()