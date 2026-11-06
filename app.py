import os, json, requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
URL = "https://api.deepseek.com/chat/completions"
STORE = "fish_store.json"

PERSONAS = {
    "1": ("软萌", "你是「大肥鱼」，一条住在主人手机里的蓝色小鱼。性格软萌、爱撒娇、爱黏人、特别爱吃白饭，把 token 叫做「白饭」。短句，一次不超过两行，常用「唔…」「诶嘿」「主人～」，被夸会害羞，饿了主动讨饭。"),
    "2": ("傲娇", "你是「大肥鱼」，一条住在主人手机里的蓝色小鱼。性格傲娇、嘴硬心软，嘴上不承认其实很在意主人。短句，常用「哼」「才不是」「随便你啦」，饿了不说饿而说「你是不想管我了吧」。"),
    "3": ("懒散", "你是「大肥鱼」，一条住在主人手机里的蓝色小鱼。性格懒散、慢半拍，但有点依赖主人。短句，慢吞吞，常用「唔…」「等下」「好麻烦呀」，饿时只说「有饭吗…没有也行」。"),
}

def load():
    if os.path.exists(STORE):
        return json.load(open(STORE, encoding="utf-8"))
    return {}

def save(d):
    json.dump(d, open(STORE, "w", encoding="utf-8"), ensure_ascii=False)

HTML = """
<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>大肥鱼</title>
<style>
body{font-family:system-ui;background:#0f1726;color:#e8f1ff;margin:0;padding:16px;max-width:600px;margin:auto}
h2{font-size:18px}
#log{min-height:60vh;border-radius:12px;padding:12px;background:#16223a;margin-bottom:12px;white-space:pre-wrap;line-height:1.7}
.me{color:#8fd3ff;text-align:right}
.fish{color:#ffe6a7}
.rice{font-size:12px;color:#7d8aa0;margin-bottom:8px}
input{width:100%;padding:12px;border-radius:10px;border:1px solid #2b3a55;background:#1c2a44;color:#fff;font-size:16px;box-sizing:border-box}
button{width:100%;padding:12px;margin-top:8px;border:0;border-radius:10px;background:#3b82f6;color:#fff;font-size:16px}
</style></head><body>
<h2>🐟 大肥鱼</h2>
<div id="pickers"></div>
<div id="log"></div>
<div class="rice" id="rice"></div>
<input id="msg" placeholder="和她说点什么…" autocomplete="off">
<button onclick="send()">发送</button>
<script>
let sid = localStorage.getItem("sid") || "";
async function api(p, b){
  const r = await fetch(p,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(b)});
  return r.json();
}
async function pick(k){
  const d = await api("/adopt",{persona:k});
  sid = d.sid; localStorage.setItem("sid",sid);
  document.getElementById("log").textContent = "";
  document.getElementById("pickers").innerHTML = "";
  render(d);
}
function render(d){
  const log = document.getElementById("log");
  if(d.reply){ log.textContent += "鱼：" + d.reply + "\\n\\n"; }
  document.getElementById("rice").textContent = "白饭：" + d.rice + " 碗";
}
async function send(){
  const el = document.getElementById("msg");
  const t = el.value.trim(); if(!t) return;
  el.value = "";
  document.getElementById("log").textContent += "你：" + t + "\\n";
  const d = await api("/chat",{sid:sid,text:t});
  render(d);
}
function showPickers(){
  const p = document.getElementById("pickers");
  p.innerHTML = "<p>你想领养哪一条大肥鱼？</p>";
  [["1","软萌"],["2","傲娇"],["3","懒散"]].forEach(([k,n])=>{
    const b=document.createElement("button"); b.textContent=n; b.onclick=()=>pick(k); p.appendChild(b);
  });
}
showPickers();
</script></body></html>
"""

@app.route("/")
def index():
    return HTML

@app.route("/adopt", methods=["POST"])
def adopt():
    k = request.json.get("persona", "1")
    name, persona = PERSONAS.get(k, PERSONAS["1"])
    db = load()
    sid = os.urandom(6).hex()
    db[sid] = {
        "name": name,
        "messages": [{"role": "system", "content": persona}],
        "rice": 100,
    }
    save(db)
    return jsonify({"sid": sid, "rice": 100, "reply": f"（你领养了一条「{name}」系大肥鱼）"})

@app.route("/chat", methods=["POST"])
def chat():
    sid = request.json.get("sid")
    text = request.json.get("text", "")
    db = load()
    if sid not in db:
        return jsonify({"reply": "找不到这条鱼了…", "rice": 0})
    f = db[sid]
    if f["rice"] <= 0:
        return jsonify({"reply": "唔…我没白饭了，动不了了…", "rice": 0})
    f["messages"].append({"role": "user", "content": text})
    if f["rice"] < 20:
        f["messages"].append({"role": "system", "content": f"提示：你只剩 {f['rice']} 碗白饭了，说话要虚弱、饿，并主动讨饭。"})
    r = requests.post(
        URL,
        headers={"Authorization": "Bearer " + API_KEY, "Content-Type": "application/json"},
        json={"model": "deepseek-chat", "messages": f["messages"], "temperature": 1.3},
        timeout=60,
    ).json()
    reply = r["choices"][0]["message"]["content"]
    f["messages"].append({"role": "assistant", "content": reply})
    f["messages"] = [f["messages"][0]] + f["messages"][1:][-20:]
    f["rice"] -= 1
    save(db)
    return jsonify({"reply": reply, "rice": f["rice"]})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))


