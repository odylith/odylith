#!/usr/bin/env node

import fs from 'fs/promises';
import path from 'path';
import process from 'process';
import readline from 'readline';
import { createRequire } from 'module';
import { pathToFileURL } from 'url';

function parseArgs(argv) {
  const args = { mermaidCliRoot: '' };
  for (let index = 0; index < argv.length; index += 1) {
    const token = String(argv[index] || '').trim();
    if (token === '--mermaid-cli-root') {
      args.mermaidCliRoot = String(argv[index + 1] || '').trim();
      index += 1;
    }
  }
  return args;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.mermaidCliRoot) {
    throw new Error('missing --mermaid-cli-root');
  }

  const packageRoot = path.resolve(args.mermaidCliRoot);
  const packageRequire = createRequire(path.join(packageRoot, 'package.json'));
  const puppeteerModule = packageRequire('puppeteer');
  const puppeteer = puppeteerModule.default ?? puppeteerModule;
  const mermaidModule = await import(pathToFileURL(path.join(packageRoot, 'src', 'index.js')).href);
  const renderMermaid = mermaidModule.renderMermaid;
  if (typeof renderMermaid !== 'function') {
    throw new Error('mermaid-cli renderMermaid export unavailable');
  }
  const mermaidPackage = packageRequire('mermaid');
  const mermaid = mermaidPackage.default ?? mermaidPackage;
  if (typeof mermaid.parse !== 'function') {
    throw new Error('mermaid parse export unavailable');
  }

  let browser = null;
  const ensureBrowser = async () => {
    if (browser !== null) {
      return browser;
    }
    browser = await puppeteer.launch({ headless: 'shell' });
    return browser;
  };

  const closeBrowser = async () => {
    if (browser === null) {
      return;
    }
    const current = browser;
    browser = null;
    await current.close();
  };

  const emit = payload => {
    process.stdout.write(`${JSON.stringify(payload)}\n`);
  };

  const parseLineNumber = message => {
    const match = /Parse error on line\s+(\d+)/i.exec(String(message || ''));
    return match ? Number.parseInt(match[1], 10) : null;
  };

  const buildValidationError = ({ job, definition, error }) => {
    const sourceMmd = String(job.source_mmd || '').trim();
    const diagramId = String(job.diagram_id || '').trim() || sourceMmd || 'unknown-diagram';
    const message = error instanceof Error ? error.message || String(error) : String(error);
    const detail = String(message || '').split(/\r?\n/, 1)[0].trim();
    const line = parseLineNumber(message);
    const lines = String(definition || '').split(/\r?\n/);
    const contextIndex =
      lines.length === 0 || line === null ? -1 : Math.min(Math.max(line - 1, 0), lines.length - 1);
    const lineContext = contextIndex >= 0 ? String(lines[contextIndex] || '').trimEnd() : '';
    return {
      name: 'MermaidValidationError',
      error: `${diagramId} failed: ${sourceMmd}${line !== null ? `:${line}` : ''}`,
      diagram_id: diagramId,
      source_mmd: sourceMmd,
      line,
      line_context: lineContext,
      detail,
    };
  };

  const validateJobs = async jobs => {
    for (const job of jobs) {
      const sourceMmd = String(job.source_mmd || '').trim();
      const resolvedSourceMmd = path.resolve(sourceMmd);
      if (!sourceMmd) {
        throw new Error('validation job missing source_mmd');
      }
      const definition = await fs.readFile(resolvedSourceMmd, 'utf-8');
      try {
        await mermaid.parse(definition);
      } catch (error) {
        const validationError = buildValidationError({ job, definition, error });
        throw Object.assign(new Error(validationError.error), validationError);
      }
    }
  };

  const renderJobs = async jobs => {
    const activeBrowser = await ensureBrowser();
    for (const job of jobs) {
      const sourceMmd = path.resolve(String(job.source_mmd || '').trim());
      const sourceSvg = path.resolve(String(job.source_svg || '').trim());
      const sourcePng = path.resolve(String(job.source_png || '').trim());
      if (!sourceMmd || !sourceSvg || !sourcePng) {
        throw new Error('render job missing source paths');
      }
      const definition = await fs.readFile(sourceMmd, 'utf-8');
      const svg = await renderMermaid(activeBrowser, definition, 'svg');
      const png = await renderMermaid(activeBrowser, definition, 'png');
      await fs.mkdir(path.dirname(sourceSvg), { recursive: true });
      await fs.mkdir(path.dirname(sourcePng), { recursive: true });
      await fs.writeFile(sourceSvg, svg.data);
      await fs.writeFile(sourcePng, png.data);
    }
  };

  const rl = readline.createInterface({
    input: process.stdin,
    crlfDelay: Infinity,
  });

  const shutdown = async () => {
    rl.close();
    await closeBrowser();
  };

  process.on('SIGINT', () => {
    shutdown().finally(() => process.exit(0));
  });
  process.on('SIGTERM', () => {
    shutdown().finally(() => process.exit(0));
  });

  for await (const line of rl) {
    const raw = String(line || '').trim();
    if (!raw) {
      continue;
    }
    let payload;
    try {
      payload = JSON.parse(raw);
    } catch (error) {
      emit({ ok: false, error: `invalid JSON: ${error.message}` });
      continue;
    }
    const command = String(payload.command || '').trim().toLowerCase();
    try {
      if (command === 'shutdown') {
        emit({ ok: true, command: 'shutdown' });
        await shutdown();
        return;
      }
      if (command === 'validate') {
        const jobs = Array.isArray(payload.jobs) ? payload.jobs : [];
        await validateJobs(jobs);
        emit({ ok: true, command: 'validate', validated: jobs.length });
        continue;
      }
      if (command !== 'render') {
        throw new Error(`unsupported command: ${command || '<empty>'}`);
      }
      const jobs = Array.isArray(payload.jobs) ? payload.jobs : [];
      await renderJobs(jobs);
      emit({ ok: true, command: 'render', rendered: jobs.length });
    } catch (error) {
      if (error && typeof error === 'object' && error.name === 'MermaidValidationError') {
        emit({
          ok: false,
          name: error.name,
          error: error.message,
          diagram_id: error.diagram_id,
          source_mmd: error.source_mmd,
          line: error.line,
          line_context: error.line_context,
          detail: error.detail,
        });
        continue;
      }
      emit({ ok: false, error: error instanceof Error ? error.message : String(error) });
    }
  }

  await closeBrowser();
}

main().catch(error => {
  const message = error instanceof Error ? error.stack || error.message : String(error);
  process.stderr.write(`${message}\n`);
  process.exit(1);
});
