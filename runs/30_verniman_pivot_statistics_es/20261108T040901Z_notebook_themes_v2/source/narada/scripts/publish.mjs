import { publishReport } from './lib/publication.mjs';

const args = process.argv.slice(2);
const options = {};
try {
  for (let i = 0; i < args.length; i++) {
    const arg = args[i];
    if (arg === '--dry-run') {
      options.dryRun = true;
    } else if (arg === '--report' || arg === '--output') {
      if (!args[i + 1] || args[i + 1].startsWith('--')) {
        throw new Error(`${arg} requires a path.`);
      }
      const key = arg === '--report' ? 'reportPath' : 'outputRoot';
      if (options[key]) throw new Error(`Duplicate option: ${arg}`);
      options[key] = args[++i];
    } else {
      throw new Error(`Unknown option: ${arg}`);
    }
  }
  if (!options.reportPath) {
    throw new Error('Usage: node scripts/publish.mjs --report PATH [--output PATH] [--dry-run]');
  }
  console.log(JSON.stringify(await publishReport(options)));
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
}
