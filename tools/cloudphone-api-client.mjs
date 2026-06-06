#!/usr/bin/env node
import fs from "node:fs";

const DEFAULT_BASE_URL = "https://relay.example.com/cloudphone-relay";
const DEFAULT_DEVICE_ID = "demo-device-id";
const DEFAULT_TIMEOUT_MS = 30000;

function usage() {
  console.error(`Usage:
  cloudphone-api-client devices
  cloudphone-api-client cmd <name> [jsonParams]
  cloudphone-api-client launch-xhs
  cloudphone-api-client screencap --out file.png
  cloudphone-api-client dump-ui --out file.xml

Environment:
  CLOUDPHONE_RELAY_URL    default ${DEFAULT_BASE_URL}
  CLOUDPHONE_RELAY_TOKEN  required
  CLOUDPHONE_DEVICE_ID    default ${DEFAULT_DEVICE_ID}`);
}

function config() {
  const token = process.env.CLOUDPHONE_RELAY_TOKEN;
  if (!token) throw new Error("CLOUDPHONE_RELAY_TOKEN is required");
  return {
    baseUrl: (process.env.CLOUDPHONE_RELAY_URL || DEFAULT_BASE_URL).replace(/\/$/, ""),
    token,
    deviceId: process.env.CLOUDPHONE_DEVICE_ID || DEFAULT_DEVICE_ID,
  };
}

async function requestJson(path, options = {}) {
  const { baseUrl, token } = config();
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      "x-relay-token": token,
      "content-type": "application/json",
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  let json;
  try {
    json = JSON.parse(text);
  } catch {
    throw new Error(`Invalid JSON response (${response.status}): ${text.slice(0, 300)}`);
  }
  if (!response.ok || json.ok === false) {
    throw new Error(json.error || `HTTP ${response.status}`);
  }
  return json;
}

async function createCommand(name, params = {}) {
  const { deviceId } = config();
  const json = await requestJson("/commands", {
    method: "POST",
    body: JSON.stringify({ deviceId, name, params }),
  });
  return json.command;
}

async function waitCommand(id, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    const json = await requestJson(`/commands/${encodeURIComponent(id)}`);
    const command = json.command;
    if (["completed", "failed", "offline"].includes(command.status)) return command;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`command_timeout: ${id}`);
}

function parseOut(args) {
  const index = args.indexOf("--out");
  if (index < 0 || !args[index + 1]) throw new Error("--out file is required");
  return args[index + 1];
}

async function run() {
  const [subcommand, ...args] = process.argv.slice(2);
  if (!subcommand) {
    usage();
    process.exit(2);
  }

  if (subcommand === "devices") {
    console.log(JSON.stringify(await requestJson("/devices"), null, 2));
    return;
  }

  if (subcommand === "cmd") {
    const [name, paramsJson = "{}"] = args;
    if (!name) throw new Error("cmd name is required");
    const params = JSON.parse(paramsJson);
    const created = await createCommand(name, params);
    const command = await waitCommand(created.id);
    console.log(JSON.stringify(command, null, 2));
    process.exit(command.status === "completed" ? 0 : 1);
  }

  if (subcommand === "launch-xhs") {
    const created = await createCommand("launch_xhs");
    console.log(JSON.stringify(await waitCommand(created.id), null, 2));
    return;
  }

  if (subcommand === "screencap") {
    const out = parseOut(args);
    const created = await createCommand("screencap");
    const command = await waitCommand(created.id);
    if (command.status !== "completed") throw new Error(command.error || command.status);
    fs.writeFileSync(out, Buffer.from(command.result.base64, "base64"));
    console.log(JSON.stringify({ ok: true, out, byteCount: command.result.byteCount }, null, 2));
    return;
  }

  if (subcommand === "dump-ui") {
    const out = parseOut(args);
    const created = await createCommand("dump_ui");
    const command = await waitCommand(created.id);
    if (command.status !== "completed") throw new Error(command.error || command.status);
    fs.writeFileSync(out, command.result.xml);
    console.log(JSON.stringify({ ok: true, out, charCount: command.result.charCount }, null, 2));
    return;
  }

  usage();
  process.exit(2);
}

run().catch((error) => {
  console.error(error.message || error);
  process.exit(1);
});
