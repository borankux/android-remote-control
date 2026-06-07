import http from "node:http";
import crypto from "node:crypto";
import { WebSocketServer } from "ws";

const PORT = Number(process.env.PORT || 18088);
const RELAY_TOKEN = process.env.RELAY_TOKEN || "";
const UPDATE_URL_PREFIX = process.env.UPDATE_URL_PREFIX || "";
const ONLINE_TTL_MS = 45_000;
const MAX_BODY_BYTES = 128 * 1024;
const MAX_RESULT_CHARS = 8 * 1024 * 1024;
const ADB_TUNNEL_TTL_MS = 10 * 60_000;
const ALLOWED_LAUNCH_PACKAGES = new Set(["com.xingin.xhs", "com.allin.cloudphone.inspector"]);
const SCREENSHOT_PRESETS = {
  crisp: { format: "jpeg", maxWidth: 720, quality: 80 },
  balanced: { format: "jpeg", maxWidth: 540, quality: 65 },
  smooth: { format: "jpeg", maxWidth: 360, quality: 45 }
};
const MJPEG_BOUNDARY = "cloudphone-mjpeg";
const MJPEG_FRAME_TIMEOUT_MS = 5_000;
const MJPEG_MAX_VIEWERS_PER_DEVICE = 1;
const MJPEG_FPS_VALUES = new Set([1, 2, 5]);
const MJPEG_MODE_VALUES = new Set(["auto", "smooth", "balanced", "crisp"]);
const MJPEG_LEVELS = ["smooth", "balanced", "crisp"];
const ALLOWED_COMMANDS = new Set([
  "ping", "snapshot", "screencap", "tap", "swipe", "long_press", "back", "home",
  "input_text", "clear_text", "launch_app", "launch_xhs", "dump_ui", "wait_for_text",
  "adb_enable", "adb_status", "adb_disable", "self_update"
]);
const devices = new Map();
const commands = new Map();
const adbTunnels = new Map();
const frameRequests = new Map();
const mjpegViewers = new Map();

function sendJson(res, status, body) {
  const payload = JSON.stringify(body, null, 2);
  res.writeHead(status, { "content-type": "application/json; charset=utf-8", "cache-control": "no-store" });
  res.end(payload);
}

function tokenFrom(req, url) {
  return req.headers["x-relay-token"] || url.searchParams.get("token") || "";
}

function authorized(req, url) {
  if (!RELAY_TOKEN) return false;
  const given = Buffer.from(String(tokenFrom(req, url)));
  const expected = Buffer.from(RELAY_TOKEN);
  return given.length === expected.length && crypto.timingSafeEqual(given, expected);
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let body = "";
    req.setEncoding("utf8");
    req.on("data", (chunk) => {
      body += chunk;
      if (body.length > MAX_BODY_BYTES) reject(new Error("body_too_large"));
    });
    req.on("end", () => {
      if (!body.trim()) return resolve({});
      try { resolve(JSON.parse(body)); } catch { reject(new Error("invalid_json")); }
    });
    req.on("error", reject);
  });
}

function intParam(params, name, fallback, min, max) {
  const raw = params[name] ?? fallback;
  const value = Number(raw);
  if (!Number.isFinite(value)) throw new Error(`invalid_${name}`);
  if (value < min || value > max) throw new Error(`${name}_out_of_range`);
  return Math.round(value);
}

function isAllowedUpdateUrl(value) {
  if (!UPDATE_URL_PREFIX) return false;
  try {
    const url = new URL(value);
    const prefix = new URL(UPDATE_URL_PREFIX);
    return url.protocol === "https:" &&
      url.origin === prefix.origin &&
      url.pathname.startsWith(prefix.pathname) &&
      url.pathname.endsWith(".apk");
  } catch {
    return false;
  }
}

