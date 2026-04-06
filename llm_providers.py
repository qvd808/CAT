# LLM Provider Priority Configuration
# List providers in priority order - first available provider is used, subsequent ones are fallbacks
# Set enabled=False to skip a provider
# API keys are loaded from .env file using the api_key_env variable name
#
# All providers below are FREE tier (no credit card required):
#   Cerebras  — 1M tokens/day, no CC needed
#   Groq      — ~500K tokens/day, no CC needed
#   Google    — Gemini 2.5 Flash, ~250 req/day, no CC needed
#   SambaNova — $5 trial credits (~3 months), no CC needed
#   OpenRouter (free models only) — `:free` suffix, 200 req/day per model

PROVIDERS = [
    # 1. Cerebras — fastest inference, 1M tokens/day free, no CC
    #    OpenAI-compatible endpoint — no extra package needed
    {
        "name": "cerebras",
        "enabled": True,
        "api_key_env": "CEREBRAS_API_KEY",
        "model_env": "CEREBRAS_MODEL",
        "default_model": "qwen-3-235b-a22b-instruct-2507",
        "module": "langchain_openai",
        "class": "ChatOpenAI",
        "base_url": "https://api.cerebras.ai/v1",
        "max_tokens": 8192,
    },
    # 2. Groq — fast inference, ~500K tokens/day free, no CC
    {
        "name": "groq",
        "enabled": True,
        "api_key_env": "GROQ_API_KEY",
        "model_env": "GROQ_MODEL",
        "default_model": "llama-3.3-70b-versatile",
        "module": "langchain_groq",
        "class": "ChatGroq",
        "max_tokens": 8192,
    },
    # 3. Mistral AI — free tier, uses langchain-mistralai (native client, no max_completion_tokens issue)
    {
        "name": "mistral",
        "enabled": True,
        "api_key_env": "MISTRAL_API_KEY",
        "model_env": "MISTRAL_MODEL",
        "default_model": "mistral-small-latest",
        "module": "langchain_mistralai",
        "class": "ChatMistralAI",
        "max_tokens": 8192,
    },
    # 4. SambaNova — fast reasoning, $5 free trial credits, no CC
    #    OpenAI-compatible endpoint — no extra package needed
    {
        "name": "sambanova",
        "enabled": True,
        "api_key_env": "SAMBANOVA_API_KEY",
        "model_env": "SAMBANOVA_MODEL",
        "default_model": "Meta-Llama-3.3-70B-Instruct",
        "module": "langchain_openai",
        "class": "ChatOpenAI",
        "base_url": "https://api.sambanova.ai/v1",
        "max_tokens": 8192,
    },
    # 5. NVIDIA NIM — free credits on sign-up
    {
        "name": "nvidia",
        "enabled": True,
        "api_key_env": "NVIDIA_API_KEY",
        "model_env": "MODEL_NAME",
        "default_model": "meta/llama-3.3-70b-instruct",
        "module": "langchain_nvidia_ai_endpoints",
        "class": "ChatNVIDIA",
        "max_tokens": 8192,
    },
    # 6. OpenRouter (free models only, `:free` suffix) — 200 req/day per model, no CC
    {
        "name": "openrouter",
        "enabled": True,
        "api_key_env": "OPENROUTER_API_KEY",
        "model_env": "OPENROUTER_MODEL",
        "default_model": "openai/gpt-oss-20b:free",
        "module": "langchain_openai",
        "class": "ChatOpenAI",
        "base_url": "https://openrouter.ai/api/v1",
        "max_tokens": 4096,
        "default_headers": {
            "HTTP-Referer": "https://github.com/your-org/ai-solution-architect",
            "X-Title": "AI Solution Architect",
        },
    },
    # 7. Google AI Studio — Gemini 2.5 Flash free tier (needs langchain-google-genai)
    #    65k output tokens, 1M context window — best choice for heavy generation tasks
    {
        "name": "google",
        "enabled": True,
        "api_key_env": "GOOGLE_API_KEY",
        "model_env": "GOOGLE_MODEL",
        "default_model": "gemini-2.5-flash",
        "module": "langchain_google_genai",
        "class": "ChatGoogleGenerativeAI",
        "max_tokens": 65536,
    },
]

# Temperature presets per agent role
TEMPERATURES = {
    "supervisor": 0.3,
    "product_manager": 0.7,
    "architect": 0.4,
    "tech_strategist": 0.5,
    "critic": 0.3,
    "prototype_builder": 0.4,
    "qa_validator": 0.3,
}

# Roles that need high output tokens or deep reasoning.
# Providers are tried in the order listed before falling back to the full PROVIDERS list.
# openrouter is last — free tier caps at 4096 tokens, so it's a last resort for heavy tasks.
ROLE_PROVIDERS: dict[str, list[str]] = {
    "prototype_builder": ["google", "cerebras", "mistral", "groq", "nvidia", "sambanova", "openrouter"],
    "architect":         ["google", "cerebras", "mistral", "groq", "nvidia", "sambanova", "openrouter"],
    "test_engineer":     ["google", "cerebras", "mistral", "groq", "nvidia", "sambanova", "openrouter"],
    "debugger":          ["google", "cerebras", "mistral", "groq", "nvidia", "sambanova", "openrouter"],
}
