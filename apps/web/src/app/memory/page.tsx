import type { Metadata } from "next";
import { MemoryDesk } from "@/components/memory-desk";

export const metadata: Metadata = { title: "Memory" };

export default function MemoryPage() {
  return <MemoryDesk />;
}
