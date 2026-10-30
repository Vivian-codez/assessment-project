/**
 * ==============================================================================
 * Verism AI – Educator Authentication Page (Sign In & Account Registration)
 *
 * Implements local JWT authentication via FastAPI backend (/api/v1/auth/login
 * and /api/v1/auth/signup). Automatically redirects authenticated educators
 * with active JWT tokens to the main dashboard.
 * ==============================================================================
 */

// Import TanStack Router file-route creator and programmatic navigation hook
import { createFileRoute, useNavigate } from "@tanstack/react-router";
// Import React component state and effect hooks
import { useState, useEffect } from "react";
// Import Lucide icons for visual affordances in form fields and buttons
import { ShieldCheck, Mail, Lock, User, ArrowRight, Loader2, Sparkles, GraduationCap } from "lucide-react";
// Import API client functions and authentication token storage utilities
import { api, setAuthToken, setCachedUser, getAuthToken } from "@/lib/api";
// Import shared UI Button component
import { Button } from "@/components/ui/button";
// Import shared UI Input component
import { Input } from "@/components/ui/input";

// Register this file as the route handler for path '/login'
export const Route = createFileRoute("/login")({
  // Associate LoginPage as the root rendering component for this route
  component: LoginPage,
});

// Component implementing educator authentication forms
function LoginPage() {
  // Hook providing programmatic page routing
  const navigate = useNavigate();
  // State toggling between sign-in mode and account registration mode
  const [tab, setTab] = useState<"signin" | "signup">("signin");
  // Form input state for user email address
  const [email, setEmail] = useState("");
  // Form input state for user password
  const [password, setPassword] = useState("");
  // Form input state for user full name (used on registration)
  const [fullName, setFullName] = useState("");
  // Form input state for academic role/department
  const [role, setRole] = useState("Instructor · Computer Science");
  // Loading flag tracking asynchronous network submission
  const [loading, setLoading] = useState(false);
  // Error alert message text displayed on authentication failure
  const [errorMsg, setErrorMsg] = useState("");
  // Success alert message text displayed on completion
  const [successMsg, setSuccessMsg] = useState("");

  // Effect verifying whether an active local JWT token already exists in browser storage
  useEffect(() => {
    // If a valid JWT token is stored, navigate immediately to the dashboard
    if (getAuthToken()) {
      // Redirect to home dashboard
      navigate({ to: "/" });
    }
  // Run on mount or when navigate hook reference changes
  }, [navigate]);

  // Handler processing sign-in form submissions
  const handleSignIn = async (e: React.FormEvent) => {
    // Prevent default browser form submission refresh
    e.preventDefault();
    // Enable loading state spinner
    setLoading(true);
    // Clear previous error messages
    setErrorMsg("");
    // Clear previous success messages
    setSuccessMsg("");

    // Trim and lower-case the input email address
    const cleanEmail = email.trim().toLowerCase();
    // Attempt authentication via backend REST API
    try {
      // Call backend /api/v1/auth/login endpoint with credentials
      const apiRes = await api.auth.login({ email: cleanEmail, password });
      // Persist the issued JWT bearer token to localStorage
      setAuthToken(apiRes.access_token);
      // Persist the user profile object to localStorage cache
      setCachedUser(apiRes.user);
      // Navigate authenticated educator to the dashboard root
      navigate({ to: "/" });
    // Catch invalid credentials or server errors
    } catch (err: any) {
      // Display error message to user
      setErrorMsg(err.message || "Failed to sign in. Please verify your credentials.");
    // Reset loading state once network call concludes
    } finally {
      // Disable loading spinner
      setLoading(false);
    }
  };

  // Handler processing new account registration form submissions
  const handleSignUp = async (e: React.FormEvent) => {
    // Prevent default browser form submission refresh
    e.preventDefault();
    // Enable loading state spinner
    setLoading(true);
    // Clear previous error messages
    setErrorMsg("");
    // Clear previous success messages
    setSuccessMsg("");

    // Trim and lower-case the input email address
    const cleanEmail = email.trim().toLowerCase();
    // Trim input educator full name
    const cleanName = fullName.trim();

    // Validate that full name is provided
    if (!cleanName) {
      // Set validation error message
      setErrorMsg("Please enter your full name.");
      // Disable loading spinner
      setLoading(false);
      // Terminate submission
      return;
    }

    // Attempt account registration via backend REST API
    try {
      // Call backend /api/v1/auth/signup endpoint with user details
      const apiRes = await api.auth.signUp({
        // Sanitized email
        email: cleanEmail,
        // Plaintext password for server-side bcrypt hashing
        password: password,
        // Educator full display name
        name: cleanName,
        // Academic department role
        role: role,
      });
      // Store returned access token in localStorage
      setAuthToken(apiRes.access_token);
      // Store user profile object in localStorage cache
      setCachedUser(apiRes.user);
      // Navigate newly registered educator to dashboard root
      navigate({ to: "/" });
    // Catch existing email conflict or server errors
    } catch (err: any) {
      // Display registration error message
      setErrorMsg(err.message || "Registration failed. Please try a different email.");
    // Conclude loading indicator
    } finally {
      // Disable loading spinner
      setLoading(false);
    }
  };

  // Render authentication page layout
  return (
    // Outer centered page wrapper with full viewport height
    <div className="relative flex min-h-screen items-center justify-center bg-[#f7f8fa] p-4 text-[#1a1f2c]">
      {/* Decorative background radial gradient glows */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        {/* Top-left soft indigo ambient blur blob */}
        <div className="absolute -top-40 -left-40 size-96 rounded-full bg-indigo-100/60 blur-3xl" />
        {/* Bottom-right soft emerald ambient blur blob */}
        <div className="absolute -bottom-40 -right-40 size-96 rounded-full bg-emerald-100/60 blur-3xl" />
      </div>

      {/* Glassmorphic card container hosting authentication forms */}
      <div className="relative w-full max-w-md rounded-2xl border border-gray-200/80 bg-white/95 p-8 shadow-xl backdrop-blur-md">
        {/* Brand header displaying icon, console title, and subhead */}
        <div className="mb-6 flex flex-col items-center text-center">
          {/* Circular badge container for brand icon */}
          <div className="mb-3 flex size-12 items-center justify-center rounded-xl bg-[#1e293b] text-white shadow-md">
            {/* GraduationCap icon representing education and grading console */}
            <GraduationCap className="size-6 text-indigo-300" />
          </div>
          {/* Main heading typography */}
          <h1 className="font-display text-2xl font-semibold tracking-tight text-gray-900">
            Verism AI Educator Console
          </h1>
          {/* Informational subhead subtitle */}
          <p className="mt-1 text-xs text-gray-500">
            Sign in with your verified credentials to manage classrooms, rosters, and rubrics.
          </p>
        </div>

        {/* Tab switch control allowing users to alternate between Sign In and Sign Up */}
        <div className="mb-6 flex rounded-lg bg-gray-100 p-1">
          {/* Tab button for Sign In mode */}
          <button
            type="button"
            onClick={() => {
              // Activate signin form tab
              setTab("signin");
              // Clear error feedback
              setErrorMsg("");
              // Clear success feedback
              setSuccessMsg("");
            }}
            className={`flex-1 rounded-md py-2 text-xs font-semibold transition-all ${
              tab === "signin"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-900"
            }`}
          >
            Sign In
          </button>
          {/* Tab button for Create Account mode */}
          <button
            type="button"
            onClick={() => {
              // Activate signup form tab
              setTab("signup");
              // Clear error feedback
              setErrorMsg("");
              // Clear success feedback
              setSuccessMsg("");
            }}
            className={`flex-1 rounded-md py-2 text-xs font-semibold transition-all ${
              tab === "signup"
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-500 hover:text-gray-900"
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Error message alert box displayed when errorMsg is non-empty */}
        {errorMsg && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
            {errorMsg}
          </div>
        )}
        {/* Success message alert box displayed when successMsg is non-empty */}
        {successMsg && (
          <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-700">
            {successMsg}
          </div>
        )}

        {/* Conditional rendering: Sign In form displayed when active tab is 'signin' */}
        {tab === "signin" ? (
          <form onSubmit={handleSignIn} className="space-y-4">
            {/* Email address input field group */}
            <div>
              <label className="block text-xs font-medium text-gray-700">Email Address</label>
              <div className="relative mt-1">
                {/* Mail envelope icon placed inside the input box */}
                <Mail className="absolute top-2.5 left-3 size-4 text-gray-400" />
                <Input
                  type="email"
                  required
                  placeholder="instructor@university.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-9 text-sm"
                />
              </div>
            </div>

            {/* Password input field group */}
            <div>
              <div className="flex items-center justify-between">
                <label className="block text-xs font-medium text-gray-700">Password</label>
              </div>
              <div className="relative mt-1">
                {/* Padlock icon placed inside the input box */}
                <Lock className="absolute top-2.5 left-3 size-4 text-gray-400" />
                <Input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9 text-sm"
                />
              </div>
            </div>

            {/* Submit button for sign in */}
            <Button
              type="submit"
              disabled={loading}
              className="mt-2 w-full bg-[#1e293b] py-2.5 text-xs font-medium text-white hover:bg-[#0f172a]"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="size-4 animate-spin" /> Verifying Credentials...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  Sign In to Dashboard <ArrowRight className="size-4" />
                </span>
              )}
            </Button>
          </form>
        ) : (
          /* Sign Up form displayed when active tab is 'signup' */
          <form onSubmit={handleSignUp} className="space-y-4">
            {/* Full legal name input field group */}
            <div>
              <label className="block text-xs font-medium text-gray-700">Full Name</label>
              <div className="relative mt-1">
                {/* User avatar icon placed inside the input box */}
                <User className="absolute top-2.5 left-3 size-4 text-gray-400" />
                <Input
                  type="text"
                  required
                  placeholder="Prof. Jane Doe"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="pl-9 text-sm"
                />
              </div>
            </div>

            {/* Academic Department & Faculty Role input field group */}
            <div>
              <label className="block text-xs font-medium text-gray-700">Department / Role</label>
              <Input
                type="text"
                placeholder="e.g. Computer Science · Faculty"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="mt-1 text-sm"
              />
            </div>

            {/* Email address input field group */}
            <div>
              <label className="block text-xs font-medium text-gray-700">Work Email Address</label>
              <div className="relative mt-1">
                {/* Mail envelope icon placed inside the input box */}
                <Mail className="absolute top-2.5 left-3 size-4 text-gray-400" />
                <Input
                  type="email"
                  required
                  placeholder="instructor@university.edu"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-9 text-sm"
                />
              </div>
            </div>

            {/* Password input field group */}
            <div>
              <label className="block text-xs font-medium text-gray-700">Password</label>
              <div className="relative mt-1">
                {/* Padlock icon placed inside the input box */}
                <Lock className="absolute top-2.5 left-3 size-4 text-gray-400" />
                <Input
                  type="password"
                  required
                  placeholder="Minimum 6 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-9 text-sm"
                />
              </div>
            </div>

            {/* Submit button for account creation */}
            <Button
              type="submit"
              disabled={loading}
              className="mt-2 w-full bg-[#1e293b] py-2.5 text-xs font-medium text-white hover:bg-[#0f172a]"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="size-4 animate-spin" /> Creating Account...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  Create Verified Account <ArrowRight className="size-4" />
                </span>
              )}
            </Button>
          </form>
        )}

        {/* Security and compliance footer banner */}
        <div className="mt-6 border-t border-gray-100 pt-4 text-center">
          <p className="flex items-center justify-center gap-1.5 text-[11px] text-gray-400">
            <ShieldCheck className="size-3.5 text-emerald-500" /> Protected by Local JWT Authentication & FERPA Encryption
          </p>
        </div>
      </div>
    </div>
  );
}
