// Import TanStack Router helper to define a type-safe file-based route
import { createFileRoute } from "@tanstack/react-router";
// Import the core VerismApp component from the root route
import { VerismApp } from "./index";

// Define and export the TanStack route configuration for the /dashboard/rubrics/new path
export const Route = createFileRoute("/dashboard/rubrics/new")({
  // Bind the DashboardRubricsNewPageRoute component to render for this route
  component: DashboardRubricsNewPageRoute,
});

// Component function rendering the main Verism console initialized to the matrix rubric builder view
function DashboardRubricsNewPageRoute() {
  // Render VerismApp with the rubric_builder view active
  return <VerismApp initialView="rubric_builder" />;
}
