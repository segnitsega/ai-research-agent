import type { Metadata } from "next";
import { RunsIndex } from "@/components/runs-index";

export const metadata: Metadata = { title: "Runs" };

export default function RunsPage() {
  return <RunsIndex />;
}
