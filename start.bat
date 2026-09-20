@echo off
rem ================================================================
rem  Ornith-1.5-35B-A3B APEX-MTP I-Compact (17.4G, mudler imatrix)
rem  on Thetom turboquant-plus TQP v0.3.0 engine - 2026-09-18 FINAL v2
rem  MEASURED on this 8G/32G machine (all A/B tested):
rem    PP 937.8 @57K depth (turbo4 KV best; q8_0=874, old fork=102)
rem    TG 27.9 @57K depth (43% of 128K), ~36-37 shallow (threads 24/12;
rem  KEY FINDINGS (do not revert):
rem    - --kv-unified + --cache-ram put KV in system RAM = per-token
rem      PCIe reads = TG at depth collapses to 5 t/s. REMOVED.
rem    - turbo4 KV: PP equal-or-better, deep TG +23% vs q8_0.
rem    - MTP OFF (--spec-type none): acceptance 0.15-0.34 = -31~-39%
rem      TG in all scenarios (writing + coding).
rem    - --fit auto-balances GPU layers (no manual ncmoe needed).
rem  RAM note: mlock 17.4G resident (sleep-idle -1, kk style).
rem  If RAM tight: --sleep-idle-seconds -1 -> 600.
rem  Vision: mmproj on CPU (--no-mmproj-offload, zero VRAM cost).
rem    mmproj+MTP coexistence VERIFIED on b10964 (#28715/#28587 fixes);
rem    MTP stays off here for speed, so no crash risk either way.
rem  Alt config for max shallow TG: b10964 (doc section 10, TG 40.2).
rem  ================================================================
cd /d D:\llm\bin\atomic-b10269\pkg\build\bin
llama-server.exe ^
  -m "D:\lmstudio-models\mudler\Ornith-1.5-35B-A3B-APEX-MTP-I-Compact.gguf" ^
  --mmproj "D:\lmstudio-models\mudler\mmproj-ornith-apex.gguf" ^
  --no-mmproj-offload ^
  -c 131072 -np 1 -fa on ^
  -ctk turbo4 -ctv turbo4 ^
  -b 2816 -ub 2816 ^
  --threads 24 --threads-batch 12 ^
  --cache-prompt --ctx-checkpoints 8 --keep -1 ^
  --spec-type none ^
  --reasoning on --reasoning-budget 2048 --reasoning-budget-message "Thinking budget reached; continue to the final answer based on the analysis so far." --reasoning-preserve --jinja --reasoning-format deepseek ^
  --host 127.0.0.1 --port 24555
pause
