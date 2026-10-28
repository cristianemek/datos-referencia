const fs = require('fs');
const { optimize } = require('svgo');

const [input, output, variant = 'minimal'] = process.argv.slice(2);

if (!input || !output) {
  process.stderr.write('Uso: node optimize-keepdims.js <entrada.svg> <salida.svg> [minimal|lossless|lossless-paths]\n');
  process.exit(1);
}

const minimal = [
  'removeDoctype', 'removeXMLProcInst', 'removeComments', 'removeMetadata', 'removeEditorsNSData',
  { name: 'cleanupNumericValues', params: { floatPrecision: 10 } },
  'removeScripts',
];
const lossless = [...minimal, 'cleanupIds', 'convertStyleToAttrs', 'removeUnknownsAndDefaults', 'removeUselessDefs', 'cleanupAttrs'];
const losslessPaths = [
  ...lossless,
  {
    name: 'convertPathData',
    params: {
      floatPrecision: 8, transformPrecision: 10, applyTransforms: false, applyTransformsStroked: false,
      makeArcs: false, straightCurves: false, convertToQ: false, lineShorthands: true, convertToZ: false,
      curveSmoothShorthands: false, removeUseless: false, collapseRepeated: false, forceAbsolutePath: false,
    },
  },
];
const presets = { minimal, lossless, 'lossless-paths': losslessPaths };

function ensureViewBox(svg) {
  const root = svg.match(/^<svg\b[^>]*>/)[0];
  if (/\sviewBox=/.test(root)) {
    return svg;
  }
  const width = root.match(/\swidth="([\d.]+)"/);
  const height = root.match(/\sheight="([\d.]+)"/);
  if (!width || !height) {
    throw new Error('el SVG no tiene viewBox ni width/height numéricos');
  }
  return svg.replace(/^<svg/, `<svg viewBox="0 0 ${width[1]} ${height[1]}"`);
}

try {
  if (!presets[variant]) {
    throw new Error(`variante desconocida: ${variant}`);
  }
  const { data } = optimize(fs.readFileSync(input, 'utf8'), { plugins: presets[variant], js2svg: { pretty: false } });
  const oneLine = ensureViewBox(data.replace(/[\r\n]+/g, ' '));
  const rootTag = oneLine.match(/^<svg\b[^>]*>/)[0];
  const singleLine = /\sxmlns=/.test(rootTag) ? oneLine : oneLine.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');
  fs.writeFileSync(output, singleLine);
} catch (error) {
  process.stderr.write(`No se pudo optimizar ${input}: ${error.message}\n`);
  process.exit(1);
}
