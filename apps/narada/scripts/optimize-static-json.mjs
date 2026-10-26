import { compactStaticPublicationJson, verifyStaticPublicationJson } from './lib/static-json-delivery.mjs';

const options = {};
let verify = false;
try {
  const args = process.argv.slice(2);
  for (let i = 0; i < args.length; i++) {
    const flag = args[i];
    if (flag === '--verify') {
      if (verify) throw new Error('Duplicate option: --verify');
      verify = true;
    } else if (flag === '--canonical-root' || flag === '--export-root') {
      const key = flag === '--canonical-root' ? 'canonicalRoot' : 'exportRoot';
      if (options[key]) throw new Error(`Duplicate option: ${flag}`);
      if (!args[i + 1] || args[i + 1].startsWith('--')) throw new Error(`${flag} requires a path.`);
      options[key] = args[++i];
    } else {
      throw new Error(`Unknown option: ${flag}`);
    }
  }
  const receipt = await (verify ? verifyStaticPublicationJson : compactStaticPublicationJson)(options);
  const summary = { ...receipt };
  delete summary.files;
  console.log(JSON.stringify(summary));
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
