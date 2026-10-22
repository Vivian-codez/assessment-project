import { createFileRoute } from "@tanstack/react-router";
import { VerismApp } from "./index";

export const Route = createFileRoute("/dashboard/rubrics/new")({
  component: DashboardRubricsNewPageRoute,
});

function DashboardRubricsNewPageRoute() {
  return <VerismApp initialView="rubric_builder" />;
}
