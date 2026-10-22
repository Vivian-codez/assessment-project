import { createFileRoute } from "@tanstack/react-router";
import { VerismApp } from "./index";

export const Route = createFileRoute("/dashboard/roster")({
  component: DashboardRosterPageRoute,
});

function DashboardRosterPageRoute() {
  return <VerismApp initialView="roster" />;
}
