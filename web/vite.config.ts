import { cpSync, existsSync, mkdirSync, statSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { defineConfig, type Plugin } from "vite";

const require = createRequire(import.meta.url);

/** The Pyodide runtime files the browser needs; everything else in the package is node-only. */
const PYODIDE_ASSETS = [
  "pyodide.mjs",
  "pyodide.asm.mjs",
  "pyodide.asm.wasm",
  "python_stdlib.zip",
  "pyodide-lock.json",
];

/**
 * Copy the Pyodide runtime out of node_modules into `public/pyodide/`.
 *
 * The worker loads it from there at run time (see src/worker.ts), so nothing about Pyodide
 * goes through Vite's bundler - its `import("node:fs")` branches and its 9.6 MB .wasm are
 * both things a bundler handles badly. Self-hosting instead of using the CDN keeps the game
 * offline-first: after the first load everything comes from our own origin.
 */
function pyodideAssets(): Plugin {
  return {
    name: "los-pyodide-assets",
    buildStart() {
      const from = dirname(require.resolve("pyodide/package.json"));
      const to = join(import.meta.dirname, "public", "pyodide");
      mkdirSync(to, { recursive: true });
      for (const name of PYODIDE_ASSETS) {
        const src = join(from, name);
        const dest = join(to, name);
        if (existsSync(dest) && statSync(dest).size === statSync(src).size) continue;
        cpSync(src, dest);
      }
    },
  };
}

export default defineConfig({
  base: "./",
  plugins: [pyodideAssets()],
  build: {
    target: "es2022",
    // engine.zip and the Pyodide runtime are served as-is from public/, never inlined.
    assetsInlineLimit: 0,
  },
  worker: { format: "es" },
  server: { headers: { "Cache-Control": "no-store" } },
});
