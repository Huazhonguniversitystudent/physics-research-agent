import os

import streamlit as st
from dotenv import load_dotenv

from src.agent import run_agent
from src.rag.pdf_documents import list_knowledge_papers
from src.rag.retriever import search_knowledge_base
from src.web.public_mode import is_public_demo_mode, synthetic_demo


load_dotenv()
PUBLIC_DEMO_MODE = is_public_demo_mode()


st.set_page_config(page_title="Physics Research Agent", page_icon="⚛️", layout="wide")
st.markdown(
    """
    <style>
    .block-container {max-width: 1120px; padding-top: 2rem;}
    [data-testid="stMetric"] {background: #f5f7fb; border: 1px solid #e3e8f0; padding: 1rem; border-radius: 12px;}
    .demo-badge {display:inline-block; padding:.25rem .65rem; border-radius:999px; background:#fff3cd;
                 color:#795500; font-weight:700; border:1px solid #ffe69c; margin-bottom:.6rem;}
    .muted {color:#667085;}
    </style>
    """,
    unsafe_allow_html=True,
)


def show_trace(trace: list[dict]) -> None:
    if not trace:
        return
    with st.expander("🔧 查看工具调用过程"):
        for index, item in enumerate(trace, 1):
            st.markdown(f"**{index}. `{item['tool']}`**")
            st.json(item.get("arguments", {}), expanded=False)
            st.caption("结果摘要")
            result = item.get("result")
            if isinstance(result, (dict, list)):
                st.json(result, expanded=False)
            else:
                st.code(str(result))
            if item.get("citations"):
                st.caption("引用：" + " · ".join(item["citations"]))


def run_public_agent(question: str) -> None:
    if not os.getenv("DEEPSEEK_API_KEY"):
        st.warning("未检测到 API Key。请在本地 .env 配置 DEEPSEEK_API_KEY。")
        return
    with st.spinner("Agent 正在思考…"):
        result = run_agent(question, show_steps=False, public_mode=PUBLIC_DEMO_MODE, collect_trace=True)
    st.markdown(result["answer"])
    show_trace(result["trace"])


st.title("⚛️ Physics Research Agent")
st.markdown("### 面向物理科研场景的 AI Agent 学习与实践项目")
st.caption("让 LLM 调用受限 Python 工具，并基于科研数据与文献证据回答问题。")

with st.sidebar:
    st.title("Physics Research Agent")
    st.header("运行状态")
    if PUBLIC_DEMO_MODE:
        st.success("Public Demo Mode")
        st.caption("只允许公开文档、公开论文与合成演示数据。")
    else:
        st.info("Private Local Mode")
        st.caption("已显式关闭公开模式；私有能力仍不会在页面中列出。")
    st.markdown("**能力**")
    st.markdown("✓ 普通物理问答  \n✓ 数学计算  \n✓ 合成科研 CSV  \n✓ Markdown RAG  \n✓ PDF 论文 RAG  \n✗ 私人真实科研数据（Public Mode 禁用）")
    st.divider()
    st.caption("当前项目为学习原型，不用于自动生成科研结论。")

mode = st.radio(
    "选择演示模式",
    ("A · Agent 对话", "B · 科研数据 Demo", "C · 论文问答"),
    horizontal=True,
)

if mode.startswith("A"):
    st.subheader("Agent 对话")
    st.caption("选择示例或输入问题，展示模型如何选择工具并回传结果。")
    examples = [
        "天为什么是蓝色的？",
        "12345 * 6789 等于多少？",
        "比较 synthetic_micromagnetics.csv 中两条曲线的 switching time。",
        "根据项目文档，Tool Calling 中是谁真正执行 Python？请给出处。",
        "根据 Mumax3 论文，默认动力学时间积分方法是什么？请给页码。",
    ]
    columns = st.columns(len(examples))
    for index, example in enumerate(examples):
        if columns[index].button(f"示例 {index + 1}", width="stretch"):
            st.session_state.agent_question = example
    question = st.text_area("问题", key="agent_question", height=100, placeholder="例如：计算 12345 * 6789")
    if st.button("运行 Agent", type="primary", disabled=not question.strip()):
        run_public_agent(question)

elif mode.startswith("B"):
    st.subheader("科研数据 Demo")
    st.markdown('<span class="demo-badge">SYNTHETIC · 合成演示数据</span>', unsafe_allow_html=True)
    st.info("以下数据仅用于演示管线和统计方法，不是真实实验或仿真结果。")
    if st.button("运行合成数据分析", type="primary"):
        with st.spinner("读取 CSV、线性插值并绘图…"):
            result = synthetic_demo()
        first, second, difference = st.columns(3)
        first.metric("MuMax3 过零时间", f"{result['mumax3_ps']:.3f} ps")
        second.metric("COMSOL 过零时间", f"{result['comsol_ps']:.3f} ps")
        difference.metric("绝对差值", f"{result['difference_ps']:.3f} ps")
        st.image(result["plot_path"], caption=f"{result['dataset']} · {result['method']}", width="stretch")

else:
    st.subheader("公开论文 PDF 问答")
    papers = list_knowledge_papers(include_local=False)
    available = [paper for paper in papers if paper["local_available"]]
    if available:
        paper = available[0]
        st.markdown(f"**{paper['title']}**  ")
        authors = ", ".join(paper.get("authors", [])) or "作者未知"
        st.caption(f"{authors} · {paper.get('year') or '年份未知'} · paper_id: {paper['paper_id']}")
        if paper.get("source_url"):
            st.markdown(f"[arXiv source]({paper['source_url']})")
        paper_question = st.text_area(
            "论文问题",
            value="What time integration methods are supported, and where are they described?",
            height=100,
        )
        if st.button("检索并回答", type="primary", disabled=not paper_question.strip()):
            if os.getenv("DEEPSEEK_API_KEY"):
                run_public_agent(f"根据论文 {paper['paper_id']} 回答：{paper_question}")
            else:
                st.warning("未检测到 API Key。请在本地 .env 配置 DEEPSEEK_API_KEY。")
                result = search_knowledge_base(
                    paper_question, top_k=4, scope="papers", paper_id=paper["paper_id"], public_only=True
                )
                st.caption("以下仅是本地检索证据，未生成 Agent 答案。")
                if not result["results"]:
                    st.info("当前检索到的论文片段不足以支持这个结论。")
                for item in result["results"]:
                    st.markdown(f"**{item['citation']}**")
                    st.write(item["text"][:500])
    else:
        st.warning("未找到可读取的公开论文 PDF，请先按 README 配置。")
