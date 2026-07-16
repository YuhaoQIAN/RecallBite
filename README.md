# RecallBite

> Save the thought. Recall the use. Apply it when it matters.

RecallBite 不是 summary 工具，也不是传统知识库。它把你手上的材料揉成以后能用的知识卡，再在需要的时候把它重新激活成表达、问题和行动。

**RecallBite saves the use of knowledge, not just the knowledge itself.**

## 核心工作流

```
Add Knowledge  →  Memory Cards  →  Activate Memory
```

### 1. Add Knowledge

把 article、transcript、meeting notes、webinar notes、slide text、LinkedIn post、link/title 或 one rough thought 直接丢进去。支持 PDF、DOCX、PPTX、纯文本和 URL 输入。

系统会根据输入长度和上下文自动生成三种卡片：

| 卡片类型 | 触发条件 | 输出内容 |
|---------|---------|---------|
| **Insight Pack** | 完整材料 | 具体用法、表达和问题 |
| **Use Card** | 中等完整度 | 可用但带保守提示的卡片 |
| **Clue Card** | 信息很少 | 仅生成线索，不装作确定结论 |

### 2. Memory Cards

卡片集合展示：card type、core insight、fog index、tags、trigger map、copy-ready wording。

### 3. Activate Memory

输入当前任务（如 proposal、meeting、CPD reflection、internal sharing、client discussion），系统召回相关卡片并生成：

- Why it matters now
- How to apply it
- Ready-to-use wording
- Better questions to ask
- Confidence note

## 本地运行

```bash
# 克隆项目
git clone https://github.com/YuhaoQIAN/RecallBite.git
cd RecallBite

# 创建虚拟环境
py -m venv .venv
.venv\Scripts\activate

# 安装依赖
pip install -r recallbite_mvp/requirements.txt

# 启动应用
streamlit run recallbite_mvp/app.py
```

应用将在 `http://localhost:8501` 启动。

## LLM 配置（可选）

RecallBite 可以在无 API key 的情况下使用本地规则运行。如需启用 LLM 增强功能：

```bash
cp recallbite_mvp/.env.example recallbite_mvp/.env
```

编辑 `.env` 文件，填入你的配置：

```env
RECALLBITE_LLM_API_KEY=your-api-key-here
RECALLBITE_LLM_PROVIDER=openai        # openai / deepseek / qwen / azure / ollama
RECALLBITE_LLM_MODEL=gpt-4o           # 可选，有默认值
```

## 测试

```bash
cd recallbite_mvp
pytest
```

## 支持的输入类型

- Article / Newsletter
- Transcript / Meeting Script
- Webcast / Lecture Notes
- Slide / Screenshot Text (PDF, PPTX)
- Link / Title
- One Thought / Rough Idea

## 技术栈

- **前端**: Streamlit (Dark Theme)
- **后端**: Python 3.14
- **文档解析**: PyMuPDF, python-docx, python-pptx, BeautifulSoup4
- **LLM**: OpenAI-compatible API (支持 DeepSeek、通义千问、Ollama 等)
- **存储**: 本地 JSON + SQLite

## 产品边界

- 不做登录 / 不做云同步
- 不接入 Teams / Zoom / Outlook / 企业邮箱
- 不上传外部服务
- 不处理敏感客户资料

## 项目结构

```
RecallBite/
├── recallbite_mvp/
│   ├── app.py                  # Streamlit 主应用
│   ├── requirements.txt        # Python 依赖
│   ├── .env.example            # 环境变量模板
│   ├── .streamlit/config.toml  # Streamlit 主题配置
│   ├── data/                   # 本地数据存储
│   ├── src/                    # 核心模块
│   │   ├── parsers/            # 文档解析器
│   │   ├── analyzers/          # 内容分析器
│   │   ├── generator.py        # 卡片生成
│   │   ├── activation.py       # 知识激活
│   │   ├── knowledge_base.py   # 本地知识库
│   │   ├── llm_client.py       # LLM 客户端
│   │   ├── retrieval.py        # 检索模块
│   │   └── storage.py          # 存储模块
│   └── tests/                  # 测试用例
└── sample/                     # 示例文件
```

## License

MIT
