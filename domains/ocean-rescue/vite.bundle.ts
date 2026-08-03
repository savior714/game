import { createHash } from "node:crypto";
import { mkdirSync, writeFileSync, readFileSync, realpathSync } from "node:fs";
import { join, relative, resolve, sep } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";

import { type Plugin, type UserConfig } from "vite";

const ROOT = fileURLToPath(new URL(".", import.meta.url));
const SRC_ROOT = resolve(ROOT, "src");
const MANIFEST_PATH = resolve(SRC_ROOT, "build-manifest.json");
const TEMPLATE_PATH = resolve(SRC_ROOT, "index.template.html");

const SCHEMA_VERSION = 1;

// Non-tracked deterministic entry, generated at build time from the manifest.
// Use the real tmpdir path so the module id is canonical (macOS /var -> /private/var).
const TMPDIR_ROOT = realpathSync(tmpdir());

const CSS_MARKER = "<!-- OCEAN_RESCUE_CSS -->";
const SCRIPTS_MARKER = "<!-- OCEAN_RESCUE_SCRIPTS -->";

const URL_SCHEME_RE = /^[a-zA-Z][a-zA-Z0-9+.-]*:/;

const PIXI_CONTRACT = {
  file: "vendor/pixi-8.19.0.min.js",
  namespace: "PIXI",
};

/**
 * Bundle-lane parameters. The shadow lane preserves the proven WP-20 output;
 * the production lane emits the canonical application bundle consumed by the
 * standalone packaging adapter. Both lanes share the same manifest-derived
 * boundary validation and IIFE bundling logic.
 */
export interface BundleLaneOptions {
  lane: "shadow" | "production";
  outFile: string;
  htmlFile: string | null;
  metadataFile: string;
  globalName: string;
  entryName: string;
  metadataState: string;
  target: string;
}

function fail(message: string): never {
  throw new Error(`[ocean-rescue-bundle] ${message}`);
}

function normalizePath(p: string): string {
  return p.split(sep).join("/");
}

interface OrderedEntry {
  raw: string;
  namespace: string;
  kind: string;
  absolutePath: string;
}

interface BundleModuleRecord {
  [moduleId: string]: unknown;
}

interface BundleChunk {
  type: "chunk";
  code: string;
  fileName: string;
  isEntry: boolean;
  isDynamicEntry: boolean;
  dynamicImports: string[];
  imports: string[];
  modules: BundleModuleRecord | undefined;
}

interface BundleOutputRecord {
  [fileName: string]: { type: "chunk" | "asset" } | BundleChunk;
}

interface Boundary {
  template: string;
  styleAbsolutePath: string;
  vendor: OrderedEntry;
  appScripts: OrderedEntry[];
  namespaces: string[];
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
  if (candidate !== SRC_ROOT && !candidate.startsWith(SRC_ROOT + "/")) {
    fail(`${label}: path escapes domain src root: ${raw}`);
  }
  try {
    readFileSync(candidate);
  } catch {
    fail(`${label}: file not found: ${raw}`);
  }
  return candidate;
}

