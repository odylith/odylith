#!/usr/bin/env node

import fs from 'fs/promises';
import path from 'path';
import process from 'process';
import readline from 'readline';
import { createRequire } from 'module';
import { fileURLToPath, pathToFileURL } from 'url';

const workerDir = path.dirname(fileURLToPath(import.meta.url));
const mermaidRenderConfigPath = path.join(workerDir, 'mermaid_render_config.json');

async function loadMermaidRenderConfig() {
  const raw = await fs.readFile(mermaidRenderConfigPath, 'utf-8');
  const parsed = JSON.parse(raw);
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('Mermaid render config must be a JSON object');
  }
  return parsed;
}

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
  const mermaidIIFEPath = packageRequire.resolve('mermaid/dist/mermaid.js');
  const zenumlIIFEPath = packageRequire.resolve('@mermaid-js/mermaid-zenuml/dist/mermaid-zenuml.js');
  const mermaidRenderConfig = await loadMermaidRenderConfig();
  let browser = null;
  let renderPage = null;
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
    if (renderPage !== null) {
      const page = renderPage;
      renderPage = null;
      await page.close();
    }
    await current.close();
  };

  const mermaidHTMLPath = path.join(packageRoot, 'dist', 'index.html');
  const ensureRenderPage = async () => {
    if (renderPage !== null) {
      return renderPage;
    }
    const activeBrowser = await ensureBrowser();
    renderPage = await activeBrowser.newPage();
    await renderPage.setViewport({ width: 1600, height: 1200 });
    renderPage.on('console', msg => {
      console.warn(msg.text());
    });
    await renderPage.goto(pathToFileURL(mermaidHTMLPath).href, { waitUntil: 'load' });
    await renderPage.addScriptTag({ path: mermaidIIFEPath });
    await renderPage.addScriptTag({ path: zenumlIIFEPath });
    return renderPage;
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

  const renderOutputs = async definition => {
    const page = await ensureRenderPage();
    const rendered = await page.evaluate(async definitionText => {
      const container = document.querySelector('#container');
      if (!container) {
        throw new Error('Mermaid render container missing');
      }
      container.innerHTML = '';
      document.body.style.background = 'white';
      await Promise.all(Array.from(document.fonts, font => font.load()));
      const globalWithMermaid = globalThis;
      const mermaid = globalWithMermaid.mermaid;
      const zenuml = globalWithMermaid['mermaid-zenuml'];
      const elkLayouts = globalWithMermaid.elkLayouts;
      if (!mermaid) {
        throw new Error('Mermaid global missing after worker bootstrap');
      }
      if (!zenuml) {
        throw new Error('Mermaid Zenuml plugin missing after worker bootstrap');
      }
      if (!globalWithMermaid.__odylithMermaidInitialized) {
        await mermaid.registerExternalDiagrams([zenuml]);
        if (elkLayouts) {
          mermaid.registerLayoutLoaders(elkLayouts);
        }
        mermaid.initialize({ ...globalWithMermaid.__odylithMermaidRenderConfig, startOnLoad: false });
        globalWithMermaid.__odylithMermaidInitialized = true;
      }
      globalWithMermaid.__odylithMermaidRenderCounter =
        (Number(globalWithMermaid.__odylithMermaidRenderCounter || 0) + 1);
      const renderId = `odylith-svg-${globalWithMermaid.__odylithMermaidRenderCounter}`;
      const { svg: svgText } = await mermaid.render(renderId, definitionText, container);
      container.innerHTML = svgText;
      const svg = container.getElementsByTagName?.('svg')?.[0];
      if (!svg) {
        throw new Error('svg not found');
      }
      globalWithMermaid.__odylithPolishRenderedSvg(svg);
      const xmlSerializer = new XMLSerializer();
      const svgXML = xmlSerializer.serializeToString(svg);
      const rect = svg.getBoundingClientRect();
      return {
        svgXML,
        clip: {
          x: Math.floor(rect.left),
          y: Math.floor(rect.top),
          width: Math.ceil(rect.width),
          height: Math.ceil(rect.height)
        }
      };
    }, definition);
    await page.setViewport({
      width: Math.max(rendered.clip.x + rendered.clip.width, 1),
      height: Math.max(rendered.clip.y + rendered.clip.height, 1)
    });
    const png = await page.screenshot({ clip: rendered.clip });
    return {
      svg: Buffer.from(rendered.svgXML, 'utf-8'),
      png
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
        await renderOutputs(definition);
      } catch (error) {
        const validationError = buildValidationError({ job, definition, error });
        throw Object.assign(new Error(validationError.error), validationError);
      }
    }
  };

  const renderJobs = async jobs => {
    for (const job of jobs) {
      const sourceMmd = path.resolve(String(job.source_mmd || '').trim());
      const sourceSvg = path.resolve(String(job.source_svg || '').trim());
      const sourcePng = path.resolve(String(job.source_png || '').trim());
      if (!sourceMmd || !sourceSvg || !sourcePng) {
        throw new Error('render job missing source paths');
      }
      const definition = await fs.readFile(sourceMmd, 'utf-8');
      let rendered;
      try {
        rendered = await renderOutputs(definition);
      } catch (error) {
        const validationError = buildValidationError({ job, definition, error });
        throw Object.assign(new Error(validationError.error), validationError);
      }
      await fs.mkdir(path.dirname(sourceSvg), { recursive: true });
      await fs.mkdir(path.dirname(sourcePng), { recursive: true });
      await fs.writeFile(sourceSvg, rendered.svg);
      await fs.writeFile(sourcePng, rendered.png);
    }
  };

  const renderPageConfig = async () => {
    const page = await ensureRenderPage();
    await page.evaluate(config => {
      globalThis.__odylithMermaidRenderConfig = config;
      globalThis.__odylithPolishRenderedSvg = svg => {
        svg.setAttribute(
          'style',
          'background: transparent; shape-rendering: geometricPrecision; text-rendering: geometricPrecision;',
        );
        const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
        style.textContent = `
          .node rect,
          .node circle,
          .node ellipse,
          .node polygon,
          .node path {
            stroke-width: 1.35px;
          }
          .node rect {
            rx: 8px;
            ry: 8px;
          }
          .cluster rect {
            rx: 14px;
            ry: 14px;
            stroke-width: 1.2px;
          }
          .edgePath .path,
          .flowchart-link {
            stroke-width: 1.45px;
          }
          .edgeLabel,
          .nodeLabel,
          .cluster-label {
            line-height: 1.35;
          }
        `;
        svg.insertBefore(style, svg.firstChild);
        const clusterPalette = [
          { fill: '#effcf9', stroke: '#9bd8cf', label: '#062f2b' },
          { fill: '#f1f7ff', stroke: '#a8c7f7', label: '#102f5f' },
          { fill: '#fff3f0', stroke: '#efb3a4', label: '#5c2418' },
          { fill: '#f2fbef', stroke: '#a9d69e', label: '#0f3a24' },
          { fill: '#fbf7ff', stroke: '#d3b9f5', label: '#31135f' },
        ];
        const nodePalette = {
          input: { fill: '#e8fbf7', stroke: '#5bbfb2', label: '#062f2b' },
          intelligence: { fill: '#eaf3ff', stroke: '#77a9ef', label: '#102f5f' },
          decision: { fill: '#ffece7', stroke: '#df8f7d', label: '#5c2418' },
          apply: { fill: '#f4ebff', stroke: '#ad8ae6', label: '#31135f' },
          memory: { fill: '#ebf9e8', stroke: '#7ec373', label: '#0f3a24' },
          neutral: { fill: '#f5f8fb', stroke: '#b7c7d9', label: '#1f2937' },
        };
        const clusterPaletteByBucket = {
          input: clusterPalette[0],
          intelligence: clusterPalette[1],
          decision: clusterPalette[2],
          apply: clusterPalette[4],
          memory: clusterPalette[3],
        };
        const fallbackNodeTones = [
          nodePalette.input,
          nodePalette.intelligence,
          nodePalette.decision,
          nodePalette.apply,
          nodePalette.memory,
          nodePalette.neutral,
        ];
        // Atlas owns rendered color for consistency across legacy and new diagrams.
        // Source Mermaid stays topology truth; rendered fill/stroke/text color is a
        // surface-level readability contract and may override authored color tokens.
        const numericAttr = (element, name) => {
          const value = Number.parseFloat(element?.getAttribute(name) || '');
          return Number.isFinite(value) ? value : null;
        };
        const translatePoint = element => {
          const match = /translate\(\s*([-\d.]+)(?:[\s,]+)([-\d.]+)\s*\)/.exec(element.getAttribute('transform') || '');
          if (!match) {
            return null;
          }
          const x = Number.parseFloat(match[1]);
          const y = Number.parseFloat(match[2]);
          if (!Number.isFinite(x) || !Number.isFinite(y)) {
            return null;
          }
          return { x, y };
        };
        const bucketForText = text => {
          const normalized = String(text || '').toLowerCase();
          if (/\?|decision|decide|gate|confirm|choose|blocked|valid|stale|ready|pass|fail|whether/.test(normalized)) {
            return 'decision';
          }
          if (/\b(apply|write|render|refresh|sync|update|publish|release|migrate|deploy|repair|scaffold|register|create|author|materialize|bundle)\b/.test(normalized)) {
            return 'apply';
          }
          if (/\b(memory|compass|state|ledger|history|cache|session|timeline|proof|observation)\b/.test(normalized)) {
            return 'memory';
          }
          if (/\b(input|intent|prompt|source|repo|docs|catalog|watch|signal|request|operator|user|external)\b/.test(normalized)) {
            return 'input';
          }
          if (/\b(engine|compiler|planner|routing|classifier|agent|runtime|registry|radar|atlas|casebook|tribunal|context|component|analysis|proposal)\b/.test(normalized)) {
            return 'intelligence';
          }
          return '';
        };
        const bucketForClassNames = element => {
          const classNames = Array.from(element?.classList || []).map(value => String(value || '').toLowerCase());
          for (const bucket of ['input', 'intelligence', 'decision', 'apply', 'memory']) {
            if (classNames.includes(bucket)) {
              return bucket;
            }
          }
          return '';
        };
        const toneForNode = (node, fallbackTone) => {
          const bucket = bucketForClassNames(node) || bucketForText(node.textContent || '');
          if (bucket && nodePalette[bucket]) {
            return nodePalette[bucket];
          }
          return fallbackTone || nodePalette.neutral;
        };
        const clusterLabelText = cluster => (
          Array.from(cluster.querySelectorAll('.cluster-label'))
            .map(label => label.textContent || '')
            .join(' ')
          || cluster.id
          || ''
        );
        const toneForCluster = (cluster, fallbackTone) => {
          const bucket = bucketForText(`${clusterLabelText(cluster)} ${cluster.id || ''}`);
          if (bucket && clusterPaletteByBucket[bucket]) {
            return clusterPaletteByBucket[bucket];
          }
          return fallbackTone;
        };
        for (const rect of svg.querySelectorAll('.node rect')) {
          rect.setAttribute('rx', rect.getAttribute('rx') || '8');
          rect.setAttribute('ry', rect.getAttribute('ry') || '8');
        }
        const clusterBounds = [];
        const clusterGroups = Array.from(svg.querySelectorAll('.cluster'));
        for (const [index, cluster] of clusterGroups.entries()) {
          const rect = cluster.querySelector('rect');
          if (!rect) {
            continue;
          }
          rect.setAttribute('rx', rect.getAttribute('rx') || '14');
          rect.setAttribute('ry', rect.getAttribute('ry') || '14');
          const authoredStyle = rect.getAttribute('style') || '';
          const tone = toneForCluster(cluster, clusterPalette[index % clusterPalette.length]);
          const x = numericAttr(rect, 'x');
          const y = numericAttr(rect, 'y');
          const width = numericAttr(rect, 'width');
          const height = numericAttr(rect, 'height');
          if (x !== null && y !== null && width !== null && height !== null) {
            clusterBounds.push({ x, y, width, height, tone });
          }
          rect.setAttribute(
            'style',
            `${authoredStyle};fill:${tone.fill} !important;stroke:${tone.stroke} !important;stroke-width:1.15px !important`,
          );
          for (const label of cluster.querySelectorAll('.cluster-label, .cluster-label span, .cluster-label text, .cluster-label p')) {
            label.setAttribute('style', `${label.getAttribute('style') || ''};color:${tone.label} !important;fill:${tone.label} !important`);
          }
        }
        const clusterToneForNode = node => {
          const point = translatePoint(node);
          if (!point) {
            return null;
          }
          const matches = clusterBounds
            .filter(bounds => (
              point.x >= bounds.x
              && point.x <= bounds.x + bounds.width
              && point.y >= bounds.y
              && point.y <= bounds.y + bounds.height
            ))
            .sort((a, b) => (a.width * a.height) - (b.width * b.height));
          return matches[0]?.tone || null;
        };
        const nodeShape = node => (
          node.querySelector(':scope > rect.label-container, :scope > rect.basic, :scope > polygon, :scope > circle, :scope > ellipse, :scope > path')
          || node.querySelector('rect.label-container, rect.basic, polygon, circle, ellipse, path')
        );
        for (const [index, node] of Array.from(svg.querySelectorAll('.node')).entries()) {
          const shape = nodeShape(node);
          if (!shape) {
            continue;
          }
          if (shape.tagName.toLowerCase() === 'rect') {
            shape.setAttribute('rx', shape.getAttribute('rx') || '8');
            shape.setAttribute('ry', shape.getAttribute('ry') || '8');
          }
          const authoredStyle = shape.getAttribute('style') || '';
          const clusterTone = clusterToneForNode(node);
          const fallbackTone = clusterTone || fallbackNodeTones[index % fallbackNodeTones.length];
          const tone = toneForNode(node, fallbackTone);
          shape.setAttribute(
            'style',
            `${authoredStyle};fill:${tone.fill} !important;stroke:${tone.stroke} !important;stroke-width:1.35px !important`,
          );
          for (const label of node.querySelectorAll('.label, .nodeLabel, .label span, .label text, .label p, .label div')) {
            label.setAttribute('style', `${label.getAttribute('style') || ''};color:${tone.label} !important;fill:${tone.label} !important`);
          }
        }
      };
    }, mermaidRenderConfig);
  };

  await renderPageConfig();

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