function sanitizeParams(name, params) {
  if (name === "screencap") {
    const format = String(params.format || "png").toLowerCase();
    if (!["png", "jpg", "jpeg", "webp"].includes(format)) throw new Error("invalid_screenshot_format");
    return {
      format,
      maxWidth: intParam(params, "maxWidth", 0, 0, 1440),
      quality: intParam(params, "quality", 90, 10, 100)
    };
  }
  if (name === "tap") {
    return { x: intParam(params, "x", NaN, 0, 4096), y: intParam(params, "y", NaN, 0, 4096) };
  }
  if (name === "swipe") {
    return {
      x1: intParam(params, "x1", NaN, 0, 4096), y1: intParam(params, "y1", NaN, 0, 4096),
      x2: intParam(params, "x2", NaN, 0, 4096), y2: intParam(params, "y2", NaN, 0, 4096),
      durationMs: intParam(params, "durationMs", 300, 50, 5000)
    };
  }
  if (name === "long_press") {
    return { x: intParam(params, "x", NaN, 0, 4096), y: intParam(params, "y", NaN, 0, 4096), durationMs: intParam(params, "durationMs", 800, 300, 5000) };
  }
  if (name === "input_text") {
    const text = String(params.text ?? "");
    if (text.length > 200) throw new Error("text_too_long");
    return { text };
  }
  if (name === "clear_text") {
    return { count: intParam(params, "count", 80, 1, 500) };
  }
  if (name === "launch_app") {
    const packageName = String(params.packageName || "");
    if (!ALLOWED_LAUNCH_PACKAGES.has(packageName)) throw new Error("package_not_allowed");
    return { packageName };
  }
  if (name === "self_update") {
    const url = String(params.url || "");
    const sha256 = String(params.sha256 || "").toLowerCase();
    if (!isAllowedUpdateUrl(url)) throw new Error("update_url_not_allowed");
    if (!/^[a-f0-9]{64}$/.test(sha256)) throw new Error("invalid_sha256");
    return { url, sha256 };
  }
  if (name === "wait_for_text") {
    const text = String(params.text ?? "");
    if (!text || text.length > 80) throw new Error("invalid_text");
    return {
      text,
      timeoutMs: intParam(params, "timeoutMs", 5000, 500, 30000),
      intervalMs: intParam(params, "intervalMs", 500, 200, 5000)
    };
  }
  return {};
}

function publicDevice(device) {
  return {
    deviceId: device.deviceId,
    online: Date.now() - device.lastSeenAt <= ONLINE_TTL_MS,
    connectedAt: new Date(device.connectedAt).toISOString(),
    lastSeenAt: new Date(device.lastSeenAt).toISOString(),
    remoteAddress: device.remoteAddress,
    hello: device.hello || null,
    lastMessage: publicLastMessage(device.lastMessage)
  };
}

function publicLastMessage(raw) {
  if (!raw) return null;
  const text = String(raw);
  try {
    const parsed = JSON.parse(text);
    if (parsed?.type !== "command_result") return text.length > 1000 ? `${text.slice(0, 1000)}…` : text;
    const result = parsed.result && typeof parsed.result === "object" ? { ...parsed.result } : parsed.result;
    if (result && typeof result === "object" && result.base64) {
      result.base64 = `[omitted ${String(parsed.result.base64).length} chars]`;
    }
    return JSON.stringify({ ...parsed, result });
  } catch {
    return text.length > 1000 ? `${text.slice(0, 1000)}…` : text;
  }
}

function publicCommand(command) {
  return {
    id: command.id,
    deviceId: command.deviceId,
    name: command.name,
    status: command.status,
    createdAt: new Date(command.createdAt).toISOString(),
    sentAt: command.sentAt ? new Date(command.sentAt).toISOString() : null,
    completedAt: command.completedAt ? new Date(command.completedAt).toISOString() : null,
    error: command.error || null,
    result: command.result || null
  };
}

function publicTunnel(tunnel) {
  return {
    id: tunnel.id,
    deviceId: tunnel.deviceId,
    createdAt: new Date(tunnel.createdAt).toISOString(),
    clientOpen: tunnel.clientWs?.readyState === tunnel.clientWs?.OPEN,
    deviceOpen: tunnel.deviceWs?.readyState === tunnel.deviceWs?.OPEN,
    clientToDeviceBytes: tunnel.clientToDeviceBytes,
    deviceToClientBytes: tunnel.deviceToClientBytes
  };
}

function closeTunnel(tunnel, code = 1000, reason = "closed") {
  try { tunnel.clientWs?.close(code, reason); } catch {}
  try { tunnel.deviceWs?.close(code, reason); } catch {}
  adbTunnels.delete(tunnel.id);
}

