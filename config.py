import os
from dotenv import load_dotenv

load_dotenv()

# ── Mock mode (no API keys needed) ───────────────────────────────────────────
# Set MOCK_MODE=true to run the full pipeline with fake responses.
# Flip to false once DASHSCOPE_API_KEY and Alibaba credentials are in .env.
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() in ("true", "1", "yes")

# ── DashScope ─────────────────────────────────────────────────────────────────
DASHSCOPE_API_KEY  = os.getenv("DASHSCOPE_API_KEY", "sk-mock-key-placeholder")
DASHSCOPE_BASE_URL = os.getenv("DASHSCOPE_BASE_URL",
                               "https://dashscope.aliyuncs.com/compatible-mode/v1")

# ── Alibaba Cloud ─────────────────────────────────────────────────────────────
ALI_ACCESS_KEY_ID     = os.getenv("ALIBABA_ACCESS_KEY_ID",     "mock-id")
ALI_ACCESS_KEY_SECRET = os.getenv("ALIBABA_ACCESS_KEY_SECRET", "mock-secret")
ALI_REGION            = os.getenv("ALIBABA_REGION", "ap-southeast-1")
OSS_BUCKET            = os.getenv("ALIBABA_OSS_BUCKET", "qwenbridge-storage")
OSS_ENDPOINT          = f"https://oss-{ALI_REGION}.aliyuncs.com"
TABLESTORE_INSTANCE   = os.getenv("ALIBABA_TABLESTORE_INSTANCE", "qwenbridge-memory")
TABLESTORE_ENDPOINT   = os.getenv("ALIBABA_TABLESTORE_ENDPOINT",
                                   "https://qwenbridge-memory.ap-southeast-1.ots.aliyuncs.com")

# ── AgentWorld ────────────────────────────────────────────────────────────────
AGENTWORLD_MODE  = os.getenv("AGENTWORLD_MODE", "offline")
AGENTWORLD_MODEL = os.getenv("AGENTWORLD_MODEL", "Qwen/Qwen-AgentWorld-35B-A3B")
AGENTWORLD_API_URL = os.getenv("AGENTWORLD_API_URL", "http://localhost:8000/v1")

# ── Model IDs (DashScope names) ───────────────────────────────────────────────
MODEL_TURBO        = "qwen-turbo"
MODEL_PLUS         = "qwen-plus"
MODEL_MAX          = "qwen-max"
MODEL_MAX_THINKING = "qwen3-max-thinking"
MODEL_VL_32B       = "qwen-vl-max"
MODEL_CODER        = "qwen-coder-plus"

# ── Server ────────────────────────────────────────────────────────────────────
MCP_HOST  = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
MCP_PORT  = int(os.getenv("MCP_SERVER_PORT", "8765"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
