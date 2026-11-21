import { createFileRoute, Navigate } from "@tanstack/react-router";

// Decoupled standalone rubric route - automatically redirects to consolidated assignments/dashboard view
export const Route = createFileRoute("/dashboard/rubrics/new")({
  component: DashboardRubricsRedirect,
});

function DashboardRubricsRedirect() {
  return <Navigate to="/dashboard" />;
}
