// Import TanStack Router helper to define a type-safe file-based route
import { createFileRoute } from "@tanstack/react-router";
// Import the core VerismApp component from the root route
import { VerismApp } from "./index";

// Define and export the TanStack route configuration for the /dashboard/ path
export const Route = createFileRoute("/dashboard/")({
  // Bind the DashboardPageRoute component to render for this route
  component: DashboardPageRoute,
});

// Component function rendering the main Verism console initialized to the dashboard view
function DashboardPageRoute() {
  // Render VerismApp with the dashboard view active
  return <VerismApp initialView="dashboard" />;
}
