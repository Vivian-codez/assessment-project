import { createFileRoute } from "@tanstack/react-router";
import { VerismApp } from "./index";

export const Route = createFileRoute("/dashboard/")({
  component: DashboardPageRoute,
});

function DashboardPageRoute() {
  return <VerismApp initialView="dashboard" />;
}
