# -*- coding: utf-8 -*-
"""服务端深度曲线探针：在指定深度灌长提示 -> 测 PP 与同深度 TG（真实工作负载口径）

用法: python depth_probe.py <模型路径> <端口> <标签> [--depths 0,32768,65536] [-- 额外参数...]
"""
import json, os, re, subprocess, sys, time, urllib.request

SERVER = r"D:\llm\bin\llama-tqp\llama-server.exe"
LOGDIR = r"D:\agent1super\tmp\tuning\logs"
CORPUS = r"D:\agent1super\tmp\bonsai\logs\ppl_corpus_zh_big.txt"
os.makedirs(LOGDIR, exist_ok=True)

def load_corpus_chars(n_chars):
    with open(CORPUS, encoding="utf-8", errors="replace") as f:
        txt = re.sub(r"\s+", "", f.read())
    if not txt:
        raise SystemExit("语料为空")
    rep = (n_chars // len(txt)) + 1
    return (txt * rep)[:n_chars]

def wait_health(port, timeout=360):
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=3) as r:
                if json.loads(r.read().decode()).get("status") == "ok":
                    return True
        except Exception:
            pass
        time.sleep(3)
    return False

def send(port, prompt, max_tokens):
    body = json.dumps({"messages": [{"role": "user", "content": prompt + "\n\n请用一句话说明上面这段文字讲的是什么。"}],
                       "max_tokens": max_tokens, "temperature": 0.0, "stream": False},
                      ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions", data=body,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=3600) as r:
        resp = json.loads(r.read().decode("utf-8", "replace"))
    return resp, time.time() - t0

def parse_log(path):
    pe = dec = None
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m = re.search(r"prompt eval time\s*=\s*([\d.]+) ms /\s*(\d+) tokens.*?([\d.]+) tokens per second", line)
            if m: pe = (int(m.group(2)), float(m.group(3)))
            m2 = re.search(r"(?<!prompt )eval time\s*=\s*([\d.]+) ms /\s*(\d+) tokens.*?([\d.]+) tokens per second", line)
            if m2: dec = (int(m2.group(2)), float(m2.group(3)))
    return pe, dec

def main():
    model, port, tag = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    rest = sys.argv[4:]
    depths = [0, 32768, 65536, 118784]
    extra = []
    i = 0
    while i < len(rest):
        if rest[i] == "--depths" and i + 1 < len(rest):
            depths = [int(x) for x in rest[i+1].split(",")]
            i += 2
        else:
            extra.append(rest[i])
            i += 1
    log = os.path.join(LOGDIR, f"depth_{tag}.log")

    # 中文实测 ~1.6 字/token；关掉 prompt cache 防止重复语料被缓存复用（否则深度不起作用）
    maxdepth = max(depths)
    cmd = [SERVER, "-m", model, "-fa", "on", "-c", str(maxdepth + 8192), "-np", "1",
           "--cache-ram", "0", "--spec-type", "none", "--reasoning", "off",
           "--jinja", "--host", "127.0.0.1", "--port", str(port)] + extra
    print(f">>> 深度探针 [{tag}] 深度={depths} 参数={extra}")
    with open(log, "w", encoding="utf-8") as lf:
        proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT)
    try:
        t0 = time.time()
        if not wait_health(port):
            print("[FAIL] 加载失败，日志:", log); return
        print(f"[OK] 加载 {time.time()-t0:.0f}s")
        for d in depths:
            # 每 token 字数可由环境变量覆盖：gemma4 中文 tokenizer 实测 ~0.75 字/token（KAT qwen 系 1.65）
            cpt = float(os.environ.get("PROBE_CHARS_PER_TOKEN", "1.65"))
            n_chars = int(d * cpt) if d > 0 else 1200
            prompt = load_corpus_chars(max(n_chars, 1200))
            resp, wall = send(port, prompt, 128)
            time.sleep(2)
            pe, dec = parse_log(log)
            pp = pe[1] if pe else -1
            tg = dec[1] if dec else -1
            ntok = pe[0] if pe else -1
            line = f"DEPTH {tag} d={d} prompt_tok={ntok} PP={pp} TG={tg} wall={wall:.1f}s {time.strftime('%F %T')}"
            print(line)
            with open(os.path.join(LOGDIR, "summary_depth.txt"), "a", encoding="utf-8") as sf:
                sf.write(line + "\n")
    finally:
        proc.terminate()
        try: proc.wait(timeout=20)
        except subprocess.TimeoutExpired: proc.kill()
        time.sleep(3)

if __name__ == "__main__":
    main()
