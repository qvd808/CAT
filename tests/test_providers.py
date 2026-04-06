"""
LLM Provider Health Checks

Tests each configured provider by sending a minimal probe prompt.
Run before starting the agent to verify which providers are available:

    python -m pytest tests/test_providers.py -v
    python -m pytest tests/test_providers.py -v -s   # show live output
"""

import os
import pytest
import concurrent.futures
from dotenv import load_dotenv

load_dotenv()

PROBE = "Reply with the single word: OK"


def _call_provider(provider: dict) -> tuple[bool, str]:
    """
    Send a minimal prompt to the provider.
    Returns (ok: bool, message: str).
    """
    api_key = os.getenv(provider.get("api_key_env", ""), "")
    if not api_key:
        return False, f"API key env var '{provider['api_key_env']}' not set"

    model = os.getenv(provider.get("model_env", ""), provider.get("default_model", ""))
    module_name = provider["module"]
    class_name = provider["class"]

    try:
        module = __import__(module_name, fromlist=[class_name])
        llm_class = getattr(module, class_name)

        kwargs = {
            "model": model,
            "temperature": 0.0,
            "max_tokens": 16,
        }
        if class_name == "ChatMistralAI":
            kwargs["mistral_api_key"] = api_key
        else:
            kwargs["api_key"] = api_key
        if class_name == "ChatOpenAI":
            if "base_url" in provider:
                kwargs["base_url"] = provider["base_url"]
            if "default_headers" in provider:
                kwargs["default_headers"] = provider["default_headers"]

        llm = llm_class(**kwargs)

        # Run in a thread so we can enforce a hard timeout even if the SDK
        # does internal retries/sleeps (e.g. Google's tenacity retry loop).
        def _invoke():
            return llm.invoke(PROBE)

        ex = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = ex.submit(_invoke)
        try:
            response = future.result(timeout=15)
        except concurrent.futures.TimeoutError:
            ex.shutdown(wait=False, cancel_futures=True)
            return False, "Timed out (likely rate-limited with internal retry)"
        finally:
            ex.shutdown(wait=False)

        text = (response.content or "").strip()
        return True, text[:80] or "(empty response)"

    except Exception as e:
        msg = str(e)
        if "429" in msg or "rate_limit" in msg.lower():
            return False, "Rate limited (429)"
        if "402" in msg:
            return False, "Out of credits (402)"
        if "401" in msg or "unauthorized" in msg.lower():
            return False, "Invalid API key (401)"
        return False, msg[:200]


def _make_test(provider: dict):
    """Factory: returns a pytest test function for the given provider."""
    name = provider["name"]

    def test_fn():
        if not provider.get("enabled", True):
            pytest.skip(f"{name} is disabled in llm_providers.py")

        api_key = os.getenv(provider.get("api_key_env", ""), "")
        if not api_key:
            pytest.skip(f"{name}: {provider['api_key_env']} not set in .env")

        ok, msg = _call_provider(provider)
        if not ok:
            rate_limited = any(x in msg.lower() for x in ("rate limit", "429", "timed out", "out of credits", "402"))
            if rate_limited:
                pytest.xfail(f"{name} is currently rate-limited: {msg}")
            else:
                pytest.fail(f"{name} failed: {msg}")
        print(f"\n  {name} response: {msg}")

    test_fn.__name__ = f"test_provider_{name}"
    test_fn.__doc__ = f"Check that {name} responds to a minimal prompt."
    return test_fn


# Dynamically generate one test per provider from llm_providers.py
def _register_tests():
    from llm_providers import PROVIDERS
    module = globals()
    for p in PROVIDERS:
        fn = _make_test(p)
        module[fn.__name__] = fn


_register_tests()
