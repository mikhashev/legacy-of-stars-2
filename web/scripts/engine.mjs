// Runs the repository's engine builder (scripts/build_web_engine.py) from npm.
// The interpreter is `python`, overridable with the PYTHON environment variable.
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const builder = resolve(here, "..", "..", "scripts", "build_web_engine.py");
const python = process.env.PYTHON || "python";

const run = spawnSync(python, [builder], { stdio: "inherit", shell: process.platform === "win32" });
if (run.error) {
  console.error(`[engine] cannot run '${python}': ${run.error.message}. Set PYTHON to your interpreter.`);
  process.exit(1);
}
process.exit(run.status ?? 1);
