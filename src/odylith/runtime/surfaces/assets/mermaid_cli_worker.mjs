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
    browser = await puppeteer.launch({
      headless: 'shell',
      args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
    });
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
          'background: #FFFFFF; shape-rendering: geometricPrecision; text-rendering: geometricPrecision;',
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
            stroke-width: 1.15px;
          }
          .edgePath .path,
          .flowchart-link {
            stroke: #B9C7D8;
            stroke-width: 1.25px;
            opacity: 0.65;
          }
          .edgeLabel {
            color: #24384A;
            fill: #24384A;
          }
          .edgeLabel rect,
          .edgeLabel background {
            fill: #FFFFFF;
            opacity: 0.96;
          }
          .edgeLabel,
          .nodeLabel,
          .cluster-label {
            line-height: 1.35;
          }
        `;
        svg.insertBefore(style, svg.firstChild);
        const BODY_TEXT = '#0F1D30';
        const STRUCTURE_LABEL = '#24384A';
        const rewriteManagedTextColors = () => {
          for (const styleNode of svg.querySelectorAll('style')) {
            styleNode.textContent = String(styleNode.textContent || '')
              .replace(/#132033/gi, BODY_TEXT)
              .replace(/#293D52/gi, STRUCTURE_LABEL);
          }
        };
        rewriteManagedTextColors();
        const nodePalette = {
          neutral: { fill: '#FBFDFF', stroke: '#D8E5F4', label: BODY_TEXT },
          primary: { fill: '#EFF6FF', stroke: '#BFD7FE', label: BODY_TEXT },
          execution: { fill: '#ECFDFB', stroke: '#A7E9E3', label: BODY_TEXT },
          governance: { fill: '#F5F3FF', stroke: '#DDD6FE', label: BODY_TEXT },
          constraint: { fill: '#FFF8E6', stroke: '#F6D98B', label: BODY_TEXT },
          invalid: { fill: '#FFF1F0', stroke: '#F7B4AE', label: BODY_TEXT },
        };
        const clusterPalette = [
          { bucket: 'neutral', fill: '#FBFDFF', stroke: '#D8E5F4', label: STRUCTURE_LABEL },
          { bucket: 'primary', fill: '#FBFDFF', stroke: '#BFD7FE', label: STRUCTURE_LABEL },
          { bucket: 'execution', fill: '#FBFDFF', stroke: '#A7E9E3', label: STRUCTURE_LABEL },
          { bucket: 'governance', fill: '#FBFDFF', stroke: '#DDD6FE', label: STRUCTURE_LABEL },
          { bucket: 'constraint', fill: '#FBFDFF', stroke: '#F6D98B', label: STRUCTURE_LABEL },
          { bucket: 'invalid', fill: '#FBFDFF', stroke: '#F7B4AE', label: STRUCTURE_LABEL },
        ];
        const clusterPaletteByBucket = {
          neutral: clusterPalette[0],
          primary: clusterPalette[1],
          execution: clusterPalette[2],
          governance: clusterPalette[3],
          constraint: clusterPalette[4],
          invalid: clusterPalette[5],
        };
        const connectorPalette = {
          default: { stroke: '#B9C7D8', width: '1.25px', opacity: '0.65', dash: '' },
          primary: { stroke: '#52677F', width: '1.75px', opacity: '0.90', dash: '' },
          evidence: { stroke: '#0F766E', width: '1.5px', opacity: '0.80', dash: '4 4' },
          dependency: { stroke: '#B7791F', width: '1.5px', opacity: '0.75', dash: '3 3' },
          invalid: { stroke: '#B42318', width: '1.5px', opacity: '0.80', dash: '5 3' },
        };
        const classBucketAliases = {
          actor: 'primary',
          anchor: 'primary',
          input: 'primary',
          intent: 'primary',
          request: 'primary',
          shell: 'primary',
          source: 'primary',
          report: 'primary',
          metadata: 'primary',
          diagram: 'primary',
          service: 'execution',
          runtime: 'execution',
          engine: 'execution',
          execution: 'execution',
          apply: 'execution',
          memory: 'execution',
          cache: 'execution',
          persistence: 'execution',
          notification: 'execution',
          component: 'execution',
          intelligence: 'governance',
          governance: 'governance',
          policy: 'governance',
          rule: 'governance',
          owner: 'governance',
          truth: 'governance',
          proof: 'governance',
          delivery: 'governance',
          decision: 'constraint',
          gate: 'constraint',
          followup: 'constraint',
          fallback: 'constraint',
          constraint: 'constraint',
          warning: 'constraint',
          denied: 'invalid',
          invalid: 'invalid',
          failure: 'invalid',
          error: 'invalid',
          neutral: 'neutral',
          note: 'neutral',
        };
        // Atlas owns rendered semantic color for consistency across legacy and
        // new diagrams. Source Mermaid stays topology truth; rendered color is
        // a surface-level readability contract and may override authored color
        // tokens when those tokens drift from the Atlas semantic language.
        // Containers default to neutral structure and only use semantic borders
        // when their label clearly names a semantic region. Nodes carry the
        // semantic fill; unclassified nodes stay neutral instead of rotating
        // through arbitrary colors or inheriting a container tone.
        const stripManagedShapeStyle = styleText => (
          String(styleText || '')
            .split(';')
            .map(part => part.trim())
            .filter(part => part && !/^(fill|stroke|stroke-width)\s*:/i.test(part))
            .join(';')
        );
        const managedShapeStyle = (authoredStyle, managedStyleText) => {
          const retainedStyle = stripManagedShapeStyle(authoredStyle);
          return `${retainedStyle ? `${retainedStyle};` : ''}${managedStyleText}`;
        };
        const stripManagedEdgeStyle = styleText => (
          String(styleText || '')
            .split(';')
            .map(part => part.trim())
            .filter(part => part && !/^(stroke|stroke-width|stroke-dasharray|opacity)\s*:/i.test(part))
            .join(';')
        );
        const managedEdgeStyle = (authoredStyle, tone) => {
          const retainedStyle = stripManagedEdgeStyle(authoredStyle);
          const dash = tone.dash ? `stroke-dasharray:${tone.dash} !important;` : 'stroke-dasharray:none !important;';
          return `${retainedStyle ? `${retainedStyle};` : ''}stroke:${tone.stroke} !important;stroke-width:${tone.width} !important;opacity:${tone.opacity} !important;${dash}`;
        };
        const stripManagedTextStyle = styleText => (
          String(styleText || '')
            .split(';')
            .map(part => part.trim())
            .filter(part => part && !/^(color|fill)\s*:/i.test(part))
            .join(';')
        );
        const managedTextStyle = (authoredStyle, color) => {
          const retainedStyle = stripManagedTextStyle(authoredStyle);
          return `${retainedStyle ? `${retainedStyle};` : ''}color:${color} !important;fill:${color} !important`;
        };
        const bucketForText = text => {
          const normalized = String(text || '').toLowerCase();
          if (/\b(denied?|reject(?:ed|ion)?|invalid|security violation|policy rejection|destructive failure|unrecoverable)\b/.test(normalized)) {
            return 'invalid';
          }
          if (/\b(ambiguous|ambiguity|missing|unresolved|assumption|partial|fallback|conflict|retry|pending|conditional|condition|stale|blocked|blocker|gap|decision|decide|gate|confirm|choose|whether)\b/.test(normalized) || /\?/.test(normalized)) {
            return 'constraint';
          }
          if (/\b(policy|grant|ownership|owner|governance|rule|provenance|authorization|authorisation|access|tribunal|adjudication|audit|dossier|reasoning|evidence|proof)\b/.test(normalized)) {
            return 'governance';
          }
          if (/\b(runtime|execution|service|cache|lookup|notification|persist|persistence|record|create|write|apply|render|refresh|sync|update|publish|release|migrate|deploy|repair|scaffold|register|materialize|bundle|worker|daemon|process|valid|resolved|success|memory|compass|state|ledger|history|timeline|observation)\b/.test(normalized)) {
            return 'execution';
          }
          if (/\b(user|developer|operator|input|intent|prompt|request|api|entry|source|repo|docs|catalog|watch|signal|external|atlas|diagram|metadata|report|final|dashboard|output|artifact|proposal)\b/.test(normalized)) {
            return 'primary';
          }
          return '';
        };
        const bucketForClassNames = element => {
          const classNames = Array.from(element?.classList || []).map(value => String(value || '').toLowerCase());
          for (const className of classNames) {
            if (nodePalette[className]) {
              return className;
            }
            if (classBucketAliases[className]) {
              return classBucketAliases[className];
            }
          }
          return '';
        };
        const toneForNode = node => {
          const bucket = bucketForClassNames(node) || bucketForText(node.textContent || '');
          if (bucket && nodePalette[bucket]) {
            return nodePalette[bucket];
          }
          return nodePalette.neutral;
        };
        const clusterLabelText = cluster => (
          Array.from(cluster.querySelectorAll('.cluster-label'))
            .map(label => label.textContent || '')
            .join(' ')
          || cluster.id
          || ''
        );
        const toneForCluster = cluster => {
          const bucket = bucketForClassNames(cluster) || bucketForText(`${clusterLabelText(cluster)} ${cluster.id || ''}`);
          if (bucket && clusterPaletteByBucket[bucket]) {
            return clusterPaletteByBucket[bucket];
          }
          return clusterPaletteByBucket.neutral;
        };
        for (const rect of svg.querySelectorAll('.node rect')) {
          rect.setAttribute('rx', rect.getAttribute('rx') || '8');
          rect.setAttribute('ry', rect.getAttribute('ry') || '8');
        }
        for (const cluster of Array.from(svg.querySelectorAll('.cluster'))) {
          const rect = cluster.querySelector('rect');
          if (!rect) {
            continue;
          }
          rect.setAttribute('rx', rect.getAttribute('rx') || '14');
          rect.setAttribute('ry', rect.getAttribute('ry') || '14');
          const authoredStyle = rect.getAttribute('style') || '';
          const tone = toneForCluster(cluster);
          rect.setAttribute(
            'style',
            managedShapeStyle(
              authoredStyle,
              `fill:${tone.fill} !important;stroke:${tone.stroke} !important;stroke-width:1.15px !important`,
            ),
          );
          for (const label of cluster.querySelectorAll('.cluster-label, .cluster-label span, .cluster-label text, .cluster-label p')) {
            label.setAttribute('style', managedTextStyle(label.getAttribute('style') || '', tone.label));
          }
        }
        const nodeShape = node => (
          node.querySelector(':scope > rect.label-container, :scope > rect.basic, :scope > polygon, :scope > circle, :scope > ellipse, :scope > path')
          || node.querySelector('rect.label-container, rect.basic, polygon, circle, ellipse, path')
        );
        for (const node of Array.from(svg.querySelectorAll('.node'))) {
          const shape = nodeShape(node);
          if (!shape) {
            continue;
          }
          if (shape.tagName.toLowerCase() === 'rect') {
            shape.setAttribute('rx', shape.getAttribute('rx') || '8');
            shape.setAttribute('ry', shape.getAttribute('ry') || '8');
          }
          const authoredStyle = shape.getAttribute('style') || '';
          const tone = toneForNode(node);
          shape.setAttribute(
            'style',
            managedShapeStyle(
              authoredStyle,
              `fill:${tone.fill} !important;stroke:${tone.stroke} !important;stroke-width:1.35px !important`,
            ),
          );
          for (const label of node.querySelectorAll('.label, .nodeLabel, .label text, .label p, .label div')) {
            label.setAttribute('style', managedTextStyle(label.getAttribute('style') || '', tone.label));
          }
        }
        const bucketForEdge = edge => {
          const edgeGroup = edge?.closest?.('.edgePath');
          const text = `${edge?.id || ''} ${edgeGroup?.id || ''} ${Array.from(edge?.classList || []).join(' ')}`.toLowerCase();
          if (/\b(denied?|reject(?:ed|ion)?|invalid|security violation|policy rejection|destructive failure|unrecoverable)\b/.test(text)) {
            return 'invalid';
          }
          if (/\b(evidence|validation|validated|proof|verified|verify|provenance)\b/.test(text)) {
            return 'evidence';
          }
          if (/\b(dependency|depends|retry|assumption|fallback|missing|partial|pending|conditional|conflict|ambiguous|unresolved)\b/.test(text)) {
            return 'dependency';
          }
          if (/\b(primary|selected|entry|request|intent|api|final|report)\b/.test(text)) {
            return 'primary';
          }
          const authoredStyle = String(edge?.getAttribute?.('style') || '');
          const authoredDash = String(edge?.getAttribute?.('stroke-dasharray') || '');
          if (/stroke-dasharray\s*:/i.test(authoredStyle) || authoredDash) {
            return 'dependency';
          }
          return 'default';
        };
        for (const edge of svg.querySelectorAll('.edgePath .path, .flowchart-link')) {
          const tone = connectorPalette[bucketForEdge(edge)] || connectorPalette.default;
          edge.setAttribute('style', managedEdgeStyle(edge.getAttribute('style') || '', tone));
        }
        for (const label of svg.querySelectorAll('.edgeLabel, .edgeLabel span, .edgeLabel text, .edgeLabel p, .edgeLabel div')) {
          label.setAttribute('style', managedTextStyle(label.getAttribute('style') || '', STRUCTURE_LABEL));
        }
        for (const labelBackground of svg.querySelectorAll('.edgeLabel rect, .edgeLabel background')) {
          labelBackground.setAttribute('style', `${labelBackground.getAttribute('style') || ''};fill:#FFFFFF !important;opacity:0.96 !important`);
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
