// Import error-capture module to initialize out-of-band exception listeners
import "./lib/error-capture";

// Import error consumer helper to retrieve last trapped SSR error
import { consumeLastCapturedError } from "./lib/error-capture";
// Import HTML error page renderer function
import { renderErrorPage } from "./lib/error-page";

// Type definition for the server entrypoint fetch handler
type ServerEntry = {
  // Fetch method receiving Request, environment, and execution context
  fetch: (request: Request, env: unknown, ctx: unknown) => Promise<Response> | Response;
};

// Variable holding the lazily imported server entry promise
let serverEntryPromise: Promise<ServerEntry> | undefined;

// Function to resolve or dynamically import the TanStack Start server entrypoint
async function getServerEntry(): Promise<ServerEntry> {
  // Check if promise has not yet been initialized
  if (!serverEntryPromise) {
    // Dynamically import server entry module and unwrap default export
    serverEntryPromise = import("@tanstack/react-start/server-entry").then(
      // Extract default export or module object as ServerEntry
      (m) => (m.default ?? m) as ServerEntry,
    );
  }
  // Return resolved server entry promise
  return serverEntryPromise;
}

// h3 swallows in-handler throws into a normal 500 Response with body
// {"unhandled":true,"message":"HTTPError"} — try/catch alone never fires for those.
// Helper function to detect and normalize swallowed h3 internal 500 responses into user-facing HTML error pages
async function normalizeCatastrophicSsrResponse(response: Response): Promise<Response> {
  // If response status is less than 500, return original response immediately
  if (response.status < 500) return response;
  // Extract content-type response header
  const contentType = response.headers.get("content-type") ?? "";
  // If response is not JSON, return original response
  if (!contentType.includes("application/json")) return response;

  // Clone response and read text body to inspect payload
  const body = await response.clone().text();
  // Check if payload matches h3's swallowed generic HTTPError structure
  if (!isH3SwallowedErrorBody(body)) return response;

  // Log captured underlying error or generate explanatory Error instance
  console.error(consumeLastCapturedError() ?? new Error(`h3 swallowed SSR error: ${body}`));
  // Return human-friendly HTML fallback error page
  return new Response(renderErrorPage(), {
    // Set HTTP 500 status
    status: 500,
    // Set text/html UTF-8 content type
    headers: { "content-type": "text/html; charset=utf-8" },
  });
}

// Helper function to check if response JSON string matches h3 unhandled HTTPError pattern
function isH3SwallowedErrorBody(body: string): boolean {
  // Begin try block to parse JSON
  try {
    // Parse body as record with unhandled and message properties
    const payload = JSON.parse(body) as { unhandled?: unknown; message?: unknown };
    // Check if unhandled is true and message is HTTPError
    return payload.unhandled === true && payload.message === "HTTPError";
    // Catch JSON parsing errors
  } catch {
    // Return false if body is not valid JSON
    return false;
  }
}

// Export default server handler object with fetch method
export default {
  // Asynchronous request listener handler
  async fetch(request: Request, env: unknown, ctx: unknown) {
    // Begin try block to execute SSR fetch
    try {
      // Await resolution of the server entrypoint handler
      const handler = await getServerEntry();
      // Execute handler fetch with request, environment, and context
      const response = await handler.fetch(request, env, ctx);
      // Normalize catastrophic 500 responses and return final response
      return await normalizeCatastrophicSsrResponse(response);
      // Catch top-level execution errors
    } catch (error) {
      // Log caught server execution error
      console.error(error);
      // Return 500 response rendering fallback HTML error page
      return new Response(renderErrorPage(), {
        // Set HTTP 500 status
        status: 500,
        // Set text/html content-type header
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }
  },
};
