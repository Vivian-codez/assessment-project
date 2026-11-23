// Import QueryClient and QueryClientProvider for server state caching
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
// Import router primitives and types from TanStack Router
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
  type ErrorComponentProps,
} from "@tanstack/react-router";
// Import React hooks, component class, and types
import React, { useState, useId, type ReactNode, type ErrorInfo } from "react";
// Import Lucide icons for diagnostic display and interaction
import { AlertCircle, ChevronDown, ChevronUp, Copy, Check, RefreshCw, Home } from "lucide-react";
// Import global application styles
import appCss from "../styles.css?url";

/**
 * NotFoundComponent renders a user-friendly 404 display when a requested route does not exist.
 *
 * @returns {JSX.Element} The rendered 404 error page.
 */
function NotFoundComponent() {
  // Render centered 404 container
  return (
    // Outer flex wrapper taking full viewport height
    <div className="flex min-h-screen items-center justify-center bg-background px-4">
      {/* Centered card content with maximum width constraint */}
      <div className="max-w-md text-center">
        {/* Large 404 status heading */}
        <h1 className="text-7xl font-bold text-foreground">404</h1>
        {/* Descriptive subtitle heading */}
        <h2 className="mt-4 text-xl font-semibold text-foreground">Page not found</h2>
        {/* User-facing explanation text */}
        <p className="mt-2 text-sm text-muted-foreground">
          The page you're looking for doesn't exist or has been moved.
        </p>
        {/* Navigation action container */}
        <div className="mt-6">
          {/* Link back to application root dashboard */}
          <Link
            to="/"
            className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Go home
          </Link>
        </div>
      </div>
    </div>
  );
}

/**
 * Properties for DiagnosticErrorView component.
 */
interface DiagnosticErrorViewProps {
  // Captured error object or primitive
  error: unknown;
  // Callback resetting the error state
  reset: () => void;
  // React component stack captured via componentDidCatch
  componentStack?: string | null;
}

/**
 * DiagnosticErrorView provides an authoritative diagnostic UI for uncaught route and render exceptions.
 * Includes unique error reference identifier, component stack trace, execution stack trace, clipboard copying, and safe recovery actions.
 *
 * @param {DiagnosticErrorViewProps} props - Properties containing error, reset callback, and optional componentStack.
 * @returns {JSX.Element} The rendered diagnostic error interface.
 */
