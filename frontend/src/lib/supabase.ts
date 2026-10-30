/**
 * ==============================================================================
 * Verism AI – Frontend Authentication & Supabase Client Stub
 *
 * In local Docker mode (default), delegates all authentication to the FastAPI
 * backend REST API (/api/v1/auth/*) using standard JWT Bearer tokens.
 *
 * If VITE_USE_SUPABASE=true, loads the real @supabase/supabase-js client
 * for cloud-synced deployments.
 * ==============================================================================
 */

// Evaluate the boolean flag indicating whether cloud Supabase is enabled
const _useSupabase =
  // Check if Vite environment variable is explicitly string "true"
  (import.meta.env as any).VITE_USE_SUPABASE === "true" ||
  // Or check if Vite environment variable is boolean true
  (import.meta.env as any).VITE_USE_SUPABASE === true;

// Resolve the target Supabase project URL from environment or fallback default
const _supabaseUrl: string =
  // Read VITE_SUPABASE_URL from environment variables
  (import.meta.env as any).VITE_SUPABASE_URL ||
  // Default fallback Supabase project URL
  "https://lzranjtbiucfaktbnjec.supabase.co";

// Resolve the target Supabase anon API key from environment or fallback default
const _supabaseAnonKey: string =
  // Read VITE_SUPABASE_ANON_KEY from environment variables
  (import.meta.env as any).VITE_SUPABASE_ANON_KEY ||
  // Default fallback anon JWT key
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx6cmFuanRiaXVjZmFrdGJuamVjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTIzNDAyMTMsImV4cCI6MjEwNzkxNjIxM30.TWBIc8-chcw7aI2LYX8NEiopKWMz9-wNB9oqTKe5q9s";

/** Exported boolean flag indicating whether the real Supabase client is active. */
export const useSupabase: boolean = _useSupabase;

// ---------------------------------------------------------------------------
// No-op stub used when USE_SUPABASE=false (Local Docker Mode)
// ---------------------------------------------------------------------------

// Constant representing an empty session object returned by the stub
const _noOpSession = { data: { session: null }, error: null };

// Stub auth object mimicking @supabase/supabase-js auth interface
const _noOpAuth = {
  // getSession method returns null session so app uses stored local JWT token
  getSession: async () => _noOpSession,
  // onAuthStateChange returns a dummy unsubscribe subscription function
  onAuthStateChange: (_cb: unknown) => ({
    // Inner data payload containing subscription controller
    data: { subscription: { unsubscribe: () => {} } },
  }),
  // signInWithPassword throws descriptive error pointing to local backend endpoint
  signInWithPassword: async () => {
    // Throw error to guide developers to /api/v1/auth/login
    throw new Error("Cloud auth is disabled. Use the backend /api/v1/auth/login endpoint.");
  },
  // signUp throws descriptive error pointing to local backend endpoint
  signUp: async () => {
    // Throw error to guide developers to /api/v1/auth/signup
    throw new Error("Cloud auth is disabled. Use the backend /api/v1/auth/signup endpoint.");
  },
  // signOut succeeds silently with null error
  signOut: async () => ({ error: null }),
};

// Client class providing proxy query builders for table calls
class _NoOpClient {
  // Attach the stubbed authentication interface
  auth = _noOpAuth;
  // Chainable table method returning a proxy query builder
  table(_name: string) {
    // Create a recursive JavaScript Proxy to absorb method chains (select, eq, order, etc.)
    const chain: any = new Proxy({}, {
      // Dynamic getter returning a function that returns the proxy chain
      get: (_target, _prop) => (..._args: unknown[]) => chain,
    });
    // Terminal execute method returning empty data array
    chain.execute = async () => ({ data: [], error: null });
    // Return proxy chain instance
    return chain;
  }
}

// ---------------------------------------------------------------------------
// Client Export Initialisation
// ---------------------------------------------------------------------------

// Declare variable to hold client instance
let _client: any;

// Check if cloud Supabase is requested via environment configuration
if (_useSupabase) {
    // Attempt dynamic import to avoid bundling supabase-js when not needed
    try {
      // Dynamically import createClient from @supabase/supabase-js package
      const { createClient } = await import("@supabase/supabase-js");
      // Instantiate real Supabase client with auto-refresh and session persistence
      _client = createClient(_supabaseUrl, _supabaseAnonKey, {
        // Configure authentication options
        auth: {
          // Persist user session to localStorage
          persistSession: true,
          // Automatically refresh expired session tokens
          autoRefreshToken: true,
          // Detect incoming OAuth or magic-link tokens in URL hash
          detectSessionInUrl: true,
        },
      });
    // Catch module resolution or network initialization errors
    } catch {
      // Log warning when SDK cannot be loaded
      console.warn("[supabase] @supabase/supabase-js not available – using no-op stub.");
      // Fallback to local no-op client stub
      _client = new _NoOpClient();
    }
// If USE_SUPABASE is false, instantiate the local no-op stub directly
} else {
    // Instantiate local no-op client stub
    _client = new _NoOpClient();
}

/** Exported Supabase client (active SDK or lightweight local stub). */
export const supabase = _client;
