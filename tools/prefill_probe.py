# -*- coding: utf-8 -*-
"""服务端真实提示预填充探针（对齐历史 923.8 @19K / 937.8 @57K 的口径）

llama-bench pp512 = 512 token 小批量口径（350-465）
服务端真实长提示 = ub2816 大块口径（900+）
本探针：起 llama-server -> 灌 ~19K token 中文长提示 -> 解析 prompt eval 与 decode 速率 -> 停服

用法: python prefill_probe.py [T0|T3|all]
"""
import json, os, re, subprocess, sys, time, urllib.request

SERVER = r"D:\llm\bin\llama-tqp\llama-server.exe"
MODEL = r"D:\lmstudio-models\mudler\Ornith-1.5-35B-A3B-APEX-MTP-I-Compact.gguf"
LOGDIR = r"D:\agent1super\tmp\tuning\logs"
CORPUS = r"D:\agent1super\tmp\bonsai\logs\ppl_corpus_zh_big.txt"
os.makedirs(LOGDIR, exist_ok=True)

PORT = 24575
CONFIGS = {
    # 现役生产口径（历史 923.8/937.8 就是在这一组测到的）→ 实测 PP 1139
    "T0_base": ["-ctk", "turbo4", "-ctv", "turbo4", "-b", "2816", "-ub", "2816", "-t", "24"],
    # 公开案例组（矩阵浅层冠军）→ 实测 PP 崩到 403（ub512 伤预填实锤）
    "T3_win": ["-ctk", "turbo4", "-ctv", "turbo4", "-b", "2048", "-ub", "512", "-t", "6", "-ncmoe", "35"],
    # 大块+显式卸载 → 实测 PP 926 / TG 39.0（目前最佳平衡）
    "T7_big_ub_ncmoe": ["-ctk", "turbo4", "-ctv", "turbo4", "-b", "4096", "-ub", "2048", "-t", "24", "-ncmoe", "35"],
    # 分解实验：生产批尺寸 + 显式 ncmoe35（隔离卸载策略的影响）
    "T8_prod_ncmoe": ["-ctk", "turbo4", "-ctv", "turbo4", "-b", "2816", "-ub", "2816", "-t", "24", "-ncmoe", "35"],
    # 分解实验：T8 + t6（隔离线程的影响）
    "T9_prod_ncmoe_t6": ["-ctk", "turbo4", "-ctv", "turbo4", "-b", "2816", "-ub", "2816", "-t", "6", "-ncmoe", "35"],
}

def load_prompt(target_chars=30000):
    with open(CORPUS, encoding="utf-8", errors="replace") as f:
        txt = f.read()
    txt = re.sub(r"\s+", "", txt)
    return txt[:target_chars]

def wait_health(timeout=240):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=3) as r:
                if json.loads(r.read().decode()).get("status") == "ok":
                    return True
        except Exception:
            pass
        time.sleep(3)
    return False

def send(prompt, max_tokens):
    body = json.dumps({
        "messages": [{"role": "user", "content": prompt + "\n\n请用一句话说明上面这段文字讲的是什么。"}],
        "max_tokens": max_tokens, "temperature": 0.0, "stream": False,
    }, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=1800) as r:
        resp = json.loads(r.read().decode("utf-8", "replace"))
    return resp, time.time() - t0

def parse_log(path):
    pe = dec = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.search(r"prompt eval time\s*=\s*([\d.]+) ms /\s*(\d+) tokens.*?([\d.]+) tokens per second", line)
            if m:
                pe = (int(m.group(2)), float(m.group(3)), float(m.group(1)))
            m2 = re.search(r"\beval time\s*=\s*([\d.]+) ms /\s*(\d+) tokens.*?([\d.]+) tokens per second", line)
            if m2 and "prompt" not in line:
                dec = (int(m2.group(2)), float(m2.group(3)))
    return pe, dec

def run(tag, params, prompt, max_tokens=256):
    log = os.path.join(LOGDIR, f"srvprobe2_{tag}.log")
    # ⚠️ 不能带 -ngl/-fitt：会让 --fit 直接 abort（实测预填掉到 55-97 t/s）。
    # 生产 bat 也不带 → 完全对齐生产。
    cmd = [SERVER, "-m", MODEL, "-fa", "on",
           "-c", "40960", "-np", "1", "--no-mmap", "--mlock",
           "--cache-prompt", "--spec-type", "none", "--reasoning", "off",
           "--jinja", "--host", "127.0.0.1", "--port", str(PORT)] + params
    print(f"\n>>> [{tag}] 启动: {' '.join(params)}")
    with open(log, "w", encoding="utf-8") as lf:
        proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT)
    try:
        if not wait_health():
            print(f"[{tag}] 健康检查超时"); return
        print(f"[{tag}] 已就绪，灌入 {len(prompt)} 字中文长提示…")
        resp, wall = send(prompt, max_tokens)
        time.sleep(2)
        pe, dec = parse_log(log)
        print(f"[{tag}] 请求墙钟 {wall:.1f}s | 提示 token={pe[0] if pe else '?'} "
              f"预填={pe[1] if pe else '?'} t/s | 解码={dec[1] if dec else '?'} t/s")
        with open(os.path.join(LOGDIR, "summary_prefill.txt"), "a", encoding="utf-8") as sf:
            sf.write(f"PREFILL {tag} prompt_tok={pe[0] if pe else -1} PP={pe[1] if pe else -1} "
                     f"TG={dec[1] if dec else -1} wall={wall:.1f}s {time.strftime('%F %T')}\n")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            proc.kill()
        time.sleep(3)

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    prompt = load_prompt()
    tags = list(CONFIGS) if which == "all" else [which]
    for t in tags:
        run(t, CONFIGS[t], prompt)
    print("\n===== 完成 =====")
