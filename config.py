import os
from dotenv import load_dotenv

load_dotenv()

# ── DashScope ─────────────────────────────────────────────────────────────────
DASHSCOPE_API_KEY   = os.environ["DASHSCOPE_API_KEY"]
DASHSCOPE_BASE_URL  = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")

# ── Alibaba Cloud ─────────────────────────────────────────────────────────────
ALI_ACCESS_KEY_ID     = os.environ["ALIBABA_ACCESS_KEY_ID"]
ALI_ACCESS_KEY_SECRET = os.environ["ALIBABA_ACCESS_KEY_SECRET"]
ALI_REGION            = os.getenv("ALIBABA_REGION", "ap-southeast-1")
OSS_BUCKET            = os.getenv("ALIBABA_OSS_BUCKET", "qwenbridge-storage")
OSS_ENDPOINT          = f"https://oss-{ALI_REGION}.aliyuncs.com"
TABLESTORE_INSTANCE   = os.getenv("ALIBABA_TABLESTORE_INSTANCE", "qwenbridge-memory")
TABLESTORE_ENDPOINT   = os.environ["ALIBABA_TABLESTORE_ENDPOINT"]

# ── AgentWorld ────────────────────────────────────────────────────────────────
AGENTWORLD_MODE       = os.getenv("AGENTWORLD_MODE", "api")
AGENTWORLD_MODEL      = os.getenv("AGENTWORLD_MODEL", "Qwen/Qwen-AgentWorld-35B-A3B")
AGENTWORLD_API_URL    = os.getenv("AGENTWORLD_API_URL", "http://localhost:8000/v1")

# ── Model IDs (DashScope names) ───────────────────────────────────────────────
MODEL_TURBO          = "qwen-turbo"           # $0.05/$0.20 per 1M
MODEL_PLUS           = "qwen-plus"            # $0.40/$1.20 per 1M
MODEL_MAX            = "qwen-max"             # $1.60/$6.40 per 1M
MODEL_MAX_THINKING   = "qwen3-max-thinking"   # $1.20/$6.00 per 1M (reasoning)
MODEL_VL_32B         = "qwen-vl-max"          # vision, $0.16/$0.64 per 1M
MODEL_CODER          = "qwen-coder-plus"      # code, $0.30/$1.50 per 1M

# ── Server ────────────────────────────────────────────────────────────────────
MCP_HOST = os.getenv("MCP_SERVER_HOST", "0.0.0.0")
MCP_PORT = int(os.getenv("MCP_SERVER_PORT", "8765"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