function loadBoundary(): Boundary {
  const manifest = JSON.parse(readFileSync(MANIFEST_PATH, "utf-8")) as Record<
    string,
    unknown
  >;
  if (typeof manifest.template !== "string") fail("manifest.template must be a string");
  const templateAbs = assertSrcPath(manifest.template, "manifest.template");
  if (resolve(templateAbs) !== TEMPLATE_PATH) {
    fail("manifest.template must resolve to the canonical template");
  }
  if (
    !Array.isArray(manifest.styles) ||
    manifest.styles.length !== 1 ||
    typeof manifest.styles[0] !== "string"
  ) {
    fail("manifest.styles must contain exactly one stylesheet");
  }
  const styleAbsolutePath = assertSrcPath(
    manifest.styles[0] as string,
    "manifest.styles[0]",
  );
  if (!Array.isArray(manifest.scripts) || manifest.scripts.length < 2) {
    fail("manifest.scripts must be a non-empty array");
  }
  const scripts = manifest.scripts.map((entry, index) => {
    if (typeof entry !== "object" || entry === null) {
      fail(`manifest.scripts[${index}] must be an object`);
    }
    const e = entry as { file?: unknown; namespace?: unknown; kind?: unknown };
    if (typeof e.file !== "string") {
      fail(`manifest.scripts[${index}].file must be a string`);
    }
    if (typeof e.namespace !== "string") {
      fail(`manifest.scripts[${index}].namespace must be a string`);
    }
    const kind = typeof e.kind === "string" ? e.kind : "app";
    return {
      raw: e.file,
      namespace: e.namespace,
      kind,
      absolutePath: assertSrcPath(e.file, `manifest.scripts[${index}].file`),
    };
  });

  const vendor = scripts[0];
  if (vendor.kind !== "vendor") fail("first script must be the vendor entry");
  if (vendor.absolutePath !== resolve(SRC_ROOT, PIXI_CONTRACT.file)) {
    fail(`vendor file must be ${PIXI_CONTRACT.file}`);
  }
  if (vendor.namespace !== PIXI_CONTRACT.namespace) {
    fail(`vendor namespace must be ${PIXI_CONTRACT.namespace}`);
  }
  if (scripts.filter((s) => s.kind === "vendor").length !== 1) {
    fail("exactly one kind=vendor entry is required");
  }

  const appScripts = scripts.slice(1);
  if (appScripts[appScripts.length - 1].raw !== "app.js") {
    fail("app.js must be the last non-vendor script");
  }
  const files = new Set<string>();
  const namespaces = new Set<string>();
  for (const s of appScripts) {
    if (files.has(s.raw)) fail(`duplicate application file: ${s.raw}`);
    files.add(s.raw);
    if (namespaces.has(s.namespace)) {
      fail(`duplicate application namespace: ${s.namespace}`);
    }
    namespaces.add(s.namespace);
    const normalized = normalizePath(s.absolutePath);
    if (normalized.includes("/node_modules/pixi.js/")) {
      fail(`application script resolves inside node_modules/pixi.js: ${s.raw}`);
    }
  }

  return {
    template: readFileSync(TEMPLATE_PATH, "utf-8"),
    styleAbsolutePath,
    vendor,
    appScripts,
    namespaces: appScripts.map((s) => s.namespace),
  };
}

function virtualEntrySource(appScripts: OrderedEntry[]): string {
  // Side-effect imports in canonical manifest order. Each script attaches its
  // global namespace and references previously loaded globals (PIXI and earlier
  // OceanRescue.* namespaces) during its own execution, so order is preserved.
  const imports = appScripts
    .map((script) => `import ${JSON.stringify(normalizePath(script.absolutePath))};`)
    .join("\n");
  return `${imports}\n`;
}

function deriveDocument(boundary: Boundary, outFile: string): string {
  const template = boundary.template;
  if (template.split(CSS_MARKER).length - 1 !== 1) {
    fail(`template must contain exactly one ${CSS_MARKER}`);
  }
  if (template.split(SCRIPTS_MARKER).length - 1 !== 1) {
    fail(`template must contain exactly one ${SCRIPTS_MARKER}`);
  }
  const styleLink =
    `<link rel="stylesheet" href="/src/${relative(SRC_ROOT, boundary.styleAbsolutePath).split(sep).join("/")}">`;
  const pixiSrc = `/src/${relative(SRC_ROOT, boundary.vendor.absolutePath).split(sep).join("/")}`;
  const scriptTags = [
    `<script src="${pixiSrc}"></script>`,
    `<script src="/dist/${outFile}"></script>`,
  ].join("\n  ");
  return template.replace(CSS_MARKER, styleLink).replace(SCRIPTS_MARKER, scriptTags);
}

function sourcePath(moduleKey: string): string {
  const trimmed = moduleKey.replace(/^\0/, "");
  if (URL_SCHEME_RE.test(trimmed)) {
    return trimmed;
  }
  return resolve(trimmed);
}

function normalizeMetadataKeyOrder(payload: Record<string, unknown>): string {
  return JSON.stringify(payload, null, 2) + "\n";
}

