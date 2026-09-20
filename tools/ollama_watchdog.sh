#!/usr/bin/env bash
# 测试期间 Ollama"显存小偷"看门狗（交接铁律 #2）
# qwen3-vl:4b 会周期性被自动拉起占 5.7GB 显存，测试中途出现即数据失真。
# 用法: bash ollama_watchdog.sh   （后台跑，Ctrl-C/杀进程停）
LOG="D:/agent1super/tmp/bonsai/logs/ollama_watchdog.log"
echo "===== 看门狗启动 $(date '+%F %T') =====" >> "$LOG"
while true; do
  PS=$(curl -s --max-time 5 http://127.0.0.1:11434/api/ps 2>/dev/null)
  if [ -n "$PS" ]; then
    NAMES=$(echo "$PS" | grep -o '"name":"[^"]*"' | cut -d'"' -f4)
    if [ -n "$NAMES" ]; then
      for n in $NAMES; do
        echo "$(date '+%F %T') [拦截] 发现加载模型 $n -> ollama stop" >> "$LOG"
        ollama stop "$n" >/dev/null 2>&1
        echo "$(date '+%F %T') [拦截] stop 返回 rc=$?" >> "$LOG"
      done
    fi
  fi
  sleep 10
done
