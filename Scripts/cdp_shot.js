// Screenshot via CDP direto (Node 24, WebSocket global)
const wsUrl = process.argv[2];
const outPath = process.argv[3];
const width = parseInt(process.argv[4] || "1400", 10);
const ws = new WebSocket(wsUrl);
let id = 0;
const pending = new Map();
function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const msgId = ++id;
    pending.set(msgId, { resolve, reject });
    ws.send(JSON.stringify({ id: msgId, method, params }));
  });
}
ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.id && pending.has(msg.id)) {
    const p = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) p.reject(new Error(JSON.stringify(msg.error)));
    else p.resolve(msg.result);
  }
};
ws.onopen = async () => {
  try {
    await send("Page.enable");
    await send("Emulation.setDeviceMetricsOverride", { width, height: 800, deviceScaleFactor: 1, mobile: false });
    await new Promise((r) => setTimeout(r, 2500));
    const { data } = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: true });
    require("fs").writeFileSync(outPath, Buffer.from(data, "base64"));
    console.log("PNG salvo:", outPath);
    ws.close();
    process.exit(0);
  } catch (e) {
    console.error("ERRO:", e.message);
    process.exit(1);
  }
};
ws.onerror = (e) => { console.error("ws error", e.message || e); process.exit(1); };