function oceanRescueBundlePlugin(
  boundary: Boundary,
  options: BundleLaneOptions,
): Plugin {
  const entryFile = join(TMPDIR_ROOT, options.entryName);
  const expectedModules = new Map<string, string>();
  for (const script of boundary.appScripts) {
    expectedModules.set(normalizePath(script.absolutePath), script.raw);
  }
  const entryNormalized = normalizePath(entryFile);

  return {
    name: `ocean-rescue-${options.lane}-bundle`,
    buildStart() {
      // Regenerate the non-tracked entry after any prior dist empty-out.
      mkdirSync(join(entryFile, ".."), { recursive: true });
      writeFileSync(entryFile, virtualEntrySource(boundary.appScripts), "utf-8");
    },
    generateBundle(_options, bundle) {
      const chunks = Object.values(bundle).filter(
        (item) => (item as { type?: string }).type === "chunk",
      ) as BundleChunk[];
      if (chunks.length !== 1) {
        fail(`expected exactly one JS chunk, found ${chunks.length}`);
      }
      const entryChunk = chunks[0];
      if (entryChunk.isDynamicEntry) {
        fail("entry chunk must not be a dynamic entry");
      }
      const dynamicImportCount = (entryChunk.dynamicImports ?? []).length;
      if (dynamicImportCount !== 0) {
        fail(`entry chunk has dynamic imports: ${entryChunk.dynamicImports}`);
      }

      const moduleKeys = Object.keys(entryChunk.modules ?? {});
      const normalizedModules = new Set(moduleKeys.map((key) => sourcePath(key)));
      for (const [normalized, raw] of expectedModules) {
        if (!normalizedModules.has(normalized)) {
          fail(`expected application module missing from bundle: ${raw}`);
        }
      }
      for (const key of moduleKeys) {
        const normalized = sourcePath(key);
        if (normalized === entryNormalized) {
          continue;
        }
        if (!expectedModules.has(normalized)) {
          fail(`unexpected module entered the application chunk: ${key}`);
        }
      }
      const vendorNormalized = normalizePath(boundary.vendor.absolutePath);
      if (normalizedModules.has(vendorNormalized)) {
        fail("vendored Pixi source must not enter the application bundle");
      }
      for (const key of moduleKeys) {
        if (key.includes("/node_modules/pixi.js/")) {
          fail(`pixi.js package module entered the bundle: ${key}`);
        }
      }
      for (const [expectedNormalized, raw] of expectedModules) {
        const occurrences = moduleKeys.filter(
          (key) => sourcePath(key) === expectedNormalized,
        );
        if (occurrences.length !== 1) {
          fail(`application module must occur exactly once: ${raw}`);
        }
      }

      const bundleBytes = Buffer.byteLength(entryChunk.code, "utf-8");
      const bundleSha256 = createHash("sha256")
        .update(entryChunk.code, "utf-8")
        .digest("hex");

      const emittedFiles = [
        options.outFile,
        options.metadataFile,
        ...(options.htmlFile ? [options.htmlFile] : []),
      ].sort();

      if (options.htmlFile) {
        this.emitFile({
          type: "asset",
          fileName: options.htmlFile,
          source: deriveDocument(boundary, options.outFile),
        });
      }

      const metadata = {
        schema_version: SCHEMA_VERSION,
        state: options.metadataState,
        format: "iife",
        target: options.target,
        minifier: "oxc",
        sourcemap: false,
        bundle_file: options.outFile,
        bundle_bytes: bundleBytes,
        bundle_sha256: bundleSha256,
        vendor: {
          file: boundary.vendor.raw,
          namespace: boundary.vendor.namespace,
          external: true,
        },
        application_script_count: boundary.appScripts.length,
        application_scripts: boundary.appScripts.map((s) => s.raw),
        expected_namespaces: boundary.namespaces.slice(),
        actual_module_files: boundary.appScripts.map((s) => s.raw),
        dynamic_import_count: dynamicImportCount,
        output_files: emittedFiles,
      };
      this.emitFile({
        type: "asset",
        fileName: options.metadataFile,
        source: normalizeMetadataKeyOrder(metadata as unknown as Record<string, unknown>),
      });
    },
  };
}

/**
 * Create the deterministic IIFE application-bundle configuration for one lane.
 *
 * Both the WP-20 shadow lane and the WP-21 production lane share this single
 * manifest-to-bundle algorithm; only output naming, metadata state, and the
 * shadow document emission differ.
 */
export function createBundleLaneConfig(options: BundleLaneOptions): UserConfig {
  const boundary = loadBoundary();
  const entryFile = join(TMPDIR_ROOT, options.entryName);

  return {
    root: ROOT,
    define: {},
    build: {
      outDir: "dist",
      target: options.target,
      minify: "oxc",
      sourcemap: false,
      copyPublicDir: false,
      emptyOutDir: true,
      reportCompressedSize: true,
      cssCodeSplit: false,
      modulePreload: false,
      lib: {
        entry: entryFile,
        name: options.globalName,
        formats: ["iife"],
        fileName: () => options.outFile,
      },
      rolldownOptions: {
        output: {
          inlineDynamicImports: true,
        },
      },
    },
    plugins: [oceanRescueBundlePlugin(boundary, options)],
  };
}
