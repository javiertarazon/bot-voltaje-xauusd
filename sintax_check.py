import ast, sys, time
BASE = r"D:\proyectos_javier\proyectos\xauusd-trader"
out, code = "", 0
for f in ("live_demo.py", "live_publish.py"):
    try:
        ast.parse(open(BASE + "\\" + f, encoding="utf-8").read())
        out += f"{f}: SINTAXIS OK\n"
    except SyntaxError as e:
        out += f"{f}: SINTAXIS ERROR linea {e.lineno}: {e.msg}\n"
        code = 1
open(rf"{BASE}\cert_sintax_{int(time.time())}.txt", "w").write(out)
print(out, flush=True)
sys.exit(code)