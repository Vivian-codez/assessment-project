/**
 * Standalone Fallback Error Page Generator.
 *
 * Produces an inline-styled, zero-dependency HTML document string for critical
 * bootstrapping or server-side rendering failures before React bundles initialize.
 *
 * @returns {string} Fully self-contained HTML document markup.
 */
// Export function to render a standalone fallback HTML error page string
export function renderErrorPage(): string {
  // Return complete responsive HTML template with inline styles, diagnostic branding, and user action buttons
  return `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Verism AI — Diagnostic Recovery</title>
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <style>
      body { font: 15px/1.5 system-ui, -apple-system, sans-serif; background: #fafafa; color: #111; display: grid; place-items: center; min-height: 100vh; margin: 0; padding: 1.5rem; }
      .card { max-width: 28rem; width: 100%; text-align: center; padding: 2.5rem; background: #ffffff; border: 1px solid #e5e7eb; border-radius: 1rem; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05); }
      .badge { display: inline-block; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: #b91c1c; background: #fef2f2; padding: 0.25rem 0.75rem; border-radius: 9999px; margin-bottom: 1rem; }
      h1 { font-size: 1.25rem; font-weight: 700; margin: 0 0 0.5rem; color: #111827; }
      p { color: #4b5563; font-size: 0.875rem; margin: 0 0 1.75rem; line-height: 1.6; }
      .actions { display: flex; gap: 0.75rem; justify-content: center; flex-wrap: wrap; }
      a, button { padding: 0.5rem 1.25rem; border-radius: 0.5rem; font-size: 0.875rem; font-weight: 600; cursor: pointer; text-decoration: none; border: 1px solid transparent; transition: all 0.15s ease; }
      .primary { background: #0f172a; color: #ffffff; }
      .primary:hover { background: #1e293b; }
      .secondary { background: #ffffff; color: #374151; border-color: #d1d5db; }
      .secondary:hover { background: #f9fafb; border-color: #9ca3af; }
    </style>
  </head>
  <body>
    <div class="card">
      <div class="badge">Diagnostic Recovery</div>
      <h1>Unable to initialize workspace</h1>
      <p>A network or runtime error prevented Verism AI from initializing. Your grading rubrics and encrypted records remain secure.</p>
      <div class="actions">
        <button class="primary" onclick="location.reload()">Reload Application</button>
        <a class="secondary" href="/">Return to Dashboard</a>
      </div>
    </div>
  </body>
</html>`;
}
