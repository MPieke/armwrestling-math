import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";

const distAssets = new URL("../dist/assets/", import.meta.url);
const forbiddenTokens = [
  "#f2eadc",
  "#f8f1e6",
  "#eadcc8",
  "#f5efe4",
  "#fff9ee",
  "#ffefcf",
  "#fffaf0",
  "#fffdf8",
  "255 249 238",
  "255 239 207",
  "255 255 255 / 68%",
];

const files = await readdir(distAssets);
const cssFiles = files.filter((file) => file.endsWith(".css"));

if (!cssFiles.length) {
  throw new Error("No production CSS bundle found in app/dist/assets");
}

const failures = [];

for (const file of cssFiles) {
  const css = await readFile(join(distAssets.pathname, file), "utf8");
  for (const token of forbiddenTokens) {
    if (css.toLowerCase().includes(token.toLowerCase())) {
      failures.push(`${file}: ${token}`);
    }
  }
}

if (failures.length) {
  throw new Error(`Legacy cream theme tokens leaked into production CSS:\n${failures.join("\n")}`);
}

console.log("Dark theme CSS guard passed");
