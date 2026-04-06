# CAT (Convoluted Agent Trying to code) or at least can help you prototype

Sometimes I just need a quick prototype of a simple system to work first, so I created **CAT (Convoluted Agent Trying to code)**. My goal is that if I give it a goal, it should be able to build the system by itself reliably using the free models available on the internet.

## How It Works

You describe what you want to build in plain English, then feed it into the system. The problem is that cheap models freely available on the internet are usually poor and prone to hallucinations because they don't have a long context (or I just suck at finding good models). My thought was that if I can create a loop in the system architecture, it can reliably detect what it needs to do with the minimal context needed, then solve the problem step by step. For example, to create a project, it first needs to be aware that it needs to create a file.

I use LangChain to create the workflow of agents below:

1. **📋 Product Manager** — Structures your requirements into features & user stories
2. **🏗️ Architect** — Designs the system architecture with components & data flow
3. **⚙️ Tech Strategist** — Recommends the optimal technology stack
4. **🔍 Design Critic** — Reviews the design against your requirements (revision loop)
5. **🛠️ Prototype Builder** — Generates actual code files you can run
6. **✅ QA Validator** — Validates the prototype and writes test cases

Currently, the agent logic is implemented as a binary module for specific reasons I won't go into detail about here. I can guarantee that the binary file does nothing else except act as a node within the LangChain framework. If you want to use it, you'll just have to trust that I'm not lying to you.

```
Requirements → PM → Architect → Tech Strategist → Critic → Builder → QA → Output
                                                     ↑                        |
                                                     └── Revision Loop ───────┘
```

## Quick Start

### 1. Install Dependencies
- Create a Python environment and install the requirements.
```bash
pip install -r requirements.txt
```

### 2. Set Up API Key
- There should be a `.env.template` file.
- I try to use free-tier LLMs available on the internet.


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

The goal is for it to build systems like the one above and generate unit tests to verify the functionality. Think of it this way: to build trust, the system provides unit tests so that if you run them and they pass, you know it works. Of course, there are questions about the validity of the tests and other factors, but at this early stage, it should be enough. Currently, the system's capability is limited to creating a Python-based todo app within approximately 12 hours.

## Architecture

Built with:
- **LangGraph** — Stateful graph orchestration for the agent pipeline
- **NVIDIA NIM API** — Free LLM inference (Llama 3.3 70B)
- **Pydantic** — Structured output validation
- **Rich** — Beautiful terminal UI

## 📄 License
MIT
