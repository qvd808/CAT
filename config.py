"""
Configuration for the AI Solution Architect system.
Loads environment variables and provides LLM factory with Python list-based provider priority.
"""

import os
from dotenv import load_dotenv
from llm_providers import PROVIDERS, TEMPERATURES, ROLE_PROVIDERS

load_dotenv()

# --- System Settings ---
MAX_REVISION_LOOPS = 2
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# --- Current provider index for fallback ---
_current_provider_index = 0


def _get_next_provider_index():
    """Get the next available provider index, wrapping around if needed."""
    global _current_provider_index
    enabled_count = sum(1 for p in PROVIDERS if p.get("enabled", True))
    if enabled_count == 0:
        return -1
    idx = _current_provider_index % len(PROVIDERS)
    _current_provider_index = (idx + 1) % len(PROVIDERS)
    return idx


def _create_llm_from_provider(provider, temp, max_tokens=None):
    """Create an LLM instance from a provider config."""
    name = provider.get("name", "unknown")
    api_key_env = provider.get("api_key_env", "")
    model_env = provider.get("model_env", "")
    default_model = provider.get("default_model", "")
    module_name = provider.get("module", "")
    class_name = provider.get("class", "")
    
    # Get API key from environment
    api_key = os.getenv(api_key_env, "")
    if not api_key:
        return None, f"No API key for {name}"
    
    # Get model from environment or use default
    model = os.getenv(model_env, default_model)
    
    try:
        # Dynamically import the module and class
        module = __import__(module_name, fromlist=[class_name])
        llm_class = getattr(module, class_name)
        
        # Build kwargs for the LLM constructor
        kwargs = {
            "temperature": temp,
            "max_tokens": max_tokens if max_tokens is not None else provider.get("max_tokens", 4096),
        }

        # Mistral native client uses mistral_api_key, all others use api_key
        if class_name == "ChatMistralAI":
            kwargs["mistral_api_key"] = api_key
        else:
            kwargs["api_key"] = api_key

        # Add model parameter (all providers use "model")
        kwargs["model"] = model
        if class_name == "ChatOpenAI":
            if "base_url" in provider:
                kwargs["base_url"] = provider["base_url"]
            if "default_headers" in provider:
                kwargs["default_headers"] = provider["default_headers"]
        
        return llm_class(**kwargs), None
        
    except Exception as e:
        return None, str(e)


def _ordered_providers_for_role(role: str) -> list:
    """Return PROVIDERS reordered so role-preferred providers come first."""
    preferred_names = ROLE_PROVIDERS.get(role, [])
    if not preferred_names:
        return PROVIDERS

    provider_by_name = {p["name"]: p for p in PROVIDERS}
    ordered = []
    # Add preferred providers first (in the order specified)
    for name in preferred_names:
        if name in provider_by_name:
            ordered.append(provider_by_name[name])
    # Append remaining providers as fallbacks
    preferred_set = set(preferred_names)
    for p in PROVIDERS:
        if p["name"] not in preferred_set:
            ordered.append(p)
    return ordered


def get_llm(role: str = "supervisor", max_tokens: int = None):
    """
    Factory function to create an LLM instance with automatic fallback based on PROVIDERS list.
    Roles listed in ROLE_PROVIDERS get their preferred providers tried first.
    Temperature is adjusted per agent role for optimal output.
    """
    temp = TEMPERATURES.get(role, 0.5)
    ordered = _ordered_providers_for_role(role)

    for provider in ordered:
        if not provider.get("enabled", True):
            continue

        name = provider.get("name", "unknown")
        llm, error = _create_llm_from_provider(provider, temp, max_tokens)

        if llm is not None:
            return llm
        else:
            print(f"  [dim]⚠️ {name} unavailable: {error}, trying next provider...[/]")
            continue

    provider_names = [p.get("name", "unknown") for p in PROVIDERS if p.get("enabled", True)]
    raise ValueError(
        f"No LLM API key configured! Set one of these in your .env file:\n"
        f"Providers (in priority order): {', '.join(provider_names)}\n"
        f"Edit llm_providers.py to change priority or add providers."
    )


def get_llm_with_fallback(role: str = "supervisor", max_retries: int = None, max_tokens: int = None):
    """
    Get an LLM and wrap it with fallback logic for API errors.
    Returns a wrapper that will try the next provider on rate limits or server errors.
    """
    class FallbackLLM:
        def __init__(self, role, max_retries, max_tokens):
            self.role = role
            # Default to trying every configured provider at least once
            self.max_retries = max_retries if max_retries is not None else len(PROVIDERS) + 1
            self.max_tokens = max_tokens
            self._llm = None
            self._provider_idx = 0
        
        def _get_next_llm(self):
            """Get the next available LLM provider, respecting role-based ordering."""
            ordered = _ordered_providers_for_role(self.role)
            for i in range(len(ordered)):
                idx = (self._provider_idx + i) % len(ordered)
                provider = ordered[idx]
                if not provider.get("enabled", True):
                    continue

                temp = TEMPERATURES.get(self.role, 0.5)
                llm, error = _create_llm_from_provider(provider, temp, self.max_tokens)
                if llm is not None:
                    self._provider_idx = (idx + 1) % len(ordered)
                    self._llm = llm
                    return llm
            return None
        
        def invoke(self, *args, **kwargs):
            """
            Invoke the LLM with automatic fallback on errors.
            Tries each enabled provider once. If all are rate-limited or unavailable,
            raises immediately — the caller should report failure to the user.
            """
            ordered = _ordered_providers_for_role(self.role)
            n_providers = sum(1 for p in ordered if p.get("enabled", True))

            last_error = None
            for _ in range(n_providers):
                if self._llm is None:
                    self._llm = self._get_next_llm()
                    if self._llm is None:
                        break

                try:
                    return self._llm.invoke(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_msg = str(e)
                    is_rate_limit = "429" in error_msg or "rate_limit" in error_msg.lower() or "402" in error_msg
                    is_server_error = any(code in error_msg for code in ["500", "502", "503", "504"])

                    if is_rate_limit or is_server_error:
                        reason = "rate limit/credits" if ("429" in error_msg or "402" in error_msg) else "server error"
                        print(f"  [dim]⚠️ LLM error ({reason}), switching provider...[/]")
                        self._llm = None  # Force getting a new provider next iteration
                    else:
                        raise  # Re-raise non-retryable errors immediately

            raise RuntimeError(
                "All LLM providers are currently rate-limited or unavailable. "
                "Please wait and try again later."
            )
    
    return FallbackLLM(role, max_retries, max_tokens)
