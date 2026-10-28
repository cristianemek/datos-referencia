const fs = require('fs');
const { optimize } = require('svgo');

const [input, output, variant = 'safe'] = process.argv.slice(2);

if (!input || !output) {
  process.stderr.write('Uso: node optimize-symbol.js <entrada.svg> <salida.svg> [safe|safe-styles|minimal|lossless|lossless-paths]\n');
  process.exit(1);
}

const PRECISION = 5;

try {
  const minimal = {
    plugins: [
      'removeDoctype', 'removeXMLProcInst', 'removeComments', 'removeMetadata', 'removeEditorsNSData',
      { name: 'cleanupNumericValues', params: { floatPrecision: 10 } },
      'removeDimensions', 'removeScripts',
    ],
    js2svg: { pretty: false },
  };
  const lossless = {
    plugins: [
      ...minimal.plugins,
      'cleanupIds',
      'convertStyleToAttrs',
      'removeUnknownsAndDefaults',
      'removeUselessDefs',
      'cleanupAttrs',
    ],
    js2svg: { pretty: false },
  };
  const losslessPaths = {
    plugins: [
      ...lossless.plugins,
      {
        name: 'convertPathData',
        params: {
          floatPrecision: 8, transformPrecision: 10, applyTransforms: false, applyTransformsStroked: false,
          makeArcs: false, straightCurves: false, convertToQ: false, lineShorthands: true, convertToZ: false,
          curveSmoothShorthands: false, removeUseless: false, collapseRepeated: false, forceAbsolutePath: false,
        },
      },
    ],
    js2svg: { pretty: false },
  };
  const presets = { minimal, lossless, 'lossless-paths': losslessPaths };
  const { data } = optimize(fs.readFileSync(input, 'utf8'), presets[variant] || {
    multipass: true,
    floatPrecision: PRECISION,
    plugins: [
      ...(variant === 'safe-styles' ? ['convertStyleToAttrs'] : []),
      {
        name: 'preset-default',
        params: {
          overrides: {
            mergePaths: false,
            convertShapeToPath: false,
            collapseGroups: false,
            convertPathData: { floatPrecision: PRECISION, transformPrecision: 7 },
            convertTransform: { floatPrecision: PRECISION, transformPrecision: 7 },
            cleanupNumericValues: { floatPrecision: PRECISION },
          },
        },
      },
      'removeDimensions',
      'removeXMLNS',
      'removeScripts',
    ],
    js2svg: { pretty: false },
  });

  const oneLine = data.replace(/[\r\n]+/g, ' ');
  const rootTag = oneLine.match(/^<svg\b[^>]*>/)[0];
  const singleLine = /\sxmlns=/.test(rootTag) ? oneLine : oneLine.replace(/^<svg/, '<svg xmlns="http://www.w3.org/2000/svg"');

  if (!/viewBox=/.test(singleLine)) {
    throw new Error('el SVG no tiene viewBox');
  }

  fs.writeFileSync(output, singleLine);
} catch (error) {
  process.stderr.write(`No se pudo optimizar ${input}: ${error.message}\n`);
  process.exit(1);
}
