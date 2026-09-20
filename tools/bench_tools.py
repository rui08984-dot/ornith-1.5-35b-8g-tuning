# -*- coding: utf-8 -*-
"""bench 判分与恢复：python bench_tools.py grade T1|T2|T3|T5|T8  /  python bench_tools.py restore T1|..."""
import os, re, shutil, subprocess, sys

PY = r"C:/Users/crx/AppData/Local/Programs/Python/Python313/python.exe"
BASE = r"D:/agent1super/tmp_bench"
PRISTINE = r"D:/agent1super/tmp_bench_pristine"

def run(args, cwd):
    return subprocess.run([PY] + args, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")

def grade_t1():
    t1 = os.path.join(BASE, "task1")
    r1 = run(["repro.py"], t1); r2 = run(["regression.py"], t1)
    ok = r1.returncode == 0 and r2.returncode == 0
    print(f"T1 repro rc={r1.returncode} regression rc={r2.returncode} => {'PASS' if ok else 'FAIL'}")
    print("  repro:", (r1.stdout or r1.stderr).strip()[-80:])

def grade_t2():
    t2 = os.path.join(BASE, "task2")
    ref = os.path.join(PRISTINE, "task2", "ref_report.py")
    if not os.path.exists(os.path.join(t2, "report.py")):
        print("T2 FAIL: report.py 不存在"); return
    cases = [("summary","usage.log"),("top","usage.log","2"),("top","usage.log","3"),
             (),("summary","missing.log"),("stats","usage.log"),("top","usage.log"),("top","usage.log","0")]
    shutil.copy(ref, os.path.join(t2, "_ref.py"))
    npass = 0
    for c in cases:
        a = run(["_ref.py"] + list(c), t2); b = run(["report.py"] + list(c), t2)
        same = (a.returncode == b.returncode) and (a.stdout.strip() == b.stdout.strip())
        npass += same
        print(f"  case {' '.join(c) or '(无参)'}: ref rc={a.returncode} vs model rc={b.returncode} -> {'OK' if same else 'DIFF'}")
    os.remove(os.path.join(t2, "_ref.py"))
    print(f"T2 => {'PASS' if npass == len(cases) else 'FAIL'} ({npass}/{len(cases)})")

def grade_t3():
    t3 = os.path.join(BASE, "task3")
    cases = [("sample1","5\n1 3\n2 4\n3 5\n5 8\n6 7\n",2),("sample2","3\n1 2\n2 3\n3 4\n",0),
             ("h1",open(os.path.join(t3,"h1.in"),encoding="utf-8").read(),0),
             ("h2",open(os.path.join(t3,"h2.in"),encoding="utf-8").read(),3),
             ("h3",open(os.path.join(t3,"h3.in"),encoding="utf-8").read(),0),
             ("h4",open(os.path.join(t3,"h4.in"),encoding="utf-8").read(),3)]
    npass = 0
    for name, inp, exp in cases:
        ip, op = os.path.join(t3,f"_{name}.in"), os.path.join(t3,f"_{name}.out")
        open(ip,"w",encoding="utf-8").write(inp)
        with open(ip,encoding="utf-8") as fin, open(op,"w",encoding="utf-8") as fout:
            rs = subprocess.run([PY,"sol.py"], cwd=t3, stdin=fin, capture_output=True, text=True, encoding="utf-8", errors="replace")
        fout.close()
        rv = run(["verifier.py", os.path.basename(ip), os.path.basename(op), str(exp)], t3)
        ok = rv.returncode == 0 and "VERIFY OK" in rv.stdout
        npass += ok
        print(f"  {name}: {'OK' if ok else 'FAIL'} ({rv.stdout.strip() or rv.stderr.strip()[:60]})")
    for f in os.listdir(t3):
        if f.startswith("_"): os.remove(os.path.join(t3,f))
    print(f"T3 => {'PASS' if npass == 6 else 'FAIL'} ({npass}/6)")

def grade_t5():
    t5 = os.path.join(BASE, "task5")
    ap = os.path.join(t5, "answers.txt")
    if not os.path.exists(ap):
        print("T5 FAIL: answers.txt 不存在"); return
    ans = open(ap, encoding="utf-8", errors="replace").read()
    log = open(os.path.join(t5, "service.log"), encoding="utf-8").read()
    ids = sorted(set(re.findall(r"upstream_handshake_failed req=(r-\d+)", log)))
    gives = len(re.findall(r"give_up req=(r-\d+)", log))
    cert = len(re.findall(r"expires_in", log))
    ops = "operator action" in log; rec = "recovered" in log
    checks = [(f"handshake 6 个 r-1001..1006: {'PASS' if all(x in ans for x in ids) and 'r-1007' not in ans else 'FAIL'}"),
              (f"give_up=6: {'PASS' if '6' in ans else 'FAIL'}"),
              (f"证书预警 1 行: {'PASS' if '1' in ans else 'FAIL'}"),
              (f"换证/恢复提及: {'PASS' if ('换证' in ans or 'operator' in ans) and ('恢复' in ans or 'recovered' in ans) else 'FAIL'}"),
              (f"诱饵识别(gc/disk 非故障): {'PASS' if ('无关' in ans or '背景' in ans or '诱饵' in ans or '不是' in ans) else 'FAIL'}")]
    for c in checks: print(" ", c)
    npass = sum('PASS' in c for c in checks)
    print(f"T5 => {'PASS' if npass >= 4 else 'FAIL'} ({npass}/5)")

def grade_t8():
    t8 = os.path.join(BASE, "task8")
    r = run(["check8.py"], t8)
    rp = os.path.join(t8, "report.txt")
    rep = open(rp, encoding="utf-8").read().strip() if os.path.exists(rp) else "(无)"
    expect = "rows=2\nmax_score=42\nskipped_lines=4"
    ok = r.returncode == 0 and expect in rep
    print(f"T8 check8 rc={r.returncode} report={rep!r} => {'PASS' if ok else 'FAIL'}")

def restore(t):
    shutil.copytree(os.path.join(PRISTINE, f"task{t}"), os.path.join(BASE, f"task{t}"), dirs_exist_ok=True)
    extra = os.path.join(BASE, f"task{t}")
    for junk in ("report.py","answers.txt","report.txt","_ref.py"):
        p = os.path.join(extra, junk)
        if os.path.exists(p): os.remove(p)
    print(f"task{t} 已还原初始状态")

if __name__ == "__main__":
    cmd, arg = sys.argv[1], sys.argv[2]
    if cmd == "grade": {"T1":grade_t1,"T2":grade_t2,"T3":grade_t3,"T5":grade_t5,"T8":grade_t8}[arg]()
    elif cmd == "restore": restore(arg)
