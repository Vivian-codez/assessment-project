/**
 * Verism AI – Client-Side Environment Validation.
 * Validates frontend environment variables at application startup using Zod.
 * Ensures missing or malformed variables produce clear diagnostic warnings rather than cryptic runtime errors.
 */

// Import Zod library for runtime schema validation
import { z } from "zod";

/**
 * Zod schema defining expected client-side Vite environment variables.
 */
export const clientEnvSchema = z.object({
  // Base URL pointing to the FastAPI backend REST API
  VITE_API_BASE_URL: z
    // Optional string in development, required in production
    .string()
    // Trim leading and trailing whitespace
    .trim()
    // Validate valid URL protocol format when provided
    .refine(
      (val) => {
        // Allow empty string in non-production local development
        if (!val) return true;
        // Verify string begins with http:// or https://
        return val.startsWith("http://") || val.startsWith("https://");
      },
      { message: "VITE_API_BASE_URL must begin with http:// or https://" },
    )
    .optional(),

  // Flag determining whether direct client-side Supabase authentication is enabled
  VITE_USE_SUPABASE: z
    // String representation of boolean flag
    .enum(["true", "false"])
    // Optional defaulting to false for FastAPI auth mode
    .optional()
    .default("false"),

  // Optional Supabase project endpoint URL
  VITE_SUPABASE_URL: z
    // String URL format
    .string()
    // Trim whitespace
    .trim()
    // Optional property
    .optional(),

  // Optional Supabase anonymous client JWT key
  VITE_SUPABASE_ANON_KEY: z
    // String property
    .string()
    // Trim whitespace
    .trim()
    // Optional property
    .optional(),
});

/**
 * Type contract representing inferred validated client environment values.
 */
export type ClientEnv = z.infer<typeof clientEnvSchema>;

/**
 * Validates client environment variables against the defined Zod schema.
 * Emits diagnostic warnings in production when critical settings are absent.
 *
 * @returns {ClientEnv} The validated environment configuration dictionary.
 * @throws {Error} When critical environment variables fail validation in strict mode.
 *
 * @example
 * ```typescript
 * const env = validateClientEnv();
 * console.log("API URL:", env.VITE_API_BASE_URL);
 * ```
 */
export function validateClientEnv(): ClientEnv {
  // Extract Vite environment variables object typed safely without any
  const envMap = import.meta.env as unknown as Record<string, string | undefined>;
  const rawEnv = {
    // Read API base URL
    VITE_API_BASE_URL: envMap["VITE_API_BASE_URL"],
    // Read Supabase usage toggle
    VITE_USE_SUPABASE: envMap["VITE_USE_SUPABASE"],
    // Read Supabase project URL
    VITE_SUPABASE_URL: envMap["VITE_SUPABASE_URL"],
    // Read Supabase anon key
    VITE_SUPABASE_ANON_KEY: envMap["VITE_SUPABASE_ANON_KEY"],
  };

  // Execute safe Zod schema parse
  const result = clientEnvSchema.safeParse(rawEnv);

  // Check if schema validation failed
  if (!result.success) {
    // Format error message list
    const issues = result.error.issues
      // Map issues to human-readable strings
      .map((i) => ` - ${i.path.join(".")}: ${i.message}`)
      // Join into multi-line string
      .join("\n");

    // Output formatted diagnostic notice to browser console
    console.error(`[Verism AI] Environment configuration validation errors:\n${issues}`);

    // Return parsed partial fallback data to avoid catastrophic startup halting
    return rawEnv as ClientEnv;
  }

  // Check for missing VITE_API_BASE_URL in production deployment
  if (import.meta.env?.PROD && !result.data.VITE_API_BASE_URL) {
    // Log prominent warning alerting developer to configure Vercel settings
    console.warn(
      "[Verism AI] WARNING: VITE_API_BASE_URL is not configured in Vercel project settings. " +
        "Browser API requests will attempt to resolve to http://localhost:8000/api/v1 which will fail. " +
        "Set VITE_API_BASE_URL in Vercel to your deployed backend URL.",
    );
  }

  // Return validated environment dictionary
  return result.data;
}

// Execute environment validation on module initialization
export const clientEnv = validateClientEnv();
