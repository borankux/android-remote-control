import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const RELAY_BASE = "/cloudphone-relay";
const DEFAULT_REFRESH_MS = 5000;
const DEFAULT_DEVICE_ID = "demo-device-id";
const DEFAULT_STREAM_FPS = 2;
const BOOST_STREAM_FPS = 5;
const BOOST_STREAM_MS = 3000;
const COVER_REFRESH_MS = 60_000;

const FALLBACK_PRESETS = {
  crisp: { format: "jpeg", maxWidth: 720, quality: 80 },
  balanced: { format: "jpeg", maxWidth: 540, quality: 65 },
  smooth: { format: "jpeg", maxWidth: 360, quality: 45 },
};

const QUALITY_LABELS = {
  auto: "自动",
  crisp: "清晰",
  balanced: "均衡",
  smooth: "流畅",
};

const STREAM_BOOST_COMMANDS = new Set([
  "tap",
  "swipe",
  "long_press",
  "back",
  "home",
  "input_text",
  "clear_text",
  "launch_app",
  "launch_xhs",
]);

function tokenFromLocation() {
  const hash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const query = new URLSearchParams(window.location.search);
  return hash.get("token") || query.get("token") || "";
}

function publicOrigin() {
  return window.location.origin || "https://relay.example.com";
}

function timeText(value) {
  if (!value) return "N/A";
  return new Date(value).toLocaleTimeString("zh-CN", { hour12: false });
}

