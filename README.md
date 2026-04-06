# AI Solution Architect

A multi-agent system that takes your requirements and autonomously designs a solution — complete with architecture, tech stack, and a code prototype.

## 🧠 How It Works

You describe what you want to build in plain English. Six specialized AI agents collaborate to produce:

1. **📋 Product Manager** — Structures your requirements into features & user stories
2. **🏗️ Architect** — Designs the system architecture with components & data flow
3. **⚙️ Tech Strategist** — Recommends the optimal technology stack
4. **🔍 Design Critic** — Reviews the design against your requirements (revision loop)
5. **🛠️ Prototype Builder** — Generates actual code files you can run
6. **✅ QA Validator** — Validates the prototype and writes test cases

```
Requirements → PM → Architect → Tech Strategist → Critic → Builder → QA → Output
                                                     ↑                        |
                                                     └── Revision Loop ───────┘
```

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up NVIDIA NIM API Key

1. Sign up for free at [build.nvidia.com](https://build.nvidia.com)
2. Generate an API key
3. Edit `.env` and set your key:

```
NVIDIA_API_KEY=nvapi-your-actual-key-here
```

### 3. Run

```bash
# Interactive mode (pauses for your approval before generating code)
python main.py

# Autonomous mode (runs end-to-end without pauses)
python main.py --auto
```

### 4. Enter Your Requirements

Describe what you want to build. Press Enter twice to submit.

**Example:**
```
I need a system that tracks stock prices, lets me simulate trades
without real money, and shows my profit/loss over time.

It should have a web dashboard and REST API.

```

## 📁 Output

Generated projects are saved to the `output/` folder:

```
output/
└── your_project_name/
    ├── README.md           # Setup instructions
    ├── src/                # Application code
    ├── tests/              # Auto-generated test cases
    └── ...                 # Config files, etc.
```

## ⚙️ Configuration

| Variable | Default | Description |
|---|---|---|
| `NVIDIA_API_KEY` | — | Your NIM API key (required) |
| `MODEL_NAME` | `meta/llama-3.3-70b-instruct` | LLM model to use |
| `MAX_REVISION_LOOPS` | `2` | Max times the Critic can send designs back |

## 🏗️ Architecture

Built with:
- **LangGraph** — Stateful graph orchestration for the agent pipeline
- **NVIDIA NIM API** — Free LLM inference (Llama 3.3 70B)
- **Pydantic** — Structured output validation
- **Rich** — Beautiful terminal UI

## 📄 License

MIT
