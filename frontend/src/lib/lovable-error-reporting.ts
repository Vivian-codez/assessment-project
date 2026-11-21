// Type definition for telemetry error reporting configuration options
type LovableErrorOptions = {
  // Mechanism indicating how the error was trapped (manual, onerror, unhandledrejection, or React boundary)
  mechanism?: "manual" | "onerror" | "unhandledrejection" | "react_error_boundary";
  // Flag indicating whether the error was explicitly caught and handled
  handled?: boolean;
  // Severity level categorization for the error event
  severity?: "error" | "warning" | "info";
};

// Type definition for external runtime telemetry tracking hooks
type LovableEvents = {
  // Method to record generic analytics events with arbitrary properties
  track?: (event: string, properties?: Record<string, unknown>) => string | null;
  // Method to record and dispatch caught runtime exceptions
  captureException?: (
    // Error object or unknown caught value
    error: unknown,
    // Optional contextual metadata dictionary
    context?: Record<string, unknown>,
    // Optional telemetry configuration options
    options?: LovableErrorOptions,
  ) => void;
};

// Augment the global Window interface to declare external telemetry properties
declare global {
  // Global Window extension
  interface Window {
    // Optional reference to telemetry tracking client instance
    __lovableEvents?: LovableEvents;
    // Optional reporting callback hook for editor preview runtime errors
    __lovableReportRuntimeError?: (payload: {
      // Error message string
      message: string;
      // Optional stack trace string
      stack?: string;
      // Optional file or route name string
      filename?: string;
    }) => void;
  }
}

// Export function to report runtime errors to external telemetry and editor overlay
export function reportLovableError(error: unknown, context: Record<string, unknown> = {}) {
  // Guard against server-side execution where window is undefined
  if (typeof window === "undefined") return;
  // Forward caught exception to __lovableEvents client if registered
  window.__lovableEvents?.captureException?.(
    // Pass caught error object
    error,
    // Pass context metadata including route path
    {
      // Source identifier indicating React boundary trap
      source: "react_error_boundary",
      // Current browser route path
      route: window.location.pathname,
      // Spread additional custom context properties
      ...context,
    },
    // Pass telemetry options
    {
      // Specify React error boundary mechanism
      mechanism: "react_error_boundary",
      // Flag as unhandled application failure
      handled: false,
      // Categorize as high severity error
      severity: "error",
    },
  );
  // Prod React does not rethrow boundary-caught errors to window.onerror, so the
  // editor's telemetry never sees them. Forward to lovable.js's reporting hook,
  // which is present only inside the editor preview.
  // Loaders and server fns commonly throw a raw Response; String(it) is the
  // opaque "[object Response]", so pull out the status and URL instead.
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
  // Dispatch payload to editor runtime error reporter if present
  window.__lovableReportRuntimeError?.({
    // Pass derived error message
    message,
    // Conditionally include stack trace if defined
    ...(stack !== undefined && { stack }),
    // Pass current pathname as filename context
    filename: window.location.pathname,
  });
}