function relativeText(value) {
  if (!value) return "N/A";
  const seconds = Math.max(0, Math.round((Date.now() - new Date(value).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${Math.round(seconds / 3600)}h`;
}

function shortId(id) {
  if (!id) return "N/A";
  return id.length > 10 ? `${id.slice(0, 6)}…${id.slice(-4)}` : id;
}

function mjpegStreamUrl(token, deviceId, mode, fps, nonce, viewerId) {
  if (!token || !deviceId) return "";
  const params = new URLSearchParams({
    token,
    mode,
    fps: String(fps),
    t: String(nonce),
    viewer: viewerId,
  });
  return `${RELAY_BASE}/stream/mjpeg/${encodeURIComponent(deviceId)}?${params.toString()}`;
}

function commandSummary(command) {
  const result = command?.result;
  if (!result) return command?.error || command?.status || "无结果";
  if (command.name === "screencap") return `${result.mimeType || "image"} · ${Math.round((result.byteCount || 0) / 1024)} KB`;
  if (command.name === "dump_ui") return `UI XML · ${result.charCount || 0} 字符`;
  if (command.name === "snapshot") return result.focus || result.display || "状态已刷新";
  if (command.name === "wait_for_text") return result.matched ? `找到「${result.text}」` : `未找到「${result.text}」`;
  if (result.packageName) return `启动 ${result.packageName}`;
  if (result.x !== undefined && result.y !== undefined) return `点击 ${result.x}, ${result.y}`;
  if (result.serviceAdbTcpPort !== undefined) return `ADB ${result.connectable ? "可连接" : "不可连接"} · ${result.serviceAdbTcpPort || "N/A"}`;
  return result.ok === false ? result.error || "失败" : "执行成功";
}

function parseFocus(focus) {
  const text = String(focus || "");
  const match = text.match(/u0\s+([^\s}]+)/);
  return match?.[1] || text.split("\n")[0] || "N/A";
}

function useRelayApi(token) {
  return useMemo(() => {
    async function request(path, options = {}) {
      const response = await fetch(`${RELAY_BASE}${path}`, {
        ...options,
        headers: {
          "x-relay-token": token,
          "content-type": "application/json",
          ...(options.headers || {}),
        },
      });
      const body = await response.text();
      let json;
      try {
        json = JSON.parse(body);
      } catch {
        throw new Error(`响应不是 JSON: ${body.slice(0, 120)}`);
      }
      if (!response.ok || json.ok === false) throw new Error(json.error || `HTTP ${response.status}`);
      return json;
    }

    async function runCommand(deviceId, name, params = {}, timeoutMs = 30000) {
      const created = await request("/commands", {
        method: "POST",
        body: JSON.stringify({ deviceId, name, params }),
      });
      const commandId = created.command.id;
      const started = performance.now();
      while (performance.now() - started < timeoutMs) {
        const json = await request(`/commands/${encodeURIComponent(commandId)}`);
        const command = json.command;
        if (["completed", "failed", "offline"].includes(command.status)) return command;
        await new Promise((resolve) => setTimeout(resolve, 450));
      }
      throw new Error(`命令超时: ${commandId}`);
    }

    return { request, runCommand };
  }, [token]);
}

function AuthGate() {
  return (
    <main className="auth-screen">
      <section className="auth-card">
        <p className="kicker">Cloudphone Console</p>
        <h1>缺少访问令牌</h1>
        <p>使用带 token 的入口打开控制台。</p>
        <code>https://your-domain.example/cloudphone-console/#token=&lt;relay-token&gt;</code>
      </section>
    </main>
  );
}

function ListPage({ devices, thumbnails, coverRefreshing, onRefresh, onRefreshThumbs, onRefreshThumb, onOpen, error }) {
  const onlineCount = devices.filter((device) => device.online).length;
  const rootCount = devices.filter((device) => device.hello?.rootAvailable).length;
  const coverCount = devices.filter((device) => thumbnails[device.deviceId]?.image).length;
  const latest = devices.reduce((acc, device) => {
    if (!acc) return device;
    return new Date(device.lastSeenAt) > new Date(acc.lastSeenAt) ? device : acc;
  }, null);

  return (
    <main className="workspace list-workspace">
      <section className="fleet-console">
        <div className="fleet-head">
          <div>
            <p className="kicker">PB Relay Fleet</p>
            <h1>云手机设备</h1>
          </div>
          <div className="hero-actions">
            <button onClick={onRefresh}>刷新设备</button>
            <button className="primary" onClick={onRefreshThumbs}>
              {coverRefreshing ? "正在刷新封面" : "刷新全部封面"}
            </button>
          </div>
        </div>

        <div className="fleet-metrics">
          <Metric label="在线设备" value={`${onlineCount}/${devices.length}`} />
          <Metric label="Root 可用" value={rootCount} />
          <Metric label="封面缓存" value={`${coverCount}/${devices.length}`} />
          <Metric label="最近心跳" value={latest ? relativeText(latest.lastSeenAt) : "N/A"} />
        </div>
      </section>

      {error && <div className="toast-error">{error}</div>}

      <section className="device-table">
        <div className="device-table-head">
          <span>封面</span>
          <span>设备</span>
          <span>能力</span>
          <span>连接</span>
          <span>操作</span>
        </div>
        <div className="device-table-body">
          {devices.map((device) => (
            <DeviceRow
              key={device.deviceId}
              device={device}
              thumbnail={thumbnails[device.deviceId]}
              onRefreshThumb={() => onRefreshThumb(device)}
              onOpen={() => onOpen(device.deviceId)}
            />
          ))}
          {devices.length === 0 && (
            <div className="empty-state">
              <strong>没有设备在线</strong>
              <span>确认云手机 App 已开启 Relay。</span>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function DeviceRow({ device, thumbnail, onRefreshThumb, onOpen }) {
  const hello = device.hello || {};
  return (
    <article className="device-row">
      <button className="cover-cell" onClick={onRefreshThumb} title="刷新封面">
        <div className="cover-phone">
          {thumbnail?.image ? <img src={thumbnail.image} alt={`${device.deviceId} screen`} /> : <span>无封面</span>}
        </div>
        <small>{thumbnail?.updatedAt ? `${relativeText(thumbnail.updatedAt)} 前` : "点击生成"}</small>
      </button>

      <div className="device-main">
        <div className="device-title-line">
          <strong>{hello.model || "Unknown Device"}</strong>
          <span className={device.online ? "pill online" : "pill offline"}>{device.online ? "在线" : "离线"}</span>
        </div>
        <span className="mono-id">{device.deviceId}</span>
        <span className="device-subline">
          {hello.manufacturer || "N/A"} · Android {hello.androidVersion || "N/A"} · SDK {hello.sdkInt || "N/A"}
        </span>
      </div>

      <div className="capability-stack">
        <span className={hello.rootAvailable ? "cap ok" : "cap muted"}>Root {hello.rootAvailable ? "可用" : "未知"}</span>
        <span className="cap">App {hello.appVersion || "N/A"}</span>
        <span className="cap muted">ABI {hello.abis?.split(",")?.[0] || "N/A"}</span>
      </div>

      <div className="connection-stack">
        <strong>{relativeText(device.lastSeenAt)} 前</strong>
        <span>{device.remoteAddress || "N/A"}</span>
        <span>默认 {device.deviceId === DEFAULT_DEVICE_ID ? "是" : "否"}</span>
      </div>

      <div className="row-actions">
        <button onClick={onRefreshThumb}>封面</button>
        <button className="primary" onClick={onOpen}>详情</button>
      </div>
    </article>
  );
}

function DetailPage({
  device,
  snapshot,
  streamSrc,
  streamEnabled,
  streamFps,
  streamEffectiveFps,
  streamError,
  logs,
  busy,
  error,
  qualityMode,
  activeQuality,
  manual,
  onBack,
  onQuality,
  onStreamEnabled,
  onStreamFps,
  onStreamError,
  onStreamReload,
  onManual,
  onCommand,
  onRefreshScreen,
  onCopyConnection,
  onClearLogs,
}) {
  const hello = device.hello || {};
  const currentFocus = parseFocus(logs.find((item) => item.kind === "snapshot")?.rawFocus);

  return (
    <main className="workspace detail-workspace">
      <header className="detail-top">
        <button className="ghost" onClick={onBack}>返回列表</button>
        <div>
          <p className="kicker">Device Session</p>
          <h1>{hello.model || device.deviceId}</h1>
        </div>
        <button className="primary" onClick={onCopyConnection}>复制 Agent 提示词</button>
      </header>

      {error && <div className="toast-error detail-error">{error}</div>}

      <section className="detail-grid">
        <aside className="left-rail">
          <section className="status-panel">
            <div className="status-title">
              <span className={device.online ? "status-dot on" : "status-dot"} />
              <strong>{device.online ? "Relay 在线" : "Relay 离线"}</strong>
              <small>{relativeText(device.lastSeenAt)} 前</small>
            </div>
            <div className="status-list">
              <InfoRow label="设备 ID" value={device.deviceId} />
              <InfoRow label="App" value={hello.appVersion || "N/A"} />
              <InfoRow label="系统" value={`Android ${hello.androidVersion || "N/A"} / SDK ${hello.sdkInt || "N/A"}`} />
              <InfoRow label="Root" value={hello.rootAvailable ? "可用" : "未知"} />
              <InfoRow label="来源 IP" value={device.remoteAddress || "N/A"} />
              <InfoRow label="焦点" value={currentFocus} />
              <InfoRow label="画质" value={`${QUALITY_LABELS[qualityMode]} · ${QUALITY_LABELS[activeQuality]}`} />
              <InfoRow label="预览" value={streamEnabled ? `${streamEffectiveFps}fps` : "已暂停"} />
            </div>
          </section>

          <section className="controls-panel">
            <div className="panel-head">
              <strong>控制</strong>
              <span>{busy || "空闲"}</span>
            </div>
            <div className="command-row">
              <button onClick={() => onCommand("launch_xhs", {}, "启动小红书")}>启动小红书</button>
              <button onClick={() => onCommand("home", {}, "Home")}>Home</button>
              <button onClick={() => onCommand("back", {}, "Back")}>Back</button>
              <button onClick={() => onCommand("snapshot", {}, "刷新状态")}>状态</button>
              <button onClick={() => onCommand("dump_ui", {}, "dump UI")}>UI</button>
              <button onClick={() => onCommand("adb_status", {}, "ADB 状态")}>ADB</button>
            </div>
            <div className="manual-controls">
              <input placeholder="x" value={manual.x} onChange={(event) => onManual({ ...manual, x: event.target.value })} />
              <input placeholder="y" value={manual.y} onChange={(event) => onManual({ ...manual, y: event.target.value })} />
              <button onClick={() => onCommand("tap", { x: Number(manual.x), y: Number(manual.y) }, "点击")}>点击</button>
              <input className="text-input" placeholder="文本 / 等待文本" value={manual.text} onChange={(event) => onManual({ ...manual, text: event.target.value })} />
              <button onClick={() => onCommand("input_text", { text: manual.text }, "输入文本")}>输入</button>
              <button onClick={() => onCommand("wait_for_text", { text: manual.text, timeoutMs: 5000 }, "等待文本")}>等待</button>
            </div>
          </section>

          <section className="log-panel">
            <div className="panel-head">
              <strong>动作日志</strong>
              <button className="ghost small" onClick={onClearLogs}>清空</button>
            </div>
            <div className="log-stack">
              {logs.slice(0, 7).map((item) => (
                <article className={`event ${item.status === "成功" ? "success" : "failed"}`} key={item.id}>
                  <time>{item.at.toLocaleTimeString("zh-CN", { hour12: false })}</time>
                  <strong>{item.action}</strong>
                  <span>{item.status} · {item.durationMs}ms</span>
                  <p>{item.detail}</p>
                </article>
              ))}
              {logs.length === 0 && <div className="quiet">还没有来自控制台的动作。</div>}
            </div>
          </section>
        </aside>

        <section className="phone-stage">
          <div className="phone-tools">
            <select value={qualityMode} onChange={(event) => onQuality(event.target.value)}>
              <option value="auto">自动画质</option>
              <option value="crisp">清晰</option>
              <option value="balanced">均衡</option>
              <option value="smooth">流畅</option>
            </select>
            <select value={streamFps} onChange={(event) => onStreamFps(Number(event.target.value))}>
              <option value={1}>1fps</option>
              <option value={2}>2fps</option>
              <option value={5}>5fps</option>
            </select>
            <button onClick={() => onStreamEnabled(!streamEnabled)}>{streamEnabled ? "暂停预览" : "实时预览"}</button>
            <button onClick={onStreamReload}>重连预览</button>
            <button className="primary" onClick={onRefreshScreen}>手动截图</button>
          </div>
          <div className="phone-shell">
            <div className="phone-screen">
              {streamEnabled && streamSrc ? (
                <img
                  src={streamSrc}
                  alt="remote phone live preview"
                  onError={onStreamError}
                />
              ) : snapshot?.image ? (
                <img src={snapshot.image} alt="remote phone screen" />
              ) : (
                <span>等待远端画面</span>
              )}
            </div>
          </div>
          {streamError && <div className="stream-error">{streamError}</div>}
          <div className="screen-stats">
            <span>{snapshot?.byteCount ? `${Math.round(snapshot.byteCount / 1024)} KB` : "N/A"}</span>
            <span>{streamEnabled ? "MJPEG" : snapshot?.updatedAt ? timeText(snapshot.updatedAt) : "未刷新"}</span>
            <span>{streamEnabled ? `${qualityMode} · ${streamEffectiveFps}fps` : snapshot?.level || activeQuality}</span>
          </div>
        </section>
      </section>
    </main>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="info-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function buildAgentConnectionPrompt(device, token) {
  const relayUrl = `${publicOrigin()}${RELAY_BASE}`;
  const consoleUrl = `${publicOrigin()}/cloudphone-console/#token=${token}`;
  const hello = device.hello || {};
  const deviceLabel = [
    hello.manufacturer,
    hello.model,
    hello.androidVersion ? `Android ${hello.androidVersion}` : "",
    hello.rootAvailable ? "Root available" : "Root unknown",
  ].filter(Boolean).join(" · ") || "Unknown device";

  return [
    "# 云手机远程控制 Agent 提示词",
    "",
    "你是一个云手机远程控制 Agent。请严格通过 PB Relay 的 Root API / ADB Bridge 操控设备，不要猜测协议，不要尝试任意 shell，不要绕过命令白名单。",
    "",
    "## 连接信息",
    `Relay URL: ${relayUrl}`,
    `Console URL: ${consoleUrl}`,
    `Device ID: ${device.deviceId}`,
    `Token: ${token}`,
    `Device: ${deviceLabel}`,
    `Last seen: ${device.lastSeenAt || "N/A"}`,
    `Remote IP: ${device.remoteAddress || "N/A"}`,
    "",
    "## HTTP 鉴权",
    "所有 Relay HTTP 请求必须带请求头：",
    `x-relay-token: ${token}`,
    "",
    "## API 协议",
    `1. GET ${relayUrl}/devices`,
    "   用来确认设备在线。目标设备必须 online=true。",
    `2. POST ${relayUrl}/commands`,
    `   Body: {"deviceId":"${device.deviceId}","name":"<command>","params":{}}`,
    "   返回 command.id。",
    `3. GET ${relayUrl}/commands/{id}`,
    "   每 400-800ms 轮询一次，直到 status 为 completed / failed / offline。",
    "   completed 表示执行完成；failed/offline 必须把 error 原样返回给用户。",
    "",
    "## 本地 helper 用法",
    "如果你在同一工作区执行，可以直接使用 tools/cloudphone-api-client.mjs：",
    `export CLOUDPHONE_RELAY_URL='${relayUrl}'`,
    `export CLOUDPHONE_RELAY_TOKEN='${token}'`,
    `export CLOUDPHONE_DEVICE_ID='${device.deviceId}'`,
    "node tools/cloudphone-api-client.mjs devices",
    "node tools/cloudphone-api-client.mjs cmd snapshot",
    "node tools/cloudphone-api-client.mjs cmd launch_xhs",
    "node tools/cloudphone-api-client.mjs cmd screencap '{\"format\":\"jpeg\",\"maxWidth\":540,\"quality\":65}'",
    "node tools/cloudphone-api-client.mjs cmd dump_ui",
    "node tools/cloudphone-api-client.mjs cmd tap '{\"x\":360,\"y\":720}'",
    "node tools/cloudphone-api-client.mjs cmd swipe '{\"x1\":360,\"y1\":1050,\"x2\":360,\"y2\":420,\"durationMs\":450}'",
    "node tools/cloudphone-api-client.mjs cmd input_text '{\"text\":\"hello\"}'",
    "node tools/cloudphone-api-client.mjs cmd wait_for_text '{\"text\":\"搜索\",\"timeoutMs\":5000}'",
    "",
    "## 可用 Root API 命令",
    "- snapshot: 获取前台 Activity、屏幕尺寸、ADB/Root 摘要等状态。",
    "- screencap: 获取截图。建议参数 {format:\"jpeg\",maxWidth:360|540|720,quality:45|65|80}，结果在 result.base64。",
    "- dump_ui: 获取 uiautomator XML，用于读取页面结构、按钮、文本和评论区域。",
    "- launch_xhs: 启动小红书。",
    "- launch_app: 只允许服务端白名单包名，默认允许 com.xingin.xhs 和诊断 App。",
    "- tap: 点击坐标，参数 {x,y}。",
    "- long_press: 长按坐标，参数 {x,y,durationMs}。",
    "- swipe: 滑动，参数 {x1,y1,x2,y2,durationMs}。",
    "- back / home: 系统返回和主页。",
    "- input_text: 输入短文本，文本长度有限制。",
    "- clear_text: 发送多次删除键清空输入框。",
    "- wait_for_text: 等待 UI 中出现指定文本，参数 {text,timeoutMs,intervalMs}。",
    "- adb_status / adb_enable / adb_disable: 检查或管理手机本机 adbd tcp，再配合 ADB Bridge 使用。",
    "",
    "## ADB Bridge 可选用法",
    "先用 Root API 执行 adb_enable，再执行 adb_status 确认 connectable=true。然后在本地启动桥接：",
    `CLOUDPHONE_RELAY_TOKEN='${token}' node tools/adb-bridge-client.mjs --device ${device.deviceId} --port 15555`,
    "adb connect localhost:15555",
    "adb devices",
    "adb shell wm size",
    "",
    "## 推荐控制流程",
    "1. 先调用 devices，确认目标 deviceId 在线且 rootAvailable=true。",
    "2. 调用 snapshot + screencap + dump_ui 建立当前页面状态。",
    "3. 需要控制小红书时先 launch_xhs，再等待页面稳定。",
    "4. 每次 tap/swipe/input/back/home 后，都用 wait_for_text、dump_ui 或 screencap 验证结果。",
    "5. 对截图使用 jpeg 低中档画质，只有需要看细节时才用 maxWidth=720。",
    "6. 所有动作必须记录：时间、动作、参数、是否成功、耗时、关键结果。",
    "",
    "## 安全边界",
    "- 不要执行任意 shell。",
    "- 不要调用白名单之外的命令。",
    "- 不要把 token 发到其他服务或写进公开日志。",
    "- 如果命令失败，不要假装成功，必须返回 Relay 的 error/status。",
    "- 小红书业务逻辑由 Agent 自己判断；Relay 只提供通用设备控制能力。",
  ].join("\n");
}

function App() {
  const [token] = useState(tokenFromLocation);
  const api = useRelayApi(token);
  const [view, setView] = useState("list");
  const [selectedId, setSelectedId] = useState("");
  const [devices, setDevices] = useState([]);
  const [config, setConfig] = useState({ defaultRefreshMs: DEFAULT_REFRESH_MS, screenshotPresets: FALLBACK_PRESETS });
  const [thumbnails, setThumbnails] = useState({});
  const [screens, setScreens] = useState({});
  const [logs, setLogs] = useState([]);
  const [qualityMode, setQualityMode] = useState("auto");
  const [autoLevel, setAutoLevel] = useState("balanced");
  const [streamEnabled, setStreamEnabled] = useState(true);
  const [streamFps, setStreamFps] = useState(DEFAULT_STREAM_FPS);
  const [streamNonce, setStreamNonce] = useState(0);
  const [streamError, setStreamError] = useState("");
  const [streamBoosted, setStreamBoosted] = useState(false);
  const [manual, setManual] = useState({ x: "", y: "", text: "" });
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [coverRefreshing, setCoverRefreshing] = useState(false);
  const speedRef = useRef({ slow: 0, fast: 0 });
  const streamBoostTimerRef = useRef(null);
  const streamViewerIdRef = useRef(crypto.randomUUID());
  const coverRefreshingRef = useRef(false);

  const presets = config.screenshotPresets || FALLBACK_PRESETS;
  const activeQuality = qualityMode === "auto" ? autoLevel : qualityMode;
  const selected = devices.find((device) => device.deviceId === selectedId) || devices[0];
  const selectedLogs = selected ? logs.filter((item) => item.deviceId === selected.deviceId) : [];
  const streamEffectiveFps = streamBoosted ? BOOST_STREAM_FPS : streamFps;
  const selectedStreamSrc = selected && streamEnabled
    ? mjpegStreamUrl(token, selected.deviceId, qualityMode, streamEffectiveFps, streamNonce, streamViewerIdRef.current)
    : "";

  function addLog(deviceId, action, status, detail, durationMs, extra = {}) {
    setLogs((items) => [
      { id: crypto.randomUUID(), at: new Date(), deviceId, action, status, detail, durationMs, ...extra },
      ...items,
    ].slice(0, 60));
  }

  function boostStreamTemporarily() {
    if (streamBoostTimerRef.current) window.clearTimeout(streamBoostTimerRef.current);
    setStreamBoosted(true);
    setStreamNonce((value) => value + 1);
    streamBoostTimerRef.current = window.setTimeout(() => {
      setStreamBoosted(false);
      setStreamNonce((value) => value + 1);
    }, BOOST_STREAM_MS);
  }

  async function loadDevices() {
    if (!token) return;
    const json = await api.request("/devices");
    const nextDevices = json.devices || [];
    setDevices(nextDevices);
    if (!selectedId && nextDevices[0]) setSelectedId(nextDevices[0].deviceId);
  }

  async function loadConfig() {
    if (!token) return;
    const json = await api.request("/console/config");
    setConfig(json);
  }

  function adaptQuality(durationMs) {
    if (qualityMode !== "auto") return;
    const speed = speedRef.current;
    if (durationMs > 2500) {
      speed.slow += 1;
      speed.fast = 0;
      if (speed.slow >= 2) {
        setAutoLevel((level) => (level === "crisp" ? "balanced" : "smooth"));
        speed.slow = 0;
      }
      return;
    }
    if (durationMs < 800) {
      speed.fast += 1;
      speed.slow = 0;
      if (speed.fast >= 5) {
        setAutoLevel((level) => (level === "smooth" ? "balanced" : "crisp"));
        speed.fast = 0;
      }
    }
  }

  async function runAction(device, name, params = {}, label = name, options = {}) {
    if (!device) return null;
    const startedAt = performance.now();
    if (!options.silent) setBusy(label);
    setError("");
    try {
      const command = await api.runCommand(device.deviceId, name, params);
      const durationMs = Math.round(performance.now() - startedAt);
      const status = command.status === "completed" ? "成功" : "失败";
      if (!options.silent) {
        addLog(device.deviceId, label, status, commandSummary(command), durationMs, {
          kind: name,
          rawFocus: command.result?.focus,
        });
        if (STREAM_BOOST_COMMANDS.has(name)) boostStreamTemporarily();
      }
      if (command.status !== "completed") throw new Error(command.error || command.status);
      return command;
    } catch (err) {
      const durationMs = Math.round(performance.now() - startedAt);
      if (!options.silent) addLog(device.deviceId, label, "失败", err.message, durationMs, { kind: name });
      setError(err.message);
      return null;
    } finally {
      if (!options.silent) setBusy("");
    }
  }

  async function refreshScreen(device, target = "detail", level = activeQuality, options = {}) {
    if (!device) return;
    const preset = presets[level] || presets.balanced || FALLBACK_PRESETS.balanced;
    const startedAt = performance.now();
    const command = await runAction(device, "screencap", preset, target === "thumb" ? "刷新缩略图" : "刷新画面", options);
    const durationMs = Math.round(performance.now() - startedAt);
    if (target === "detail") adaptQuality(durationMs);
    if (!command?.result?.base64) return;
    const payload = {
      image: `data:${command.result.mimeType || "image/png"};base64,${command.result.base64}`,
      byteCount: command.result.byteCount,
      level,
      updatedAt: new Date(),
    };
    if (target === "thumb") setThumbnails((items) => ({ ...items, [device.deviceId]: payload }));
    else setScreens((items) => ({ ...items, [device.deviceId]: payload }));
  }

  async function refreshCover(device, options = {}) {
    if (!device?.online) return;
    await refreshScreen(device, "thumb", "smooth", { silent: true, ...options });
  }

  async function refreshCovers(deviceList = devices) {
    if (coverRefreshingRef.current) return;
    const targets = deviceList.filter((device) => device.online);
    if (targets.length === 0) return;
    coverRefreshingRef.current = true;
    setCoverRefreshing(true);
    try {
      for (const device of targets) {
        await refreshCover(device);
      }
    } finally {
      coverRefreshingRef.current = false;
      setCoverRefreshing(false);
    }
  }

  async function copyConnectionInfo(device) {
    if (!device) return;
    const text = buildAgentConnectionPrompt(device, token);
    await navigator.clipboard.writeText(text);
    addLog(device.deviceId, "复制 Agent 提示词", "成功", "已复制完整连接方式、能力清单和操作流程", 0);
  }

  useEffect(() => {
    if (!token) return undefined;
    loadConfig().catch((err) => setError(err.message));
    loadDevices().catch((err) => setError(err.message));
    const id = setInterval(() => loadDevices().catch((err) => setError(err.message)), 5000);
    return () => clearInterval(id);
  }, [token]);

  useEffect(() => {
    if (view !== "list" || devices.length === 0) return undefined;
    const missingCover = devices.some((device) => device.online && !thumbnails[device.deviceId]?.image);
    if (missingCover) refreshCovers(devices).catch((err) => setError(err.message));
    const id = setInterval(() => {
      refreshCovers(devices).catch((err) => setError(err.message));
    }, COVER_REFRESH_MS);
    return () => clearInterval(id);
  }, [view, devices.map((device) => `${device.deviceId}:${device.online}`).join("|")]);

  useEffect(() => {
    setStreamError("");
    setStreamNonce((value) => value + 1);
  }, [selected?.deviceId, qualityMode, streamFps, streamEnabled]);

  useEffect(() => () => {
    if (streamBoostTimerRef.current) window.clearTimeout(streamBoostTimerRef.current);
  }, []);

  if (!token) return <AuthGate />;

  if (view === "detail" && selected) {
    return (
      <DetailPage
        device={selected}
        snapshot={screens[selected.deviceId]}
        streamSrc={selectedStreamSrc}
        streamEnabled={streamEnabled}
        streamFps={streamFps}
        streamEffectiveFps={streamEffectiveFps}
        streamError={streamError}
        logs={selectedLogs}
        busy={busy}
        error={error}
        qualityMode={qualityMode}
        activeQuality={activeQuality}
        manual={manual}
        onBack={() => setView("list")}
        onQuality={setQualityMode}
        onStreamEnabled={(enabled) => {
          setStreamEnabled(enabled);
        }}
        onStreamFps={(fps) => {
          setStreamFps(fps);
        }}
        onStreamError={() => {
          setStreamError("实时预览不可用，可使用手动截图。");
          setStreamEnabled(false);
        }}
        onStreamReload={() => {
          setStreamError("");
          setStreamEnabled(true);
          setStreamNonce((value) => value + 1);
        }}
        onManual={setManual}
        onCommand={(name, params, label) => runAction(selected, name, params, label)}
        onRefreshScreen={() => refreshScreen(selected, "detail", activeQuality)}
        onCopyConnection={() => copyConnectionInfo(selected)}
        onClearLogs={() => setLogs((items) => items.filter((item) => item.deviceId !== selected.deviceId))}
      />
    );
  }

  return (
    <ListPage
      devices={devices}
      thumbnails={thumbnails}
      coverRefreshing={coverRefreshing}
      error={error}
      onRefresh={loadDevices}
      onRefreshThumbs={() => refreshCovers(devices)}
      onRefreshThumb={(device) => refreshCover(device)}
      onOpen={(deviceId) => {
        setSelectedId(deviceId);
        setView("detail");
      }}
    />
  );
}

createRoot(document.getElementById("root")).render(<App />);
