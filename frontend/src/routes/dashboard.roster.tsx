// Import TanStack Router helper to define a type-safe file-based route
import { createFileRoute } from "@tanstack/react-router";
// Import the core VerismApp component from the root route
import { VerismApp } from "./index";

// Define and export the TanStack route configuration for the /dashboard/roster path
export const Route = createFileRoute("/dashboard/roster")({
  // Bind the DashboardRosterPageRoute component to render for this route
  component: DashboardRosterPageRoute,
});

// Component function rendering the main Verism console initialized to the roster roll call view
function DashboardRosterPageRoute() {
  // Render VerismApp with the roster roll call view active
  return <VerismApp initialView="roster" />;
}
