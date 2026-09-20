#!/usr/bin/env bash
# Bonsai-2 调优测试 - 环境闸门检查
# 用法: bash check_env.sh
# 退出码: 0=可以开测, 1=环境不干净（需先处理）

set -u
MODEL_DIR="D:/lmstudio-models"
echo "===== Bonsai-2 测试环境闸门 $(date '+%Y-%m-%d %H:%M:%S') ====="

FAIL=0

# 1) 有没有 llama/ollama 模型进程
echo "--- [1] 进程检查 ---"
PROCS=$(powershell -NoProfile -Command 'Get-Process | Where-Object { $_.ProcessName -match "llama|ollama" } | ForEach-Object { $_.ProcessName }' 2>/dev/null | tr -d '\r')
if [ -n "$PROCS" ]; then
  echo "发现进程: $PROCS"
  # ollama 托盘常驻是正常的，llama-server 才是问题
  if echo "$PROCS" | grep -q "llama-server"; then
    echo "[FAIL] 有 llama-server 在跑，先停掉"
    FAIL=1
  else
    echo "[ok] 只有 ollama 托盘（正常）"
  fi
else
  echo "[ok] 无相关进程"
fi

# 2) ollama 里有没有加载模型（视觉模型会吃 4G 显存）
echo "--- [2] Ollama 已加载模型 ---"
PS=$(curl -s --max-time 5 http://127.0.0.1:11434/api/ps 2>/dev/null)
if [ -n "$PS" ]; then
  NAMES=$(echo "$PS" | C:/Users/crx/AppData/Local/Programs/Python/Python313/python.exe -c "import json,sys;d=json.load(sys.stdin);print(' '.join(m['name'] for m in d.get('models',[])))" 2>/dev/null)
  if [ -n "$NAMES" ]; then
    echo "[WARN] 已加载: $NAMES -> 执行 ollama stop"
    for n in $NAMES; do ollama stop "$n" 2>/dev/null; done
    sleep 3
  else
    echo "[ok] 无已加载模型"
  fi
else
  echo "[ok] Ollama 未响应（未运行或已空闲）"
fi

# 3) 显存空闲量
echo "--- [3] GPU 显存 ---"
GPU=$(nvidia-smi --query-gpu=memory.used,memory.total,utilization.gpu --format=csv,noheader 2>/dev/null | tr -d '\r')
echo "当前: $GPU"
USED=$(echo "$GPU" | cut -d, -f1 | tr -dc '0-9')
if [ "${USED:-9999}" -gt 1000 ]; then
  echo "[WARN] 显存占用 ${USED}MiB > 1000MiB，找一下大户："
  nvidia-smi 2>/dev/null | sed -n '/Processes/,$p' | head -20
  echo "  （桌面程序占用属正常波动；>1500MiB 建议先关 Edge/QQ/壁纸引擎）"
else
  echo "[ok] 显存空闲良好"
fi

# 4) 磁盘空间
echo "--- [4] D 盘空间 ---"
DF=$(df -h /d 2>/dev/null | tail -1)
echo "$DF"
AVAIL=$(echo "$DF" | awk '{print $4}' | tr -dc '0-9')
UNIT=$(echo "$DF" | awk '{print $4}' | tr -dc 'A-Z')
if [ "$UNIT" = "G" ] && [ "${AVAIL:-0}" -lt 15 ]; then
  echo "[WARN] D 盘空闲 < 15G"
else
  echo "[ok]"
fi

# 5) 引擎/模型在位
echo "--- [5] 资产检查 ---"
for f in "D:/llm/bin/llama-prism/llama-bench.exe" "D:/llm/bin/llama-prism/llama-server.exe" "D:/llm/bin/llama-prism/llama-kv-mean-center.exe" "$MODEL_DIR/Ternary-Bonsai-2-27B-PTQ1_0.gguf"; do
  if [ -f "$f" ]; then echo "[ok] $f"; else echo "[FAIL] 缺失: $f"; FAIL=1; fi
done

# 6) 引擎更新探测（b10687 Windows CUDA 包是否已上传）
echo "--- [6] 引擎更新探测 (b10687) ---"
CODE=$(curl -sIL -o /dev/null -w "%{http_code}" --max-time 20 "https://github.com/PrismML-Eng/llama.cpp/releases/download/prism-b10687-5d80cff/llama-prism-b10687-5d80cff-bin-win-cuda-12.4-x64.zip" 2>/dev/null)
if [ "$CODE" = "200" ]; then
  echo "[!!] b10687 Windows 包已上传！可下载替换（仅 llama-prism 目录）"
else
  echo "[ok] 尚未上传 (HTTP $CODE)，继续用 b10685"
fi

echo "===== 结论 ====="
if [ "$FAIL" -eq 0 ]; then echo "环境可测 ✔"; exit 0; else echo "环境不干净 ✘（见 FAIL 项）"; exit 1; fi
