const fs = require('fs');
const { Resvg } = require('@resvg/resvg-js');

const [input, output, width = '600', background = 'white'] = process.argv.slice(2);

if (!input || !output) {
  process.stderr.write('Uso: node render.js <entrada.svg> <salida.png> [ancho] [fondo]\n');
  process.exit(1);
}

try {
  const resvg = new Resvg(fs.readFileSync(input), {
    background,
    fitTo: { mode: 'width', value: Number(width) },
    font: { loadSystemFonts: true },
  });
  fs.writeFileSync(output, resvg.render().asPng());
} catch (error) {
  process.stderr.write(`No se pudo renderizar ${input}: ${error.message}\n`);
  process.exit(1);
}
