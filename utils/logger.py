"""
Logging utilities for the AI Solution Architect pipeline.
Writes structured logs to logs/run_<timestamp>.log
Records: node transitions, errors, timings, and key decisions.
"""

import logging
import os
import time
from datetime import datetime
from pathlib import Path


LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")


def setup_logger() -> tuple[logging.Logger, str]:
    """
    Set up a new logger for this run.
    Returns (logger, log_file_path).
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    # Timestamp-based log file name
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(LOG_DIR, f"run_{ts}.log")

    # Create logger
    logger = logging.getLogger(f"architect_{ts}")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    # File handler — full detail
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(fh)

    # Write a run header
    logger.info("=" * 70)
    logger.info("AI Solution Architect — Run Started")
    logger.info(f"Log file: {log_file}")
    logger.info("=" * 70)

    return logger, log_file


# Module-level logger instance (set by main.py on startup)
_logger: logging.Logger | None = None
_run_start: float = 0.0
_node_start: float = 0.0


def init(logger: logging.Logger):
    """Initialize the module-level logger."""
    global _logger, _run_start
    _logger = logger
    _run_start = time.monotonic()


def _log(level: str, msg: str):
    if _logger:
        getattr(_logger, level)(msg)


def node_start(node_name: str):
    """Log that a node has started executing."""
    global _node_start
    _node_start = time.monotonic()
    _log("info", f"▶ NODE START  | {node_name}")


def node_end(node_name: str, success: bool = True, notes: str = ""):
    """Log that a node finished executing."""
    elapsed = time.monotonic() - _node_start
    status = "✔ SUCCESS" if success else "✘ FAILED "
    msg = f"■ NODE END    | {node_name} | {status} | {elapsed:.1f}s"
    if notes:
        msg += f" | {notes}"
    _log("info" if success else "warning", msg)


def node_error(node_name: str, error: Exception, context: str = ""):
    """Log an error that occurred inside a node."""
    msg = f"✘ NODE ERROR  | {node_name} | {type(error).__name__}: {error}"
    if context:
        msg += f" | context: {context}"
    _log("error", msg)


def routing(from_node: str, to_node: str, reason: str = ""):
    """Log a routing decision from the supervisor."""
    msg = f"→ ROUTE       | {from_node} → {to_node}"
    if reason:
        msg += f" | {reason}"
    _log("info", msg)


def revision_loop(count: int, max_count: int, triggered_by: str, reason: str = ""):
    """Log when a revision loop is triggered."""
    _log("warning", f"↺ REVISION    | loop {count}/{max_count} | triggered by {triggered_by} | {reason}")


def dep_check(ecosystem: str, package: str, valid: bool, detail: str = ""):
    """Log a dependency validation result."""
    status = "✔ VALID  " if valid else "✘ INVALID"
    _log("info", f"  DEP {status} | [{ecosystem}] {package} | {detail}")


def llm_call(node_name: str, prompt_len: int, response_len: int):
    """Log an LLM API call."""
    _log("debug", f"  LLM CALL    | {node_name} | prompt={prompt_len}ch response={response_len}ch")


def parse_error(node_name: str, error: Exception, raw_preview: str = ""):
    """Log a JSON parse failure."""
    preview = raw_preview[:200].replace("\n", " ") if raw_preview else ""
    _log("warning", f"  PARSE WARN  | {node_name} | {type(error).__name__}: {error} | raw: {preview}")


def qa_result(approved: bool, coverage: str, dep_issues: int, req_issues: int):
    """Log the QA validation summary."""
    status = "APPROVED" if approved else "REJECTED"
    _log("info", f"  QA RESULT   | {status} | coverage={coverage} | dep_issues={dep_issues} | req_issues={req_issues}")


def run_complete(project_name: str, output_dir: str):
    """Log successful run completion."""
    elapsed = time.monotonic() - _run_start
    _log("info", "=" * 70)
    _log("info", f"✔ RUN COMPLETE | project={project_name} | total={elapsed:.1f}s")
    _log("info", f"  Output: {output_dir}")
    _log("info", "=" * 70)


def run_error(error: Exception):
    """Log a fatal run error."""
    elapsed = time.monotonic() - _run_start
    _log("error", "=" * 70)
    _log("error", f"✘ RUN FAILED  | {type(error).__name__}: {error} | elapsed={elapsed:.1f}s")
    _log("error", "=" * 70)


def requirements_received(text: str):
    """Log the user's raw requirements."""
    _log("info", f"  REQUIREMENTS| {len(text)} chars | preview: {text[:150].replace(chr(10), ' ')}")
