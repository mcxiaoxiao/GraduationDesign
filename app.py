import random
import time

import streamlit as st


st.set_page_config(
    page_title="Text-to-SQL Multi-Agent System",
    page_icon="💬",
    layout="wide",
)


DEMO_STEPS = [
    {
        "user_demo": "数据库课程分数最高的学生是谁？他来自哪个专业？",
        "label": "answerable",
        "label_text": "可回答",
        "context_type": "跨表查询",
        "tables": ["成绩", "学生", "课程", "专业"],
        "reasoning": [
            "先锁定“数据库课程”这一门课。",
            "再从成绩表中找到该课程分数最高的学生。",
            "最后连接学生表和专业表补出专业信息。",
        ],
        "sql": """
SELECT s.姓名, m.专业名称, g.分数
FROM 成绩 AS g
JOIN 学生 AS s ON g.学号 = s.学号
JOIN 课程 AS c ON g.课程号 = c.课程号
JOIN 专业 AS m ON s.专业编号 = m.专业编号
WHERE c.课程名 = '数据库'
ORDER BY g.分数 DESC
LIMIT 1;
""".strip(),
        "result": [{"姓名": "林悦", "专业名称": "数据科学与大数据技术", "分数": 96}],
        "response": "查到了。数据库课程分数最高的学生是林悦，来自数据科学与大数据技术专业。",
        "score": 96,
    },
    {
        "user_demo": "编号1的学生叫啥",
        "label": "ambiguous",
        "label_text": "模糊",
        "context_type": "指代延续 + 歧义",
        "tables": ["学生", "课程"],
        "reasoning": [
            "上一轮同时命中了学生和课程两个实体。",
            "当前输入里的“编号 1”缺少实体说明，可能是学号，也可能是课程号。",
            "因此先发起澄清，而不是直接生成 SQL。",
        ],
        "sql": None,
        "result": None,
        "response": "请先澄清一下，“编号 1”指的是学生编号，还是课程编号？当前上下文里这两个对象都成立。",
        "score": 92,
    },
    {
        "user_demo": "课程",
        "label": "answerable",
        "label_text": "澄清后可回答",
        "context_type": "澄清完成 + 再次查询",
        "tables": ["课程", "成绩", "学生"],
        "reasoning": [
            "用户已经明确“1”表示课程编号 1。",
            "查询目标变为选出课程号为 1 的全部学生。",
            "因此连接课程表、成绩表和学生表返回学生名单。",
        ],
        "sql": """
SELECT s.姓名
FROM 课程 AS c
JOIN 成绩 AS g ON c.课程号 = g.课程号
JOIN 学生 AS s ON g.学号 = s.学号
WHERE c.课程号 = 1
ORDER BY s.姓名;
""".strip(),
        "result": [{"姓名": "陈浩"}, {"姓名": "林悦"}, {"姓名": "苏晴"}],
        "response": "已澄清为课程编号 1。选修这门课的学生有陈浩、林悦和苏晴。",
        "score": 95,
    },
    {
        "user_demo": "okk退下吧",
        "label": "improper",
        "label_text": "Improper",
        "context_type": "普通对话收尾",
        "tables": [],
        "reasoning": [
            "当前轮次作为演示收尾，不再继续数据库问答。",
            "因此不生成 SQL，直接返回结束语。",
        ],
        "sql": None,
        "result": None,
        "response": "再见，如果你还想继续看 Text-to-SQL 对话演示，随时回来。",
        "score": 100,
    },
]


WELCOME_MESSAGE = {
    "role": "assistant",
    "content": "这里是 Text-to-SQL Multi-Agent 系统 demo，已连接database：课程成绩.db。你可以直接在底部输入任意内容，我会根据你的输入生成 SQL 语句。",
    "meta": None,
}


LABEL_STYLES = {
    "answerable": ("#e8f7ee", "#147a43", "#2aa06b"),
    "ambiguous": ("#fff4db", "#9a6700", "#f0b429"),
    "improper": ("#eef2ff", "#3d4ea3", "#7a89d9"),
}


