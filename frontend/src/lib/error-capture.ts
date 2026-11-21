// Explanatory banner: Captures original Error out-of-band so server.ts can recover stack traces
// Captures the original Error out-of-band so server.ts can recover the stack
// when h3 has already swallowed the throw into a generic 500 Response.

// Variable storing the most recent captured error object and timestamp
let lastCapturedError: { error: unknown; at: number } | undefined;
// Constant defining time-to-live in milliseconds (5 seconds) for error retention
const TTL_MS = 5_000;

// Internal helper function to record a captured error with current timestamp
function record(error: unknown) {
  // Store error reference and record invocation timestamp
  lastCapturedError = { error, at: Date.now() };
}

// Commentary on h3 HTTPError serialization behavior and cause-chain preservation
// h3's HTTPError serializes to {"status":500,"unhandled":true,"message":"HTTPError"} —
// no stack, no cause — so a plain console.error(error) reaches the log pipeline with
// the failure detail stripped. Expand Error-like args into a string that keeps the
// message, stack, and the full cause chain.
// Constant defining the maximum recursion depth for unwrapping nested error causes
const CAUSE_DEPTH_LIMIT = 5;
// Constant limiting the maximum string length of the resulting error description
const DESCRIPTION_LENGTH_LIMIT = 8_000;

// Export function to produce a formatted multiline string description of an error and its causes
export function describeError(error: unknown): string {
  // Initialize array to hold individual error cause string segments
  const parts: string[] = [];
  // Initialize current pointer to the root error
  let current: unknown = error;
  // Loop through error cause chain up to maximum limit
  for (let depth = 0; depth < CAUSE_DEPTH_LIMIT && current != null; depth++) {
    // Check if the current object in chain is not an Error instance
    if (!(current instanceof Error)) {
      // Append string directly or safely stringify object
      parts.push(typeof current === "string" ? current : safeStringify(current));
      // Break out of cause loop
      break;
    }
    // Set prefix label indicating whether this is the root or a nested cause
    const label = depth === 0 ? "" : "caused by: ";
    // Extract formatted HTTP status string if present on error
    const status = describeStatus(current);
    // Append formatted stack trace or error message and status
    parts.push(`${label}${current.stack ?? `${current.name}: ${current.message}`}${status}`);
    // Advance pointer to inner cause property
    current = current.cause;
  }
  // Join all parts with newlines and truncate to character limit
  return parts.join("\n").slice(0, DESCRIPTION_LENGTH_LIMIT);
}

// Helper function to extract and format HTTP status codes from error objects
function describeStatus(error: Error): string {
  // Cast error to record containing optional status or statusCode properties
  const { status, statusCode } = error as { status?: unknown; statusCode?: unknown };
  // Resolve value from status or statusCode
  const value = status ?? statusCode;
  // Return formatted status string if value is numeric, otherwise empty string
  return typeof value === "number" ? ` (status ${value})` : "";
}

// Helper function to safely stringify objects without throwing JSON circular reference errors
function safeStringify(value: unknown): string {
  // Begin try block to serialize JSON
  try {
    // Return serialized JSON string or fallback to String conversion
    return JSON.stringify(value) ?? String(value);
    // Catch serialization errors
  } catch {
    // Return string representation on error
    return String(value);
  }
}

// Type guard function checking if value is an instance of Error
function isErrorLike(value: unknown): value is Error {
  // Evaluate instanceof Error check
  return value instanceof Error;
}

// Explanatory comment: Wrap console.error to intercept unhandled errors
// Wrap console.error so errors logged by any layer — including h3's internal
// unhandled-error logging, which this file cannot hook directly — are both
// recorded for consumeLastCapturedError and expanded before serialization.
// Keep original console.error reference bound to console
const originalConsoleError = console.error.bind(console);
// Monkey-patch console.error to capture and expand errors
console.error = (...args: unknown[]) => {
  // Map over arguments expanding any error-like objects
  const expanded = args.map((arg) => {
    // Return argument as-is if not an Error
    if (!isErrorLike(arg)) return arg;
    // Record error for subsequent out-of-band retrieval
    record(arg);
    // Return formatted multiline error description
    return describeError(arg);
  });
  // Call original console.error with expanded arguments
  originalConsoleError(...expanded);
};

// Check if running in a runtime supporting global event listeners (browser or Node.js with globalThis)
if (typeof globalThis.addEventListener === "function") {
  // Listen for uncaught error events and record them
  globalThis.addEventListener("error", (event) => record((event as ErrorEvent).error ?? event));
  // Listen for unhandled promise rejections and record their reasons
  globalThis.addEventListener("unhandledrejection", (event) =>
    // Record promise rejection reason
    record((event as PromiseRejectionEvent).reason),
  );
}

// Export function to consume and clear the last captured error within TTL
export function consumeLastCapturedError(): unknown {
  // Return undefined if no error has been captured
  if (!lastCapturedError) return undefined;
  // Check if captured error has expired past TTL limit
  if (Date.now() - lastCapturedError.at > TTL_MS) {
    // Clear expired error
    lastCapturedError = undefined;
    // Return undefined
    return undefined;
  }
  // Extract error object from captured container
  const { error } = lastCapturedError;
  // Clear captured error container
  lastCapturedError = undefined;
  // Return extracted error
  return error;
}
