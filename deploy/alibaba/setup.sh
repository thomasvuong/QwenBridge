#!/usr/bin/env bash
# deploy/alibaba/setup.sh — Provision Alibaba Cloud infrastructure for QwenBridge
# Run once to create OSS bucket + Table Store instance
set -euo pipefail

REGION="${ALIBABA_REGION:-ap-southeast-1}"
OSS_BUCKET="${ALIBABA_OSS_BUCKET:-qwenbridge-storage}"
TS_INSTANCE="${ALIBABA_TABLESTORE_INSTANCE:-qwenbridge-memory}"

echo "=== QwenBridge Alibaba Cloud Setup ==="
echo "Region:          $REGION"
echo "OSS Bucket:      $OSS_BUCKET"
echo "Table Store:     $TS_INSTANCE"
echo ""

# ── OSS Bucket ────────────────────────────────────────────────────────────────
echo "Creating OSS bucket: $OSS_BUCKET ..."
aliyun oss mb "oss://${OSS_BUCKET}" --region "$REGION" || echo "(bucket may already exist)"
aliyun oss set-bucket-acl "oss://${OSS_BUCKET}" public-read || true

# ── Table Store ───────────────────────────────────────────────────────────────
echo "Creating Table Store instance: $TS_INSTANCE ..."
aliyun ots CreateInstance \
  --InstanceName "$TS_INSTANCE" \
  --ClusterType HYBRID \
  --Description "QwenBridge persistent agent memory" \
  --RegionId "$REGION" || echo "(instance may already exist)"

echo ""
echo "✓ Setup complete."
echo ""
echo "Add to your .env:"
echo "ALIBABA_TABLESTORE_ENDPOINT=https://${TS_INSTANCE}.${REGION}.ots.aliyuncs.com"
