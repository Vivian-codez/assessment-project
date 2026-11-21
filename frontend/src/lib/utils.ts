// Import clsx utility and ClassValue type for conditionally joining CSS class names together
import { clsx, type ClassValue } from "clsx";
// Import twMerge to intelligently merge Tailwind CSS class names and resolve utility collisions
import { twMerge } from "tailwind-merge";

// Define and export the standard cn helper function accepting variadic class values
export function cn(...inputs: ClassValue[]) {
  // Merge conditionally resolved classes using clsx followed by twMerge deduplication
  return twMerge(clsx(inputs));
}