MIN_RESPONSE_DELAY = 2.4
MAX_RESPONSE_DELAY = 4.1


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(35, 122, 255, 0.10), transparent 30%),
                radial-gradient(circle at top right, rgba(19, 181, 123, 0.10), transparent 26%),
                linear-gradient(180deg, #f6f8fc 0%, #edf2fb 100%);
        }
        [data-testid="stSidebar"] {
            display: none;
        }
        .block-container {
            max-width: 980px;
            padding-top: 4.2rem;
            padding-bottom: 6rem;
        }
        .hero {
            padding: 1.15rem 1.2rem;
            border-radius: 22px;
            background: linear-gradient(135deg, #10233d 0%, #1f4970 100%);
            color: white;
            box-shadow: 0 20px 40px rgba(16, 35, 61, 0.15);
            margin-bottom: 1rem;
        }
        .hero h1 {
            margin: 0;
            font-size: 1.85rem;
        }
        .hero p {
            margin: 0.45rem 0 0;
            color: rgba(255, 255, 255, 0.84);
        }
        .top-actions {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 0.6rem;
        }
        .meta-line {
            margin-top: 0.35rem;
            color: #55708d;
            font-size: 0.9rem;
        }
        .badge-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin: 0.45rem 0 0.2rem;
        }
        .table-badge {
            display: inline-block;
            padding: 0.18rem 0.52rem;
            border-radius: 999px;
            background: #edf3ff;
            color: #2d4d73;
            font-size: 0.8rem;
            font-weight: 600;
        }
        .empty-tip {
            padding: 1rem 1.1rem;
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid rgba(29, 56, 95, 0.08);
            color: #5a728d;
            margin-top: 0.35rem;
        }
        .footnote {
            color: #5b748e;
            font-size: 0.9rem;
            margin-top: 0.9rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_label(label: str, text: str) -> str:
    bg_color, text_color, border_color = LABEL_STYLES[label]
    return (
        f"<span style='display:inline-block;padding:0.18rem 0.58rem;border-radius:999px;"
        f"background:{bg_color};color:{text_color};border:1px solid {border_color};"
        f"font-size:0.8rem;font-weight:700;'>{text}</span>"
    )


def init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = [WELCOME_MESSAGE]
    if "demo_index" not in st.session_state:
        st.session_state.demo_index = 0


def reset_demo() -> None:
    st.session_state.messages = [WELCOME_MESSAGE]
    st.session_state.demo_index = 0


def build_assistant_message(step: dict) -> dict:
    return {
        "role": "assistant",
        "content": step["response"],
        "meta": {
            "label": step["label"],
            "label_text": step["label_text"],
            "context_type": step["context_type"],
            "tables": step["tables"],
            "reasoning": step["reasoning"],
            "sql": step["sql"],
            "result": step["result"],
            "score": step["score"],
        },
    }


def render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        st.write(message["content"])

        meta = message.get("meta")
        if not meta:
            return

        st.markdown(
            render_label(meta["label"], meta["label_text"]),
            unsafe_allow_html=True,
        )
        st.markdown(
            f"<div class='meta-line'>上下文关系：{meta['context_type']}</div>",
            unsafe_allow_html=True,
        )

        if meta["tables"]:
            badges = "".join(
                f"<span class='table-badge'>{table}</span>" for table in meta["tables"]
            )
            st.markdown(f"<div class='badge-row'>{badges}</div>", unsafe_allow_html=True)

        with st.expander("查看本轮推理与 SQL", expanded=False):
            st.markdown("**思维链摘要**")
            for step in meta["reasoning"]:
                st.markdown(f"- {step}")

            st.markdown("**SQL**")
            if meta["sql"]:
                st.code(meta["sql"], language="sql")
            else:
                st.info("当前轮次不生成 SQL。")

            st.markdown("**执行结果**")
            if meta["result"]:
                st.table(meta["result"])
            else:
                st.info("当前轮次没有数据库执行结果。")



def append_assistant_turn() -> None:
    if st.session_state.demo_index >= len(DEMO_STEPS):
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": "这段 demo 已经结束了。你可以点上方“重新开始”再看一遍。",
                "meta": None,
            }
        )
        return

    step = DEMO_STEPS[st.session_state.demo_index]
    st.session_state.messages.append(build_assistant_message(step))
    st.session_state.demo_index += 1


def render_top() -> None:
    left, right = st.columns([6, 1])
    with left:
        st.markdown(
            """
            <div class="hero">
                <h1>Text-to-SQL Multi-Agent System</h1>
                <p>当前 SQLite 数据库为 课程成绩.db，Tables: 学生、课程、成绩、专业</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with right:
        if st.button("重新开始", use_container_width=True):
            reset_demo()
            st.rerun()


def main() -> None:
    inject_styles()
    init_state()
    render_top()


    for message in st.session_state.messages:
        render_message(message)

    user_text = st.chat_input("请输入问题")
    if user_text:
        step_index = min(st.session_state.demo_index, len(DEMO_STEPS) - 1)
        scripted_user_text = DEMO_STEPS[step_index]["user_demo"]
        st.session_state.messages.append(
            {"role": "user", "content": scripted_user_text, "meta": None}
        )
        with st.chat_message("user"):
            st.write(scripted_user_text)
        with st.chat_message("assistant"):
            with st.spinner("正在生成回复..."):
                time.sleep(random.uniform(MIN_RESPONSE_DELAY, MAX_RESPONSE_DELAY))
        append_assistant_turn()
        st.rerun()

    st.markdown(
        "<div class='footnote'>这只是简单的 demo，请勿用于生产环境。</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
