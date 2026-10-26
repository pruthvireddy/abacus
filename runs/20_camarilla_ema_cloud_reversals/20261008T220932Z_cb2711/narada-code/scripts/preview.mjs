import { createServer } from 'node:http';
import { readFile, realpath, stat } from 'node:fs/promises';
import { extname, resolve, sep } from 'node:path';

// Preview only the exported website, never the surrounding research workspace.
const root = await realpath(resolve(import.meta.dirname, '../out'));
const port = Number(process.env.PORT ?? 4173);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('PORT must be a valid TCP port.');
const mediaTypes = {
  '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8', '.json': 'application/json; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp',
  '.ico': 'image/x-icon', '.woff2': 'font/woff2',
  '.csv': 'text/csv; charset=utf-8',
};
createServer(async (request, response) => {
  if (!['GET', 'HEAD'].includes(request.method)) {
    response.writeHead(405, { Allow: 'GET, HEAD' }).end();
    return;
  }
  try {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    if (pathname.includes('\\') || pathname.split('/').some((segment) => segment.startsWith('.'))) {
      response.writeHead(400).end('Invalid path');
      return;
    }
    let target = resolve(root, `.${pathname}`);
    if ((await stat(target)).isDirectory()) target = resolve(target, 'index.html');
    target = await realpath(target);
    if (!target.startsWith(root + sep)) throw new Error('Outside export');
    const body = await readFile(target);
    const headers = { 'Content-Type': mediaTypes[extname(target)] ?? 'application/octet-stream', 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' };
    if (extname(target) === '.csv') headers['Content-Disposition'] = `attachment; filename="${target.split(sep).at(-1)}"`;
    response.writeHead(200, headers);
    response.end(request.method === 'HEAD' ? undefined : body);
  } catch {
    response.writeHead(404, { 'Content-Type': 'text/html; charset=utf-8' });
    const fallback = await readFile(resolve(root, '404.html')).catch(() => Buffer.from('Page not found'));
    response.end(request.method === 'HEAD' ? undefined : fallback);
  }
}).listen(port, '127.0.0.1', () => console.log(`Narada preview: http://127.0.0.1:${port}`));
