#!/usr/bin/env node
// Verify the CSP sha256 hashes in vercel.json match the inline scripts in dist/index.html.
// Run after `vite build`. Fail-closed: any drift exits non-zero so CI catches it before deploy.

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SITE = resolve(__dirname, "..");

const html = readFileSync(resolve(SITE, "dist/index.html"), "utf8");
const vercelJson = JSON.parse(readFileSync(resolve(SITE, "vercel.json"), "utf8"));

// Extract every bare `<script>` block (no attributes — the only CSP-relevant kind here).
// `type="application/ld+json"` and `src=...` blocks are not subject to script-src enforcement.
const inlineBlocks = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
const inlineHashes = inlineBlocks.map((body) => createHash("sha256").update(body, "utf8").digest("base64"));

const sRoute = vercelJson.headers.find((h) => h.source === "/s/(.*)");
if (!sRoute) {
  console.error("verify-csp-hash: no /s/(.*) header entry in vercel.json");
  process.exit(1);
}
const csp = sRoute.headers.find((h) => h.key === "Content-Security-Policy");
if (!csp) {
  console.error("verify-csp-hash: no Content-Security-Policy on /s/(.*) route");
  process.exit(1);
}

const scriptSrc = csp.value.match(/script-src ([^;]+);/)?.[1] ?? "";
const cspHashes = [...scriptSrc.matchAll(/'sha256-([A-Za-z0-9+/=]+)'/g)].map((m) => m[1]);

const missing = inlineHashes.filter((h) => !cspHashes.includes(h));
const stale = cspHashes.filter((h) => !inlineHashes.includes(h));

if (missing.length || stale.length) {
  console.error("verify-csp-hash: drift detected between dist/index.html and vercel.json");
  if (missing.length) console.error("  missing from CSP:", missing.map((h) => `'sha256-${h}'`).join(" "));
  if (stale.length) console.error("  stale in CSP:    ", stale.map((h) => `'sha256-${h}'`).join(" "));
  console.error(`  inline blocks in dist: ${inlineBlocks.length} | sha256 entries in CSP: ${cspHashes.length}`);
  process.exit(1);
}

console.log(`verify-csp-hash: OK (${inlineBlocks.length} inline script(s), all hashes match)`);
