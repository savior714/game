import { createHash } from "node:crypto";
import {
  existsSync,
  mkdirSync,
  writeFileSync,
  readFileSync,
} from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

import { type Plugin, type UserConfig } from "vite";

const ROOT = fileURLToPath(new URL(".", import.meta.url));
const SRC_ROOT = resolve(ROOT, "src");
const MANIFEST_PATH = resolve(SRC_ROOT, "build-manifest.json");
const LEGACY_MANIFEST_PATH = resolve(SRC_ROOT, "build-manifest.legacy.json");
const TEMPLATE_PATH = resolve(SRC_ROOT, "index.template.html");
const DEFAULT_ENTRY = "main.js";

const SCHEMA_VERSION = 1;

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
 * standalone packaging adapter. Both lanes share the same canonical-entry
 * boundary validation and IIFE bundling logic.
 */
export interface BundleLaneOptions {
  lane: "shadow" | "production";
  outFile: string;
  htmlFile: string | null;
  metadataFile: string;
  globalName: string;
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

interface Boundary {
  template: string;
  styleAbsolutePath: string;
  entryAbsolutePath: string;
  vendor: OrderedEntry;
  legacyScripts: OrderedEntry[];
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

/** Read an ordered script entry from the legacy manifest. */
function readLegacyScript(entry: unknown, index: number, label: string): OrderedEntry {
  if (typeof entry !== "object" || entry === null) {
    fail(`${label}[${index}] must be an object`);
  }
  const e = entry as { file?: unknown; namespace?: unknown; kind?: unknown };
  if (typeof e.file !== "string") {
    fail(`${label}[${index}].file must be a string`);
  }
  if (typeof e.namespace !== "string") {
    fail(`${label}[${index}].namespace must be a string`);
  }
  const kind = typeof e.kind === "string" ? e.kind : "app";
  return {
    raw: e.file,
    namespace: e.namespace,
    kind,
    absolutePath: assertSrcPath(e.file, `${label}[${index}].file`),
  };
}

function loadBoundary(): Boundary {
  const manifest = JSON.parse(readFileSync(MANIFEST_PATH, "utf-8")) as Record<
    string,
    unknown
  >;
  const legacy = JSON.parse(
    readFileSync(LEGACY_MANIFEST_PATH, "utf-8"),
  ) as Record<string, unknown>;

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

  const vendorRaw = manifest.vendor;
  if (typeof vendorRaw !== "object" || vendorRaw === null) {
    fail("manifest.vendor must be an object");
  }
  const vendor = readLegacyScript(vendorRaw, 0, "manifest.vendor");
  if (vendor.kind !== "vendor") fail("manifest.vendor.kind must be vendor");
  if (vendor.absolutePath !== resolve(SRC_ROOT, PIXI_CONTRACT.file)) {
    fail(`vendor file must be ${PIXI_CONTRACT.file}`);
  }
  if (vendor.namespace !== PIXI_CONTRACT.namespace) {
    fail(`vendor namespace must be ${PIXI_CONTRACT.namespace}`);
  }

  const entry = manifest.entry;
  if (typeof entry !== "string") fail("manifest.entry must be a string");
  const entryAbsolutePath = assertSrcPath(entry, "manifest.entry");
  if (resolve(entryAbsolutePath) !== resolve(SRC_ROOT, DEFAULT_ENTRY)) {
    fail(`manifest.entry must resolve to ${DEFAULT_ENTRY}`);
  }

  if (!Array.isArray(legacy.scripts) || legacy.scripts.length < 1) {
    fail("build-manifest.legacy.json must contain a non-empty scripts array");
  }
  const legacyScripts = legacy.scripts.map((entryItem, index) =>
    readLegacyScript(entryItem, index, "legacy.scripts"),
  );
  if (legacyScripts[0].kind !== "vendor") {
    fail("legacy.scripts[0] must be the vendor entry");
  }
  if (legacyScripts.filter((s) => s.kind === "vendor").length !== 1) {
    fail("legacy manifest must declare exactly one kind=vendor entry");
  }
  const appScripts = legacyScripts.slice(1);
  if (appScripts[appScripts.length - 1].raw !== "app.js") {
    fail("app.js must be the last legacy application script");
  }
  const files = new Set<string>();
  const namespaces = new Set<string>();
  for (const s of appScripts) {
    if (files.has(s.raw)) fail(`duplicate legacy application file: ${s.raw}`);
    files.add(s.raw);
    if (namespaces.has(s.namespace)) {
      fail(`duplicate legacy application namespace: ${s.namespace}`);
    }
    namespaces.add(s.namespace);
  }

  return {
    template: readFileSync(TEMPLATE_PATH, "utf-8"),
    styleAbsolutePath,
    entryAbsolutePath,
    vendor,
    legacyScripts: appScripts,
    namespaces: appScripts.map((s) => s.namespace),
  };
}

const STATIC_IMPORT_RE =
  /^import\s+(?:\{[^}]*\}\s*from\s+)?["']([^"']+)["']\s*;?/gm;

/**
 * Resolve a static relative specifier to its on-disk module. Bundler-style
 * extension resolution is used so both legacy ``.js`` files and migrated
 * ``.ts`` modules resolve deterministically without ambiguous specifiers.
 */
function resolveModuleTarget(current: string, spec: string): string {
  const base = resolve(dirname(current), spec);
  if (existsSync(base)) {
    return base;
  }
  for (const ext of [".ts", ".tsx", ".js", ".jsx"]) {
    const candidate = base + ext;
    if (existsSync(candidate)) {
      return candidate;
    }
  }
  fail(`entry graph references a missing file: ${spec}`);
}

/** Walk the static relative import graph from the canonical entry. */
function collectImportGraph(entryAbsolutePath: string): Set<string> {
  const seen = new Set<string>();
  const stack = [entryAbsolutePath];
  while (stack.length > 0) {
    const current = stack.pop()!;
    const normalized = normalizePath(current);
    if (seen.has(normalized)) continue;
    seen.add(normalized);
    const source = readFileSync(current, "utf-8");
    for (const match of source.matchAll(STATIC_IMPORT_RE)) {
      const spec = match[1];
      if (URL_SCHEME_RE.test(spec)) {
        fail(`entry graph contains a non-relative import: ${spec}`);
      }
      if (!spec.startsWith(".")) {
        fail(`entry graph contains a bare import: ${spec}`);
      }
      const target = resolveModuleTarget(current, spec);
      if (!target.startsWith(SRC_ROOT + "/")) {
        fail(`entry graph escapes src root: ${spec}`);
      }
      stack.push(target);
    }
  }
  return seen;
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
  const graphModules = collectImportGraph(boundary.entryAbsolutePath);
  const entryNormalized = normalizePath(boundary.entryAbsolutePath);
  const expectedModuleFiles = Array.from(graphModules)
    .filter((key) => key !== entryNormalized)
    .map((key) => relative(SRC_ROOT, key).split(sep).join("/"))
    .sort();

  const legacyRaws = new Set(boundary.legacyScripts.map((s) => s.raw));
  const applicationScripts = boundary.legacyScripts.map((s) => s.raw);

  return {
    name: `ocean-rescue-${options.lane}-bundle`,
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
      if (!normalizedModules.has(boundary.entryAbsolutePath)) {
        fail("canonical entry module missing from the bundle");
      }
      for (const key of moduleKeys) {
        const normalized = sourcePath(key);
        if (normalized === entryNormalized) {
          continue;
        }
        if (!normalized.startsWith(SRC_ROOT + "/")) {
          fail(`unexpected module entered the application chunk: ${key}`);
        }
      }
      for (const normalized of graphModules) {
        if (normalized === entryNormalized) continue;
        if (!normalizedModules.has(normalized)) {
          fail(`entry-graph module missing from the bundle: ${normalized}`);
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
      const rollbackOnlyProfile = resolve(SRC_ROOT, "profile.js");
      for (const key of moduleKeys) {
        if (sourcePath(key) === rollbackOnlyProfile) {
          fail("rollback-only legacy profile.js must not enter the bundle");
        }
      }
      const rollbackOnlyLaunch = resolve(SRC_ROOT, "launch.js");
      for (const key of moduleKeys) {
        if (sourcePath(key) === rollbackOnlyLaunch) {
          fail("rollback-only legacy launch.js must not enter the bundle");
        }
      }
      const rollbackOnlyState = resolve(SRC_ROOT, "state.js");
      for (const key of moduleKeys) {
        if (sourcePath(key) === rollbackOnlyState) {
          fail("rollback-only legacy state.js must not enter the bundle");
        }
      }
      const rollbackOnlyTravel = resolve(SRC_ROOT, "travel.js");
      for (const key of moduleKeys) {
        if (sourcePath(key) === rollbackOnlyTravel) {
          fail("rollback-only legacy travel.js must not enter the bundle");
        }
      }
      for (const normalized of graphModules) {
        if (normalized === entryNormalized) continue;
        const occurrences = moduleKeys.filter(
          (key) => sourcePath(key) === normalized,
        );
        if (occurrences.length !== 1) {
          fail(`entry-graph module must occur exactly once: ${normalized}`);
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
        entry: relative(SRC_ROOT, boundary.entryAbsolutePath).split(sep).join("/"),
        vendor: {
          file: boundary.vendor.raw,
          namespace: boundary.vendor.namespace,
          external: true,
        },
        legacy_script_count: applicationScripts.length,
        application_scripts: applicationScripts,
        expected_namespaces: boundary.namespaces.slice(),
        actual_module_files: expectedModuleFiles,
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
 * canonical-entry algorithm: the real ``src/main.js`` ESM entry owns the
 * application import graph, and the ordered legacy manifest is retained only
 * as the rollback authority. Output naming, metadata state, and the shadow
 * document emission differ per lane.
 */
export function createBundleLaneConfig(options: BundleLaneOptions): UserConfig {
  const boundary = loadBoundary();

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
        entry: boundary.entryAbsolutePath,
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
