import type { Metadata } from "next";
import { RunDesk } from "@/components/research/run-desk";

export const metadata: Metadata = { title: "Run" };

export default async function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <RunDesk id={id} />;
}
