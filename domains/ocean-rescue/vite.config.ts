import { defineConfig, type Plugin } from "vite";
import { readFileSync } from "node:fs";
import { relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL(".", import.meta.url));
const SRC_ROOT = resolve(ROOT, "src");
const MANIFEST_PATH = resolve(SRC_ROOT, "build-manifest.json");
const TEMPLATE_PATH = resolve(SRC_ROOT, "index.template.html");
const DEV_ENTRY_PATH = resolve(ROOT, "index.dev.html");

const CSS_MARKER = "<!-- OCEAN_RESCUE_CSS -->";
const SCRIPTS_MARKER = "<!-- OCEAN_RESCUE_SCRIPTS -->";
const DEV_ENTRY_MARKER = "<!-- OCEAN_RESCUE_DEV_ENTRY -->";

const URL_SCHEME_RE = /^[a-zA-Z][a-zA-Z0-9+.-]*:/;

function fail(message: string): never {
  throw new Error(message);
}

function fileExists(absolutePath: string): boolean {
  try {
    readFileSync(absolutePath);
    return true;
  } catch {
    return false;
  }
}

/** Reject unsafe manifest-derived paths; return the resolved absolute source path. */
function assertSrcPath(raw: string, label: string): string {
  if (typeof raw !== "string" || raw.length === 0) {
    fail(`${label}: empty path`);
  }
  if (URL_SCHEME_RE.test(raw)) {
    fail(`${label}: absolute URL scheme not allowed: ${raw}`);
  }
  if (raw.startsWith("//")) {
    fail(`${label}: protocol-relative path not allowed: ${raw}`);
  }
  if (raw.split("/").some((part) => part === "..")) {
    fail(`${label}: ".." traversal not allowed: ${raw}`);
  }
  const candidate = resolve(SRC_ROOT, raw);
  if (!candidate.startsWith(SRC_ROOT + "/")) {
    fail(`${label}: path escapes domain src root: ${raw}`);
  }
  if (!fileExists(candidate)) {
    fail(`${label}: file not found: ${raw}`);
  }
  return candidate;
}

function publicUrl(absolutePath: string): string {
  return "/" + relative(ROOT, absolutePath).split(pathSep()).join("/");
}

function pathSep(): string {
  return "/";
}

interface OrderedSources {
  styles: string[];
  scripts: string[];
}

function loadOrderedSources(): OrderedSources {
  const manifest = JSON.parse(readFileSync(MANIFEST_PATH, "utf-8")) as {
    template?: unknown;
    styles?: unknown;
    scripts?: unknown;
  };
  const template = manifest.template;
  const styles = manifest.styles;
  const scripts = manifest.scripts;
  if (typeof template !== "string") fail("manifest.template must be a string");
  if (!Array.isArray(styles)) fail("manifest.styles must be an array");
  if (!Array.isArray(scripts)) fail("manifest.scripts must be an array");
  const templateAbs = assertSrcPath(template, "manifest.template");
  if (resolve(templateAbs) !== TEMPLATE_PATH) {
    fail("manifest.template must resolve to the canonical template");
  }
  const stylePaths = styles.map((entry, index) =>
    assertSrcPath(entry, `manifest.styles[${index}]`),
  );
  const scriptPaths = scripts.map((entry, index) => {
    if (typeof entry !== "object" || entry === null) {
      fail(`manifest.scripts[${index}] must be an object`);
    }
    const file = (entry as { file?: unknown }).file;
    if (typeof file !== "string") {
      fail(`manifest.scripts[${index}].file must be a string`);
    }
    return assertSrcPath(file, `manifest.scripts[${index}].file`);
  });
  return { styles: stylePaths, scripts: scriptPaths };
}

function deriveDocument(): string {
  const template = readFileSync(TEMPLATE_PATH, "utf-8");
  if (template.split(CSS_MARKER).length - 1 !== 1) {
    fail(`template must contain exactly one ${CSS_MARKER}`);
  }
  if (template.split(SCRIPTS_MARKER).length - 1 !== 1) {
    fail(`template must contain exactly one ${SCRIPTS_MARKER}`);
  }

  const { styles, scripts } = loadOrderedSources();

  const styleTags = styles
    .map((absolutePath) => `<link rel="stylesheet" href="${publicUrl(absolutePath)}">`)
    .join("\n  ");

  const scriptTags = scripts
    .map((absolutePath) => `<script src="${publicUrl(absolutePath)}"></script>`)
    .join("\n");

  return template.replace(CSS_MARKER, styleTags).replace(SCRIPTS_MARKER, scriptTags);
}

function relevantForReload(absolutePath: string): boolean {
  const rel = relative(ROOT, absolutePath);
  if (!rel) return false;
  const firstSegment = rel.split("/")[0];
  if (firstSegment === "node_modules" || firstSegment === "dist") return false;
  if (
    absolutePath === DEV_ENTRY_PATH ||
    absolutePath === MANIFEST_PATH ||
    absolutePath === TEMPLATE_PATH
  ) {
    return true;
  }
  return absolutePath.startsWith(SRC_ROOT + "/");
}

function oceanRescueDevTemplatePlugin(): Plugin {
  return {
    name: "ocean-rescue-dev-template",
    configureServer(server) {
      // The legacy classic scripts are served as plain scripts and therefore do
      // not belong to Vite's ESM HMR module graph. Vite therefore does not call
      // the `handleHotUpdate` hook for changes to them. To keep the dev lane
      // responsive, we register our own listener on Vite's file watcher and
      // explicitly send a full reload for any relevant source change.
      server.watcher.on("all", (_event, file) => {
        if (relevantForReload(file)) {
          server.ws.send({ type: "full-reload" });
        }
      });
    },
    transformIndexHtml: {
      order: "pre",
      handler(html, ctx) {
        if (resolve(ctx.filename) !== DEV_ENTRY_PATH) {
          return html;
        }
        if (html.split(DEV_ENTRY_MARKER).length - 1 !== 1) {
          fail("index.dev.html must contain exactly one OCEAN_RESCUE_DEV_ENTRY marker");
        }
        return deriveDocument();
      },
    },
  };
}

export default defineConfig({
  root: ROOT,
  plugins: [oceanRescueDevTemplatePlugin()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
  },
});