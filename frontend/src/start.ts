// Import TanStack Start server bootstrap and middleware creation helpers
import { createStart, createCsrfMiddleware, createMiddleware } from "@tanstack/react-start";

// Import fallback error page renderer function
import { renderErrorPage } from "./lib/error-page";

// Create server middleware to catch uncaught server execution exceptions gracefully
const errorMiddleware = createMiddleware().server(async ({ next }) => {
  // Begin try block to forward request downstream
  try {
    // Await next middleware or route handler in chain
    return await next();
    // Catch any thrown exceptions
  } catch (error) {
    // Re-throw if error already represents a structured HTTP error with a status code
    if (error != null && typeof error === "object" && "statusCode" in error) {
      // Re-throw structured HTTP error
      throw error;
    }
    // Log unexpected runtime error to console
    console.error(error);
    // Return custom fallback 500 HTML response
    return new Response(renderErrorPage(), {
      // Set HTTP 500 Internal Server Error status
      status: 500,
      // Specify HTML content type header with UTF-8 charset
      headers: { "content-type": "text/html; charset=utf-8" },
    });
  }
});

// Start installs this automatically when src/start.ts is absent; defining the
// file opts out, so re-add it explicitly to keep server functions protected
// from cross-site requests.
// Instantiate CSRF middleware protecting server function endpoints
const csrfMiddleware = createCsrfMiddleware({
  // Filter only server function invocations for CSRF verification
  filter: (ctx) => ctx.handlerType === "serverFn",
});

// Export configured TanStack Start runtime instance with error and CSRF request middleware
export const startInstance = createStart(() => ({
  // Apply error catching and CSRF protection middleware to incoming requests
  requestMiddleware: [errorMiddleware, csrfMiddleware],
}));
