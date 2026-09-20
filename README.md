# Ornith-1.5-35B-A3B · RTX 4060 Laptop 8GB 实测调参（llama.cpp turbo4 KV）

> EN: Production start script + measured 0→118K depth curves (PP/TG) for Ornith-1.5-35B-A3B on an 8GB laptop GPU, llama.cpp turbo4 KV cache.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**硬件**：RTX 4060 Laptop 8GB · 32GB DDR5 双通道 · Windows 11 · llama.cpp 系 fork

**量化**：APEX-MTP I-Compact（16.2 GB, mudler imatrix）

**引擎**：**AtomicBot b10269-1.6.0**（llama.cpp fork，turbo4 KV + 多轮工具循环修复）
> 演进：老 TurboQuant fork（PP 102，弃）→ TheTom TQP v0.3.0（turbo4，快但多轮工具循环有 peg-native 400 bug）→ **AtomicBot b10269**（turbo4 全保留 + bug 修复）

## 生产配置（start.bat 即仓库内同名文件，零漂移）

```bat
-ctk turbo4 -ctv turbo4 -b 2816 -ub 2816 --threads 24 --no-mmap --mlock --cache-prompt --ctx-checkpoints 8 --spec-type none --reasoning on --reasoning-budget 2048 --reasoning-preserve --jinja
```

## 实测结果（服务端真实长提示口径）

| 深度 | PP (tok/s) | TG (tok/s) |
|---|---|---|
| 0 (818 tok) | 531 | **46.0** |
| 32K (34K) | 1082 | 34.6 |
| 65K (69K) | 911 | 27.9 |
| 96K (103K) | 904 | 21.5 |
| 118K (120K) | 666 | **19.64** |

## 关键发现

- 服务端真实长提示口径才是真口径：llama-bench pp512 看不见微批伤害（同配置 bench 465 vs 服务端 403→1139，差 2.8 倍）。PP 是决定轴，TG ±15% 不重要。
- turbo4 KV 在 GQA 8:1 层自动把 K 升级为 q8_0（auto-asymmetric，防质量劣化），与 TQP 同款行为。
- 线程数跟着引擎走：TQP 上 t6 最优（ub512 矩阵），AtomicBot b2816 下 t24 > t6。
- 118K 深度 TG 19.64，与 TQP v0.3.0（19.35-19.48）持平略胜；浅层 46.0 比 TQP 40-41 高 12%。
- MTP 头在本机混合卸载下为负优化（接受率 0.89 仍 -14%，验证批次太贵）——三测一致后关掉。
- 多轮工具循环修复：TQP v0.3.0 的 peg-native 解析器在第二轮必 400（上游 #20260 同机理），AtomicBot b10269 构建自带修复，Pi 多轮 write→read 闭环实测通过。

## 复现

```bash
python tools/depth_probe_atomic.py <模型.gguf> <端口> <标签> --depths 0,32768,65536,98304,118784 -ctk turbo4 -ctv turbo4 -b 2816 -ub 2816 --threads 24
python tools/test_engines.py
```

## data/ 与 tools/

`data/` 是全部实测数据（summary_*.txt 为权威深度/预填/矩阵总表，每行带时间戳，可复现）。
`tools/` 是探针与判分脚本（服务端真实长提示口径；llama-bench pp512 在本机与真实负载差 2.8 倍，仅作参考）。

## 姊妹仓库（同机同方法论）

- [kat-coder-35b-8g-tuning](https://github.com/rui08984-dot/kat-coder-35b-8g-tuning)
- [qwen3.6-35b-8g-tuning](https://github.com/rui08984-dot/qwen3.6-35b-8g-tuning)
- [bonsai2-27b-8g-tuning](https://github.com/rui08984-dot/bonsai2-27b-8g-tuning)
- [zhrp-gemma4-26b-8g-tuning](https://github.com/rui08984-dot/zhrp-gemma4-26b-8g-tuning)
- [ornith-9b-kvmem-8g-tuning](https://github.com/rui08984-dot/ornith-9b-kvmem-8g-tuning)

## 致谢

- [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) — 本体
- [TheTom/llama-cpp-turboquant](https://github.com/TheTom/llama-cpp-turboquant) — turbo4 KV 原始 fork
- [AtomicBot-ai/atomic-llama-cpp-turboquant](https://github.com/AtomicBot-ai/atomic-llama-cpp-turboquant) — 现用构建
- [PrismML](https://huggingface.co/PrismML) — Bonsai 三值 QAT
- KVMem — KV-in-RAM 超长上下文引擎

## License

MIT。模型权重遵循各自发布页许可。