function prune() {
  const now = Date.now();
  for (const [deviceId, device] of devices.entries()) {
    if (!device.socket || device.socket.readyState !== device.socket.OPEN) {
      if (now - device.lastSeenAt > ONLINE_TTL_MS * 4) devices.delete(deviceId);
    }
  }
  for (const [id, command] of commands.entries()) {
    if (now - command.createdAt > 10 * 60_000) commands.delete(id);
  }
  for (const tunnel of adbTunnels.values()) {
    if (now - tunnel.createdAt > ADB_TUNNEL_TTL_MS) closeTunnel(tunnel, 1000, "tunnel ttl");
  }
}

function sendCommand(command) {
  const device = devices.get(command.deviceId);
  if (!device?.socket || device.socket.readyState !== device.socket.OPEN) {
    command.status = "offline";
    command.error = "device_not_online";
    return false;
  }
  command.status = "sent";
  command.sentAt = Date.now();
  device.socket.send(JSON.stringify({ type: "command", commandId: command.id, command: { name: command.name, params: command.params || {} } }));
  return true;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function parseMjpegOptions(url) {
  const mode = String(url.searchParams.get("mode") || "auto").toLowerCase();
  const fps = Number(url.searchParams.get("fps") || 2);
  if (!MJPEG_MODE_VALUES.has(mode)) throw new Error("invalid_stream_mode");
  if (!MJPEG_FPS_VALUES.has(fps)) throw new Error("invalid_stream_fps");
  return { mode, fps };
}

function nextQualityLevel(level, direction) {
  const index = MJPEG_LEVELS.indexOf(level);
  if (index < 0) return "balanced";
  if (direction === "down") return MJPEG_LEVELS[Math.max(0, index - 1)];
  return MJPEG_LEVELS[Math.min(MJPEG_LEVELS.length - 1, index + 1)];
}

function mjpegViewerId(url) {
  const value = String(url.searchParams.get("viewer") || "");
  return /^[a-zA-Z0-9._-]{1,80}$/.test(value) ? value : crypto.randomUUID();
}

function registerMjpegViewer(deviceId, viewerId, res) {
  const viewers = mjpegViewers.get(deviceId) || new Map();
  const existing = viewers.get(viewerId);
  if (existing?.res && !existing.res.destroyed) {
    try { existing.res.destroy(); } catch {}
  }
  const otherViewerCount = [...viewers.keys()].filter((id) => id !== viewerId).length;
  if (otherViewerCount >= MJPEG_MAX_VIEWERS_PER_DEVICE) return null;
  const streamId = crypto.randomUUID();
  viewers.set(viewerId, { streamId, res });
  mjpegViewers.set(deviceId, viewers);
  return { viewerId, streamId };
}

function unregisterMjpegViewer(deviceId, viewerId, streamId) {
  const viewers = mjpegViewers.get(deviceId);
  if (!viewers) return;
  const current = viewers.get(viewerId);
  if (current?.streamId !== streamId) return;
  viewers.delete(viewerId);
  if (viewers.size === 0) mjpegViewers.delete(deviceId);
}

function rejectFrameRequestsForDevice(deviceId, error) {
  for (const [id, request] of frameRequests.entries()) {
    if (request.deviceId !== deviceId) continue;
    clearTimeout(request.timeout);
    frameRequests.delete(id);
    request.reject(error);
  }
}

function requestMjpegFrame(deviceId, preset) {
  const device = devices.get(deviceId);
  if (!device?.socket || device.socket.readyState !== device.socket.OPEN) {
    return Promise.reject(new Error("device_not_online"));
  }
  return new Promise((resolve, reject) => {
    const id = `frame-${crypto.randomUUID()}`;
    const timeout = setTimeout(() => {
      frameRequests.delete(id);
      reject(new Error("frame_timeout"));
    }, MJPEG_FRAME_TIMEOUT_MS);
    frameRequests.set(id, { deviceId, resolve, reject, timeout });
    device.socket.send(JSON.stringify({
      type: "command",
      commandId: id,
      command: { name: "screencap", params: preset }
    }));
  });
}

function waitForDrain(res, timeoutMs = 1500) {
  if (res.destroyed || res.writableEnded) return Promise.resolve(false);
  return new Promise((resolve) => {
    const timer = setTimeout(done, timeoutMs, false);
    function done(ok) {
      clearTimeout(timer);
      res.off("drain", onDrain);
      resolve(ok);
    }
    function onDrain() {
      done(true);
    }
    res.once("drain", onDrain);
  });
}

async function writeMjpegFrame(res, frame, level, durationMs) {
  if (res.destroyed || res.writableEnded) return false;
  const bytes = Buffer.from(String(frame.base64 || ""), "base64");
  if (bytes.length === 0) throw new Error("empty_frame");
  const mimeType = frame.mimeType || "image/jpeg";
  const header = [
    `--${MJPEG_BOUNDARY}`,
    `Content-Type: ${mimeType}`,
    `Content-Length: ${bytes.length}`,
    `X-Cloudphone-Level: ${level}`,
    `X-Cloudphone-Duration-Ms: ${durationMs}`,
    "",
    ""
  ].join("\r\n");
  const writable = res.write(header) && res.write(bytes) && res.write("\r\n");
  if (writable) return true;
  return waitForDrain(res);
}

function adaptMjpegLevel(state, durationMs, backpressure) {
  if (state.mode !== "auto") return;
  if (backpressure || durationMs > 2500) {
    state.slow += 1;
    state.fast = 0;
    if (state.slow >= 2) {
      state.level = nextQualityLevel(state.level, "down");
      state.slow = 0;
    }
    return;
  }
  if (durationMs < 800) {
    state.fast += 1;
    state.slow = 0;
    if (state.fast >= 5) {
      state.level = nextQualityLevel(state.level, "up");
      state.fast = 0;
    }
    return;
  }
  state.slow = 0;
  state.fast = 0;
}

async function handleMjpegStream(req, res, url, deviceId) {
  let options;
  try {
    options = parseMjpegOptions(url);
  } catch (error) {
    sendJson(res, 400, { ok: false, error: error.message || "invalid_stream_options" });
    return;
  }

  const device = devices.get(deviceId);
  if (!device?.socket || device.socket.readyState !== device.socket.OPEN) {
    sendJson(res, 404, { ok: false, error: "device_not_online" });
    return;
  }

  const viewerId = mjpegViewerId(url);
  const viewer = registerMjpegViewer(deviceId, viewerId, res);
  if (!viewer) {
    sendJson(res, 409, { ok: false, error: "stream_busy" });
    return;
  }

  let closed = false;
  const state = {
    mode: options.mode,
    fps: options.fps,
    level: options.mode === "auto" ? "balanced" : options.mode,
    slow: 0,
    fast: 0
  };
  const frameIntervalMs = Math.round(1000 / state.fps);

  res.on("close", () => { closed = true; });
  res.writeHead(200, {
    "content-type": `multipart/x-mixed-replace; boundary=${MJPEG_BOUNDARY}`,
    "cache-control": "no-store",
    "connection": "keep-alive",
    "x-accel-buffering": "no"
  });
  if (typeof res.flushHeaders === "function") res.flushHeaders();

  try {
    while (!closed && !res.destroyed && !res.writableEnded) {
      const startedAt = Date.now();
      const preset = SCREENSHOT_PRESETS[state.level] || SCREENSHOT_PRESETS.balanced;
      let backpressure = false;
      try {
        const result = await requestMjpegFrame(deviceId, preset);
        if (!result?.ok || !result?.base64) throw new Error(result?.error || "frame_failed");
        const durationMs = Date.now() - startedAt;
        backpressure = !(await writeMjpegFrame(res, result, state.level, durationMs));
        adaptMjpegLevel(state, durationMs, backpressure);
      } catch (error) {
        adaptMjpegLevel(state, MJPEG_FRAME_TIMEOUT_MS + 1, true);
      }
      const elapsedMs = Date.now() - startedAt;
      const delayMs = Math.max(0, frameIntervalMs - elapsedMs);
      if (delayMs > 0) await sleep(delayMs);
    }
  } finally {
    unregisterMjpegViewer(deviceId, viewer.viewerId, viewer.streamId);
    try { res.end(); } catch {}
  }
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
  if (url.pathname === "/health") {
    sendJson(res, 200, { ok: true, service: "cloudphone-relay", time: new Date().toISOString() });
    return;
  }
  if (!authorized(req, url)) {
    sendJson(res, 401, { ok: false, error: "unauthorized" });
    return;
  }
  if (req.method === "GET" && url.pathname === "/console/config") {
    sendJson(res, 200, {
      ok: true,
      defaultRefreshMs: 5000,
      screenshotPresets: SCREENSHOT_PRESETS,
      allowedCommands: [...ALLOWED_COMMANDS],
      relayBasePath: "/cloudphone-relay"
    });
    return;
  }
  if (req.method === "GET" && url.pathname === "/devices") {
    prune();
    sendJson(res, 200, { ok: true, devices: [...devices.values()].map(publicDevice) });
    return;
  }
  const streamMatch = url.pathname.match(/^\/stream\/mjpeg\/([^/]+)$/);
  if (req.method === "GET" && streamMatch) {
    prune();
    await handleMjpegStream(req, res, url, decodeURIComponent(streamMatch[1]));
    return;
  }
  if (req.method === "GET" && url.pathname === "/adb/tunnels") {
    prune();
    sendJson(res, 200, { ok: true, tunnels: [...adbTunnels.values()].map(publicTunnel) });
    return;
  }
  if (req.method === "POST" && url.pathname === "/commands") {
    try {
      const body = await readJsonBody(req);
      const deviceId = String(body.deviceId || "").trim();
      const name = String(body.name || "").trim();
      if (!deviceId || !ALLOWED_COMMANDS.has(name)) {
        sendJson(res, 400, { ok: false, error: "invalid_command", allowed: [...ALLOWED_COMMANDS] });
        return;
      }
      const command = { id: crypto.randomUUID(), deviceId, name, params: sanitizeParams(name, body.params || {}), status: "queued", createdAt: Date.now(), sentAt: null, completedAt: null, error: null, result: null };
      commands.set(command.id, command);
      sendCommand(command);
      sendJson(res, 200, { ok: true, command: publicCommand(command) });
    } catch (error) {
      sendJson(res, 400, { ok: false, error: error.message || "bad_request" });
    }
    return;
  }
  const commandMatch = url.pathname.match(/^\/commands\/([^/]+)$/);
  if (req.method === "GET" && commandMatch) {
    const command = commands.get(commandMatch[1]);
    if (!command) return sendJson(res, 404, { ok: false, error: "command_not_found" });
    sendJson(res, 200, { ok: true, command: publicCommand(command) });
    return;
  }
  sendJson(res, 404, { ok: false, error: "not_found" });
});

