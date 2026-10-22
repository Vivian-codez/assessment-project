import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { ShieldCheck, Mail, Lock, User, ArrowRight, Loader2, Sparkles, GraduationCap } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { api, setAuthToken, setCachedUser, getAuthToken } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export const Route = createFileRoute("/login")({
  component: LoginPage,
});

function LoginPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState("Instructor · Computer Science");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Check if already authenticated
  useEffect(() => {
    async function checkSession() {
      const { data } = await supabase.auth.getSession();
      if (data.session) {
        navigate({ to: "/" });
      }
    }
    checkSession();
  }, [navigate]);

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg("");
    setSuccessMsg("");

    const cleanEmail = email.trim().toLowerCase();
    try {
      // 1. Authenticate with Supabase Auth
      const { data, error } = await supabase.auth.signInWithPassword({
        email: cleanEmail,
        password: password,
      });

      if (error) {
        // Try fallback to backend API auth in case backend was used
        try {
          const apiRes = await api.auth.login({ email: cleanEmail, password });
          setAuthToken(apiRes.access_token);
          setCachedUser(apiRes.user);
          navigate({ to: "/" });
          return;
        } catch {
          throw new Error(error.message || "Invalid email or password.");
        }
      }

      if (data.session && data.user) {
        const token = data.session.access_token;
        setAuthToken(token);
        const meta = data.user.user_metadata || {};
        const profile = {
          id: data.user.id,
          name: meta.name || meta.full_name || cleanEmail.split("@")[0],
          email: data.user.email || cleanEmail,
          role: meta.role || "Instructor · Computer Science",
          preferences: meta.preferences || {},
        };
        setCachedUser(profile);
        navigate({ to: "/" });
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to sign in. Please verify your credentials.");
    } finally {
      setLoading(false);
    }
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg("");
    setSuccessMsg("");

    const cleanEmail = email.trim().toLowerCase();
    const cleanName = fullName.trim();

    if (!cleanName) {
      setErrorMsg("Please enter your full name.");
      setLoading(false);
      return;
    }

    try {
      const { data, error } = await supabase.auth.signUp({
        email: cleanEmail,
        password: password,
        options: {
          data: {
            name: cleanName,
            role: role,
          },
        },
      });

      if (error) {
        throw error;
      }

      // Also register on backend to ensure PostgreSQL sync
      try {
        await api.auth.signUp({
          email: cleanEmail,
          password: password,
          name: cleanName,
          role: role,
        });
      } catch (backendErr) {
        console.warn("Backend local sync notice:", backendErr);
      }

      if (data.session) {
        setAuthToken(data.session.access_token);
        setCachedUser({
          id: data.user!.id,
          name: cleanName,
          email: cleanEmail,
          role: role,
        });
        navigate({ to: "/" });
      } else {
        setSuccessMsg(
          "Account created successfully! If email confirmation is required, check your inbox, or sign in now."
        );
        setTab("signin");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Registration failed. Please try a different email.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-[#f7f8fa] p-4 text-[#1a1f2c]">
      {/* Background radial gradient accent */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 size-96 rounded-full bg-indigo-100/60 blur-3xl" />
        <div className="absolute -bottom-40 -right-40 size-96 rounded-full bg-emerald-100/60 blur-3xl" />
      </div>

      <div className="relative w-full max-w-md rounded-2xl border border-gray-200/80 bg-white/95 p-8 shadow-xl backdrop-blur-md">
        {/* Brand Header */}
        <div className="mb-6 flex flex-col items-center text-center">
          <div className="mb-3 flex size-12 items-center justify-center rounded-xl bg-[#1e293b] text-white shadow-md">
            <GraduationCap className="size-6 text-indigo-300" />
          </div>
          <h1 className="font-display text-2xl font-semibold tracking-tight text-gray-900">
            Verism AI Educator Console
          </h1>
          <p className="mt-1 text-xs text-gray-500">
            Sign in with your verified Supabase credentials to manage courses, rosters, and rubrics.
          </p>
        </div>

        {/* Tab switch */}
        <div className="mb-6 flex rounded-lg bg-gray-100 p-1">
          <button
            type="button"
            onClick={() => {
              setTab("signin");
              setErrorMsg("");
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
          <button
            type="button"
            onClick={() => {
              setTab("signup");
              setErrorMsg("");
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

        {/* Status Alerts */}
        {errorMsg && (
          <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
            {errorMsg}
          </div>
        )}
        {successMsg && (
          <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-700">
            {successMsg}
          </div>
        )}

        {/* Sign In Form */}
        {tab === "signin" ? (
          <form onSubmit={handleSignIn} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-700">Email Address</label>
              <div className="relative mt-1">
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

            <div>
              <div className="flex items-center justify-between">
                <label className="block text-xs font-medium text-gray-700">Password</label>
              </div>
              <div className="relative mt-1">
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
          /* Sign Up Form */
          <form onSubmit={handleSignUp} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-gray-700">Full Name</label>
              <div className="relative mt-1">
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

            <div>
              <label className="block text-xs font-medium text-gray-700">Work Email Address</label>
              <div className="relative mt-1">
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

            <div>
              <label className="block text-xs font-medium text-gray-700">Password</label>
              <div className="relative mt-1">
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

        <div className="mt-6 border-t border-gray-100 pt-4 text-center">
          <p className="flex items-center justify-center gap-1.5 text-[11px] text-gray-400">
            <ShieldCheck className="size-3.5 text-emerald-500" /> Protected by Supabase Auth with Row Level Security
          </p>
        </div>
      </div>
    </div>
  );
}
