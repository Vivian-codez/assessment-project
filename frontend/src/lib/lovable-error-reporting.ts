// Module docstring explaining client-side error logging utility
/**
 * Verism AI – Local Diagnostic Error Logging Utility
 *
 * Captures uncaught route exceptions and React boundary errors for local
 * console diagnostics without sending telemetry to external third-party hosts.
 */

// Type definition for diagnostic error reporting configuration options
export type AppErrorOptions = {
  // Mechanism indicating how the error was trapped (manual, onerror, unhandledrejection, or React boundary)
  mechanism?: "manual" | "onerror" | "unhandledrejection" | "react_error_boundary";
  // Flag indicating whether the error was explicitly caught and handled
  handled?: boolean;
  // Severity level categorization for the error event
  severity?: "error" | "warning" | "info";
};

/**
 * Report caught runtime errors to local console diagnostics with context.
 *
 * @param {unknown} error - The caught error object or thrown primitive.
 * @param {Record<string, unknown>} [context={}] - Additional key-value metadata.
 * @param {AppErrorOptions} [options={}] - Reporting options.
 */
export function reportAppError(
  error: unknown,
  context: Record<string, unknown> = {},
  options: AppErrorOptions = {},
): void {
  // Guard against server-side execution where window is undefined
  if (typeof window === "undefined") return;

  // Derive human-readable error message handling Response objects, Errors, or primitive values
  const message =
    // Check if thrown error is an instance of HTTP Response
    error instanceof Response
      ? // Format response status and URL
        `Response ${error.status}${error.url ? ` at ${error.url}` : ""}`
      : // Check if error is standard JavaScript Error
        error instanceof Error
        ? // Use error message property
          error.message
        : // Convert unknown value to string
          String(error);

  // Extract stack trace if available on Error instance
  const stack = error instanceof Error ? error.stack : undefined;

  // Log structured diagnostic entry to local console for developer debugging
  console.error("[Verism Diagnostic Error]", {
    message,
    stack,
    context: {
      route: window.location.pathname,
      ...context,
    },
    mechanism: options.mechanism || "react_error_boundary",
    timestamp: new Date().toISOString(),
  });
}

/**
 * Backward compatibility alias for legacy imports.
 *
 * @param {unknown} error - Caught error object.
 * @param {Record<string, unknown>} [context] - Context metadata.
 */
export function reportLovableError(error: unknown, context?: Record<string, unknown>): void {
  // Forward to standard local diagnostic logger
  reportAppError(error, context);
}
