/**
 * Supabase client instance for frontend authentication and direct database operations.
 */
import { createClient } from "@supabase/supabase-js";

const supabaseUrl =
  (import.meta.env as any).VITE_SUPABASE_URL ||
  "https://lzranjtbiucfaktbnjec.supabase.co";

const supabaseAnonKey =
  (import.meta.env as any).VITE_SUPABASE_ANON_KEY ||
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx6cmFuanRiaXVjZmFrdGJuamVjIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTIzNDAyMTMsImV4cCI6MjEwNzkxNjIxM30.TWBIc8-chcw7aI2LYX8NEiopKWMz9-wNB9oqTKe5q9s";

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true,
  },
});
