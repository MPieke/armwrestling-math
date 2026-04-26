import { readFile } from "node:fs/promises";
import { JSDOM } from "jsdom";
import { createServer } from "vite";

const appRoot = new URL("../", import.meta.url);
const dossierUrl = new URL("../public/match_dossier.json", import.meta.url);
const dossier = JSON.parse(await readFile(dossierUrl, "utf8"));
const dom = new JSDOM("<!doctype html><html><body><div id=\"root\"></div></body></html>", {
  url: "http://127.0.0.1:5173/",
  pretendToBeVisual: true,
});

globalThis.window = dom.window;
globalThis.document = dom.window.document;
Object.defineProperty(globalThis, "navigator", {
  configurable: true,
  value: dom.window.navigator,
});
Object.defineProperty(window, "innerWidth", {
  configurable: true,
  value: process.env.SMOKE_VIEWPORT === "mobile" ? 390 : 1280,
});
Object.defineProperty(window, "innerHeight", {
  configurable: true,
  value: process.env.SMOKE_VIEWPORT === "mobile" ? 844 : 900,
});
globalThis.HTMLElement = dom.window.HTMLElement;
globalThis.Node = dom.window.Node;
globalThis.requestAnimationFrame = dom.window.requestAnimationFrame.bind(dom.window);
globalThis.cancelAnimationFrame = dom.window.cancelAnimationFrame.bind(dom.window);
globalThis.fetch = async (url) => {
  if (String(url).endsWith("/match_dossier.json")) {
    return new Response(JSON.stringify(dossier), {
      headers: { "content-type": "application/json" },
      status: 200,
    });
  }
  throw new Error(`Unexpected fetch during smoke test: ${url}`);
};

const runtimeErrors = [];
const originalConsoleError = console.error;
console.error = (...args) => {
  runtimeErrors.push(args.map(String).join(" "));
  originalConsoleError(...args);
};

window.addEventListener("error", (event) => {
  runtimeErrors.push(event.error?.stack ?? event.message);
});

window.addEventListener("unhandledrejection", (event) => {
  runtimeErrors.push(event.reason?.stack ?? String(event.reason));
});

async function waitFor(assertion, timeoutMs = 3000) {
  const start = Date.now();
  let lastError;
  while (Date.now() - start < timeoutMs) {
    try {
      assertion();
      return;
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 25));
    }
  }
  throw lastError;
}

const server = await createServer({
  root: appRoot.pathname,
  appType: "spa",
  logLevel: "silent",
  server: { middlewareMode: true },
});

try {
  await server.ssrLoadModule("/src/main.tsx");
  await waitFor(() => {
    if (runtimeErrors.length) {
      throw new Error(runtimeErrors.join("\n"));
    }

    const text = document.body.textContent ?? "";
    const requiredText = [
      "Ermes Gasparini",
      "Artyom Morozov",
      "Evidence Snapshot",
      "Mechanism Map",
      "Argument paths you can inspect",
      "Every claim stays inspectable",
      "115",
    ];

    for (const expected of requiredText) {
      if (!text.includes(expected)) {
        throw new Error(`Smoke render missing expected text: ${expected}`);
      }
    }
  });

  console.log("Smoke render passed");
} finally {
  console.error = originalConsoleError;
  await server.close();
}
