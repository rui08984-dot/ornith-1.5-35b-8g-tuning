import json, os, subprocess, sys, time, urllib.request

ENGINES = [
    ("KAT-Coder 35B",  r"D:\llm\llama-cpp-turboquant\start-KAT.bat",       24558),
    ("Ornith 35B",     r"D:\llm\llama-cpp-turboquant\start-Ornith.bat",    24555),
    ("Qwen3.6 35B",    r"D:\llm\llama-cpp-turboquant\start-35B.bat",       24551),
    ("Bonsai-2 27B",   r"D:\llm\llama-cpp-turboquant\start-Bonsai2.bat",   24557),
    ("zh-RP 26B",      r"D:\llm\llama-cpp-turboquant\start-zhRP.bat",      24561),
    ("9B KVMem",       r"D:\llm\llama-cpp-turboquant\start-9B-longctx.bat",24560),
]
TOOLS = [{"type":"function","function":{"name":"get_weather","description":"查询指定城市当前天气",
          "parameters":{"type":"object","properties":{"city":{"type":"string","description":"城市名"}},"required":["city"]}}}]

def kill_all():
    for exe in ("llama-server.exe","llama-kvmem-server.exe"):
        subprocess.run(["taskkill","/F","/IM",exe], capture_output=True)
    time.sleep(2)

def get(url, timeout=3):
    try:
        r = urllib.request.urlopen(url, timeout=timeout)
        return r.status, r.read()
    except Exception as e:
        return None, str(e).encode()

def post_chat(port, body, timeout=90):
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/v1/chat/completions",
            data=json.dumps(body).encode("utf-8"), headers={"Content-Type":"application/json"})
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, json.loads(r.read())
    except Exception as e:
        return None, str(e)

def test(idx):
    name, bat, port = ENGINES[idx]
    kill_all()
    os.startfile(bat)
    # 健康轮询
    up, waited = False, 0
    while waited < 180:
        time.sleep(3); waited += 3
        st, _ = get(f"http://127.0.0.1:{port}/health", 2)
        if st == 200: up = True; break
    if not up:
        print(f"❌ {name}: 健康检查 {waited}s 超时"); return
    # WebUI 检查
    st, body = get(f"http://127.0.0.1:{port}/", 12)
    webui = "✅" if st == 200 and b"<" in body[:200] else f"⚠️{st}"
    # Pi 形态请求：tools + samplingParams + 中文
    body = {"messages":[{"role":"system","content":"You are a helpful assistant. Use tools when needed."},
            {"role":"user","content":"北京今天天气怎么样？必须调用 get_weather 工具查询。"}],
            "tools": TOOLS, "tool_choice":"auto", "max_tokens":300, "stream":False,
            "temperature":0.6, "top_p":0.95, "top_k":20, "min_p":0}
    st, resp = post_chat(port, body)
    if st != 200:
        print(f"❌ {name}: 对话请求失败 HTTP {st} — {str(resp)[:150]}")
    else:
        ch = resp["choices"][0]; msg = ch["message"]
        tc = msg.get("tool_calls")
        content = (msg.get("content") or "")[:60].replace("\n"," ")
        if tc: tool = f"✅ 工具调用 {tc[0]['function']['name']}({tc[0]['function'].get('arguments','')[:40]})"
        else: tool = f"⚠️ 无工具调用(直接文本: {content}...)"
        print(f"✅ {name}: 对话 OK | WebUI {webui} | {tool}")

for i in [int(x) for x in sys.argv[1:]]:
    test(i)
kill_all()
print("=== 批次结束，全部引擎已停 ===")