const wss = new WebSocketServer({ noServer: true, maxPayload: MAX_RESULT_CHARS });

function rejectUpgrade(socket, status, message) {
  socket.write(`HTTP/1.1 ${status} ${message}\r\n\r\n`);
  socket.destroy();
}

server.on("upgrade", (req, socket, head) => {
  const url = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
  if (!authorized(req, url)) return rejectUpgrade(socket, 401, "Unauthorized");

  let match = url.pathname.match(/^\/ws\/device\/([^/]+)$/);
  if (match) {
    const deviceId = decodeURIComponent(match[1]);
    wss.handleUpgrade(req, socket, head, (ws) => wss.emit("controlDevice", ws, req, deviceId));
    return;
  }

  match = url.pathname.match(/^\/adb\/client\/([^/]+)$/);
  if (match) {
    const deviceId = decodeURIComponent(match[1]);
    const device = devices.get(deviceId);
    if (!device?.socket || device.socket.readyState !== device.socket.OPEN) return rejectUpgrade(socket, 404, "Device Offline");
    for (const tunnel of adbTunnels.values()) {
      if (tunnel.deviceId === deviceId && tunnel.clientWs?.readyState === tunnel.clientWs?.OPEN) return rejectUpgrade(socket, 409, "Tunnel Busy");
    }
    wss.handleUpgrade(req, socket, head, (ws) => wss.emit("adbClient", ws, req, deviceId));
    return;
  }

  match = url.pathname.match(/^\/adb\/device\/([^/]+)\/([^/]+)$/);
  if (match) {
    const deviceId = decodeURIComponent(match[1]);
    const tunnelId = decodeURIComponent(match[2]);
    const tunnel = adbTunnels.get(tunnelId);
    if (!tunnel || tunnel.deviceId !== deviceId) return rejectUpgrade(socket, 404, "Tunnel Not Found");
    wss.handleUpgrade(req, socket, head, (ws) => wss.emit("adbDevice", ws, req, deviceId, tunnelId));
    return;
  }

  rejectUpgrade(socket, 404, "Not Found");
});