function DiagnosticErrorView({ error, reset, componentStack }: DiagnosticErrorViewProps) {
  // Access router instance to inspect active location, failing route, and cache state
  const router = useRouter();
  // State tracking whether the technical diagnostic accordion is expanded
  const [showDetails, setShowDetails] = useState(false);
  // State tracking whether error diagnostic details were copied to clipboard
  const [copied, setCopied] = useState(false);
  // Generate a stable unique error reference ID for support tracking
  const errorId = useId();
  // Create formatted error reference code
  const errorRef = `ERR-${Date.now().toString(36).toUpperCase()}-${errorId
    .replace(/[^a-zA-Z0-9]/g, "")
    .slice(0, 4)
    .toUpperCase()}`;

  // Resolve failing route pathname from router state or window location
  const failingRoute =
    router.state?.location?.pathname ||
    (typeof window !== "undefined" ? window.location.pathname : "/");
  // Resolve complete URL for debugging
  const failingUrl =
    typeof window !== "undefined"
      ? window.location.href
      : router.state?.location?.href || "unknown";
  // Resolve failing matched component route identifier
  const failingRouteId =
    router.state?.matches?.[router.state.matches.length - 1]?.routeId || "UnknownRoute";
  // Extract error class name
  const errorName = (error as Error)?.name || "RuntimeError";
  // Extract error message
  const errorMessage = (error as Error)?.message || String(error);
  // Extract real execution stack trace or fallback
  const errorStack = (error as Error)?.stack || "No stack trace available";
  // Extract effective component stack from props or attached error metadata
  const effectiveComponentStack =
    componentStack ||
    (typeof error === "object" && error !== null && "componentStack" in error
      ? String((error as { componentStack?: unknown }).componentStack || "")
      : null);

  // Helper function to copy diagnostic bundle to system clipboard
  const handleCopyDiagnostics = async () => {
    // Construct structured diagnostic payload
    const diagnostics = {
      // Diagnostic reference identifier
      errorRef,
      // ISO timestamp of failure
      timestamp: new Date().toISOString(),
      // Failing route pathname
      failingRoute,
      // Failing matched route identifier
      failingRouteId,
      // Target full URL
      failingUrl,
      // Error type name
      errorName,
      // Error message text
      message: errorMessage,
      // Raw execution stack trace
      stack: errorStack,
      // React component stack trace captured via componentDidCatch
      componentStack: effectiveComponentStack || "No component stack available",
      // Client user agent string
      userAgent: typeof navigator !== "undefined" ? navigator.userAgent : "unknown",
    };
    // Attempt write to clipboard
    try {
      // Execute asynchronous write to clipboard
      await navigator.clipboard.writeText(JSON.stringify(diagnostics, null, 2));
      // Mark copied state as true
      setCopied(true);
      // Reset copied state after timeout
      setTimeout(() => setCopied(false), 3000);
    } catch (copyErr) {
      // Fallback console log if clipboard write fails
      console.warn("Failed to copy error diagnostics to clipboard:", copyErr);
    }
  };

  // Render diagnostic recovery interface
  return (
    // Outer flex wrapper taking full viewport height with subtle background
    <div className="flex min-h-screen items-center justify-center bg-background px-4 py-8">
      {/* Diagnostic container card with border and elevation */}
      <div className="w-full max-w-2xl rounded-2xl border border-destructive/20 bg-card p-6 shadow-xl sm:p-8">
        {/* Header section with error icon and reference code */}
        <div className="flex items-start gap-4">
          {/* Rounded alert icon container */}
          <div className="grid size-12 shrink-0 place-items-center rounded-xl bg-destructive/10 text-destructive">
            <AlertCircle className="size-6" />
          </div>
          {/* Title and reference details */}
          <div className="min-w-0 flex-1">
            {/* Primary error status heading */}
            <h1 className="font-display text-xl font-bold tracking-tight text-foreground sm:text-2xl">
              An Unexpected Exception Occurred
            </h1>
            {/* Display error reference identifier for support auditing */}
            <p className="mt-1 text-xs font-mono text-muted-foreground">
              Reference ID: <span className="font-semibold text-foreground">{errorRef}</span>
            </p>
          </div>
        </div>

        {/* Concise explanation of the failure */}
        <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
          {errorMessage ||
            "A runtime execution error prevented this view from loading completely. Your data is protected."}
        </p>

        {/* Collapsible diagnostic details accordion */}
        <div className="mt-4 overflow-hidden rounded-xl border border-line bg-muted/30">
          {/* Accordion toggle button */}
          <button
            type="button"
            onClick={() => setShowDetails(!showDetails)}
            className="flex w-full items-center justify-between px-4 py-2.5 text-xs font-medium text-foreground transition-colors hover:bg-muted/50"
          >
            <span>Technical Diagnostic Details</span>
            {showDetails ? (
              <ChevronUp className="size-4 text-muted-foreground" />
            ) : (
              <ChevronDown className="size-4 text-muted-foreground" />
            )}
          </button>
          {/* Expandable stack trace and diagnostic payload */}
          {showDetails && (
            <div className="border-t border-line p-4 space-y-3">
              {/* Diagnostic metadata breakdown grid */}
              <div className="grid grid-cols-2 gap-2 text-[11px] font-mono bg-muted/50 p-2.5 rounded-lg border border-line/60">
                {/* Failing route */}
                <div>
                  <span className="text-muted-foreground">Route: </span>
                  <span className="font-semibold text-foreground">{failingRoute}</span>
                </div>
                {/* Matched component / route ID */}
                <div>
                  <span className="text-muted-foreground">Component: </span>
                  <span className="font-semibold text-foreground">{failingRouteId}</span>
                </div>
                {/* Error class */}
                <div>
                  <span className="text-muted-foreground">Type: </span>
                  <span className="text-destructive font-semibold">{errorName}</span>
                </div>
                {/* Timestamp */}
                <div>
                  <span className="text-muted-foreground">Time: </span>
                  <span className="text-muted-foreground">{new Date().toLocaleTimeString()}</span>
                </div>
              </div>

              {/* Execution stack trace preformatted text box */}
              <div>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1">
                  Stack Trace & Source
                </p>
                <pre className="max-h-48 overflow-auto rounded-lg bg-black/90 p-3 font-mono text-[11px] leading-relaxed text-emerald-400 border border-emerald-950">
                  {errorStack}
                </pre>
              </div>

              {/* React component stack preformatted text box */}
              {effectiveComponentStack && (
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold mb-1">
                    React Component Stack
                  </p>
                  <pre className="max-h-48 overflow-auto rounded-lg bg-black/90 p-3 font-mono text-[11px] leading-relaxed text-amber-300 border border-amber-950">
                    {effectiveComponentStack}
                  </pre>
                </div>
              )}

              {/* Copy diagnostic details button */}
              <div className="mt-3 flex justify-end">
                <button
                  type="button"
                  onClick={handleCopyDiagnostics}
                  className="inline-flex items-center gap-1.5 rounded-md border border-line bg-card px-2.5 py-1 text-xs font-medium text-foreground transition-colors hover:bg-muted shadow-2xs"
                >
                  {copied ? (
                    <>
                      <Check className="size-3.5 text-emerald-500" />
                      <span>Copied to Clipboard!</span>
                    </>
                  ) : (
                    <>
                      <Copy className="size-3.5 text-muted-foreground" />
                      <span>Copy Diagnostic Details</span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Action recovery buttons */}
        <div className="mt-6 flex flex-wrap items-center justify-end gap-3 border-t border-line pt-4">
          {/* Safe view fallback redirect */}
          <a
            href="/"
            className="inline-flex items-center gap-1.5 rounded-lg border border-line bg-card px-4 py-2 text-xs font-medium text-foreground transition-colors hover:bg-muted"
          >
            <Home className="size-3.5 text-muted-foreground" />
            Reset to Safe View
          </a>
          {/* Retry current route invocation */}
          <button
            type="button"
            onClick={() => {
              // Invalidate router cache to force fresh data fetch
              router.invalidate();
              // Reset error boundary state
              reset();
            }}
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-4 py-2 text-xs font-semibold text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
          >
            <RefreshCw className="size-3.5" />
            Try Again
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * ErrorComponent adapter for TanStack Router route-level error boundaries.
 */
function ErrorComponent({ error, reset, ...rest }: ErrorComponentProps) {
  // Resolve component stack if provided in rest props or attached to error
  const restInfo = rest as { info?: { componentStack?: string } };
  const compStack =
    (typeof error === "object" && error !== null && "componentStack" in error
      ? String((error as { componentStack?: unknown }).componentStack || "")
      : null) ||
    restInfo?.info?.componentStack ||
    null;
  // Render authoritative diagnostic view
  return <DiagnosticErrorView error={error} reset={reset} componentStack={compStack} />;
}

/**
 * Props interface for GlobalErrorBoundary class component.
 */
interface GlobalErrorBoundaryProps {
  // Child node tree wrapped by the error boundary
  children: ReactNode;
}

/**
 * State interface for GlobalErrorBoundary class component.
 */
interface GlobalErrorBoundaryState {
  // Whether an unhandled rendering error was caught
  hasError: boolean;
  // The caught error object
  error: Error | null;
  // The React component stack trace from componentDidCatch
  componentStack: string | null;
}

/**
 * GlobalErrorBoundary provides a standard React class boundary that intercepts render exceptions
 * and captures componentDidCatch's errorInfo.componentStack for deep component tree diagnostics.
 */
class GlobalErrorBoundary extends React.Component<
  GlobalErrorBoundaryProps,
  GlobalErrorBoundaryState
> {
  // Initialize component with clean state
  constructor(props: GlobalErrorBoundaryProps) {
    // Invoke parent React.Component constructor
    super(props);
    // Initialize default error state
    this.state = { hasError: false, error: null, componentStack: null };
  }

  // Derive error state from thrown exception
  static getDerivedStateFromError(error: Error): Partial<GlobalErrorBoundaryState> {
    // Update state to trigger fallback UI
    return { hasError: true, error };
  }

  // Lifecycle hook capturing React error info and component stack
  override componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Record component stack in local component state
    this.setState({ componentStack: errorInfo.componentStack || null });
    // Attach component stack to error object for router catch boundaries
    if (typeof error === "object" && error !== null) {
      Object.assign(error, { componentStack: errorInfo.componentStack });
    }
    // Log exception and component hierarchy to browser console
    console.error("[GlobalErrorBoundary] Caught rendering exception:", error, errorInfo);
  }

  // Reset handler to clear caught exception
  handleReset = () => {
    // Reset state to initial clear state
    this.setState({ hasError: false, error: null, componentStack: null });
  };

  // Render method returning either diagnostic view or normal children
  override render() {
    // If an error was caught during rendering, display diagnostic view
    if (this.state.hasError && this.state.error) {
      // Return DiagnosticErrorView with captured component stack
      return (
        <DiagnosticErrorView
          error={this.state.error}
          reset={this.handleReset}
          componentStack={this.state.componentStack}
        />
      );
    }
    // Otherwise render children normally
    return this.props.children;
  }
}

// Define the root route with context for QueryClient
export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  // Configure document head metadata
  head: () => ({
    meta: [
      // Character encoding metadata
      { charSet: "utf-8" },
      // Responsive viewport metadata
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      // Application page title
      { title: "Verism AI — Teacher Review Console" },
      // Application SEO description
      { name: "description", content: "AI-assisted grading and similarity review for teachers." },
      // Application author metadata
      { name: "author", content: "Verism AI" },
      // Open Graph title
      { property: "og:title", content: "Verism AI — Teacher Review Console" },
      // Open Graph description
      {
        property: "og:description",
        content: "AI-assisted grading and similarity review for teachers.",
      },
      // Open Graph document type
      { property: "og:type", content: "website" },
      // Twitter card styling
      { name: "twitter:card", content: "summary_large_image" },
      // Theme color for mobile browser status bars
      {
        name: "theme-color",
        content: "#e8f6f8",
      },
    ],
    links: [
      // Primary CSS stylesheet link
      {
        rel: "stylesheet",
        href: appCss,
      },
      // Preconnect to Google Fonts domain
      { rel: "preconnect", href: "https://fonts.googleapis.com" },
      // Preconnect to Google Fonts static asset CDN
      { rel: "preconnect", href: "https://fonts.gstatic.com" },
      // Fraunces and Inter typography stylesheet
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,400;0,9..144,500;0,9..144,600;0,9..144,700;1,9..144,400&family=Inter:wght@400;500;600;700&display=swap",
      },
      // Application favicon icon link
      { rel: "icon", href: "/favicon.ico", type: "image/x-icon" },
    ],
  }),
  // Root HTML shell component
  shellComponent: RootShell,
  // Main route wrapper component
  component: RootComponent,
  // Component to render when route is not found
  notFoundComponent: NotFoundComponent,
  // Component to render on uncaught errors
  errorComponent: ErrorComponent,
});

/**
 * RootShell provides the outer HTML document structure with head and body.
 *
 * @param {Object} props - Shell properties containing child elements.
 * @returns {JSX.Element} The rendered HTML document shell.
 */
function RootShell({ children }: { children: ReactNode }) {
  // Render full HTML document
  return (
    // HTML root tag with English language designation
    <html lang="en">
      {/* HTML document head with injected meta tags and links */}
      <head>
        <HeadContent />
      </head>
      {/* HTML document body containing application markup */}
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

/**
 * RootComponent sets up the React Query client provider and renders child route outlets.
 *
 * @returns {JSX.Element} The application root component tree.
 */
function RootComponent() {
  // Retrieve QueryClient instance from TanStack Route context
  const { queryClient } = Route.useRouteContext();

  // Render QueryClientProvider wrapping child route Outlet within GlobalErrorBoundary
  return (
    <QueryClientProvider client={queryClient}>
      {/* GlobalErrorBoundary intercepts render exceptions and captures errorInfo.componentStack */}
      <GlobalErrorBoundary>
        {/* Nested routes render here via TanStack Router Outlet */}
        <Outlet />
      </GlobalErrorBoundary>
    </QueryClientProvider>
  );
}
