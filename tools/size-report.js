const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

async function report(filePath) {
  if (!fs.existsSync(filePath)) {
    console.error('File not found:', filePath);
    process.exit(2);
  }

  const buf = fs.readFileSync(filePath);
  const original = buf.length;

  const gz = zlib.gzipSync(buf).length;
  // Node's brotli is available in zlib BrotliCompress
  let br = 0;
  if (zlib.brotliCompressSync) {
    try {
      br = zlib.brotliCompressSync(buf).length;
    } catch (e) {
      // Brotli compression may throw on very old Node builds; fallback
      br = 0;
    }
  }

  function kb(n) { return (n/1024).toFixed(2) + ' KB'; }

  console.log('Size report for:', path.relative(process.cwd(), filePath));
  console.log('  Original :', kb(original));
  console.log('  Gzip     :', gz ? kb(gz) : 'n/a');
  console.log('  Brotli   :', br ? kb(br) : 'n/a');
}

const arg = process.argv[2] || './rmk-theme/assets/css/tailwind.css';
report(arg).catch(err => { console.error(err); process.exit(1); });