wss.on("controlDevice", (ws, req, deviceId) => {
  const now = Date.now();
  devices.set(deviceId, { deviceId, socket: ws, connectedAt: now, lastSeenAt: now, remoteAddress: req.headers["x-forwarded-for"] || req.socket.remoteAddress, hello: null, lastMessage: null });
  ws.send(JSON.stringify({ type: "relay_ack", deviceId, time: new Date().toISOString() }));

  ws.on("message", (data) => {
    const text = data.toString("utf8");
    const device = devices.get(deviceId);
    if (!device) return;
    device.lastSeenAt = Date.now();
    device.lastMessage = text.slice(0, 4096);
    try {
      const parsed = JSON.parse(text);
      if (parsed.type === "hello") device.hello = parsed;
      if (parsed.type === "command_result") {
        const frameRequest = frameRequests.get(String(parsed.commandId || ""));
        if (frameRequest && frameRequest.deviceId === deviceId) {
          clearTimeout(frameRequest.timeout);
          frameRequests.delete(String(parsed.commandId || ""));
          if (parsed.ok) frameRequest.resolve(parsed.result || null);
          else frameRequest.reject(new Error(parsed.error || "frame_failed"));
          return;
        }
        const command = commands.get(String(parsed.commandId || ""));
        if (command && command.deviceId === deviceId) {
          command.status = parsed.ok ? "completed" : "failed";
          command.completedAt = Date.now();
          command.error = parsed.error || null;
          const resultText = JSON.stringify(parsed.result || null);
          command.result = resultText.length > MAX_RESULT_CHARS ? { truncated: true, text: resultText.slice(0, MAX_RESULT_CHARS) } : parsed.result || null;
        }
      }
    } catch {}
  });

  ws.on("close", () => {
    const device = devices.get(deviceId);
    if (device) { device.lastSeenAt = Date.now(); device.socket = null; }
    rejectFrameRequestsForDevice(deviceId, new Error("device_control_closed"));
    for (const tunnel of adbTunnels.values()) {
      if (tunnel.deviceId === deviceId) closeTunnel(tunnel, 1000, "device control closed");
    }
  });
});

