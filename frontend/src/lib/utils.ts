// Import clsx utility and ClassValue type for conditionally joining CSS class names together
import { clsx, type ClassValue } from "clsx";
// Import twMerge to intelligently merge Tailwind CSS class names and resolve utility collisions
import { twMerge } from "tailwind-merge";

/**
 * Merge conditional CSS class names using clsx followed by twMerge deduplication.
 *
 * @param {...ClassValue[]} inputs - Variadic list of class values, booleans, or condition objects.
 * @returns {string} Clean, merged, and deduplicated Tailwind CSS class string.
 * @example cn("px-4 py-2", isActive && "bg-teal-600 text-white")
 */
export function cn(...inputs: ClassValue[]): string {
  // Merge conditionally resolved classes using clsx followed by twMerge deduplication
  return twMerge(clsx(inputs));
}

/**
 * Format count and noun into correct grammatical English singular or plural representation.
 * Prevents awkward phrasing like "1 submission(s)" or "5 student(s)".
 *
 * @param {number} count - The numeric quantity being quantified.
 * @param {string} singular - The singular noun form (e.g. "submission", "student", "course").
 * @param {string} [plural] - Optional irregular plural form (e.g. "criteria" for "criterion").
 * @returns {string} Formatted count string (e.g. "1 submission", "5 submissions", "0 students").
 * @example pluralize(1, "submission") // returns "1 submission"
 * @example pluralize(4, "submission") // returns "4 submissions"
 * @example pluralize(2, "criterion", "criteria") // returns "2 criteria"
 */
export function pluralize(count: number, singular: string, plural?: string): string {
  // Determine plural form using custom plural override or appending 's'
  const pluralForm = plural || `${singular}s`;
  // Return formatted string with number and correct grammatical form
  return `${count} ${count === 1 ? singular : pluralForm}`;
}

/**
 * Convert arbitrary course or title text into canonical Title Case for academic consistency.
 *
 * @param {string} text - Raw input string to title case.
 * @returns {string} Title-cased output string.
 * @example toTitleCase("distributed systems") // returns "Distributed Systems"
 */
export function toTitleCase(text: string): string {
  // Guard against null or empty input
  if (!text) return "";
  // Split on spaces and capitalize the first letter of each significant word
  return text
    // Replace lowercase initial letters with uppercase counterparts
    .replace(/\b\w+/g, (word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase());
}
