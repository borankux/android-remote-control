#!/usr/bin/env node
import net from "node:net";

const DEFAULT_BASE_URL = "wss://relay.example.com/cloudphone-relay";
const DEFAULT_DEVICE_ID = "demo-device-id";

function parseArgs() {
  const args = process.argv.slice(2);
  const result = {
    baseUrl: process.env.CLOUDPHONE_RELAY_WS_URL || DEFAULT_BASE_URL,
    token: process.env.CLOUDPHONE_RELAY_TOKEN,
    deviceId: process.env.CLOUDPHONE_DEVICE_ID || DEFAULT_DEVICE_ID,
    port: 15555,
  };
  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === "--base-url") result.baseUrl = args[++i];
    else if (arg === "--token") result.token = args[++i];
    else if (arg === "--device") result.deviceId = args[++i];
    else if (arg === "--port") result.port = Number(args[++i]);
    else if (arg === "--help") result.help = true;
    else throw new Error(`unknown argument: ${arg}`);
  }
  return result;
}

function usage() {
  console.error(`Usage:
  adb-bridge-client --device demo-device-id --port 15555

Then run:
  adb connect localhost:15555

Environment:
  CLOUDPHONE_RELAY_WS_URL default ${DEFAULT_BASE_URL}
  CLOUDPHONE_RELAY_TOKEN  required
  CLOUDPHONE_DEVICE_ID    default ${DEFAULT_DEVICE_ID}`);
}

function websocketUrl(config) {
  const base = config.baseUrl.replace(/\/$/, "");
  return `${base}/adb/client/${encodeURIComponent(config.deviceId)}?token=${encodeURIComponent(config.token)}`;
}

function bridgeConnection(localSocket, config) {
  const ws = new WebSocket(websocketUrl(config));
  let wsOpen = false;
  let closed = false;
  let clientToDeviceBytes = 0;
  let deviceToClientBytes = 0;

  function closeBoth(reason) {
    if (closed) return;
    closed = true;
    try { localSocket.destroy(); } catch {}
    try { ws.close(1000, reason); } catch {}
    console.error(`[adb-bridge] closed: ${reason}; up=${clientToDeviceBytes} down=${deviceToClientBytes}`);
  }

  ws.binaryType = "arraybuffer";
  ws.addEventListener("open", () => {
    wsOpen = true;
    console.error("[adb-bridge] relay connected");
    localSocket.resume();
  });
  ws.addEventListener("message", async (event) => {
    if (typeof event.data === "string") {
      console.error(`[adb-bridge] ${event.data}`);
      return;
    }
    const buffer = Buffer.from(await event.data.arrayBuffer());
    deviceToClientBytes += buffer.length;
    localSocket.write(buffer);
  });
  ws.addEventListener("close", () => closeBoth("relay closed"));
  ws.addEventListener("error", () => closeBoth("relay error"));

  localSocket.pause();
  localSocket.on("data", (chunk) => {
    if (!wsOpen || closed) return;
    clientToDeviceBytes += chunk.length;
    ws.send(chunk);
  });
  localSocket.on("close", () => closeBoth("local closed"));
  localSocket.on("error", () => closeBoth("local error"));
}

function main() {
  const config = parseArgs();
  if (config.help) {
    usage();
    return;
  }
  if (!config.token) throw new Error("CLOUDPHONE_RELAY_TOKEN or --token is required");
  if (!Number.isInteger(config.port) || config.port < 1024 || config.port > 65535) {
    throw new Error("port must be an integer between 1024 and 65535");
  }
  const server = net.createServer((socket) => bridgeConnection(socket, config));
  server.listen(config.port, "localhost", () => {
    console.error(`[adb-bridge] listening on localhost:${config.port}`);
    console.error(`[adb-bridge] device ${config.deviceId}`);
  });
}

try {
  main();
} catch (error) {
  console.error(error.message || error);
  usage();
  process.exit(1);
}