wss.on("adbClient", (ws, req, deviceId) => {
  const device = devices.get(deviceId);
  const tunnel = { id: crypto.randomUUID(), deviceId, clientWs: ws, deviceWs: null, createdAt: Date.now(), clientToDeviceBytes: 0, deviceToClientBytes: 0 };
  adbTunnels.set(tunnel.id, tunnel);
  device.socket.send(JSON.stringify({ type: "adb_tunnel_open", tunnelId: tunnel.id }));
  ws.send(JSON.stringify({ type: "adb_tunnel_ack", tunnelId: tunnel.id, deviceId }));

  ws.on("message", (data, isBinary) => {
    if (!isBinary) return;
    if (tunnel.deviceWs?.readyState === tunnel.deviceWs?.OPEN) {
      tunnel.clientToDeviceBytes += data.length;
      tunnel.deviceWs.send(data, { binary: true });
    }
  });
  ws.on("close", () => closeTunnel(tunnel, 1000, "client closed"));
  ws.on("error", () => closeTunnel(tunnel, 1011, "client error"));
});

wss.on("adbDevice", (ws, req, deviceId, tunnelId) => {
  const tunnel = adbTunnels.get(tunnelId);
  if (!tunnel) return ws.close(1008, "unknown tunnel");
  tunnel.deviceWs = ws;
  if (tunnel.clientWs?.readyState === tunnel.clientWs?.OPEN) tunnel.clientWs.send(JSON.stringify({ type: "adb_device_ready", tunnelId }));

  ws.on("message", (data, isBinary) => {
    if (!isBinary) return;
    if (tunnel.clientWs?.readyState === tunnel.clientWs?.OPEN) {
      tunnel.deviceToClientBytes += data.length;
      tunnel.clientWs.send(data, { binary: true });
    }
  });
  ws.on("close", () => closeTunnel(tunnel, 1000, "device tunnel closed"));
  ws.on("error", () => closeTunnel(tunnel, 1011, "device tunnel error"));
});

setInterval(prune, 30_000).unref();
server.listen(PORT, "127.0.0.1", () => console.log(`cloudphone-relay listening on 127.0.0.1:${PORT}`));
