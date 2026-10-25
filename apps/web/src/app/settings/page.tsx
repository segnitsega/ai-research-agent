import type { Metadata } from "next";
import { SettingsDesk } from "@/components/settings-desk";

export const metadata: Metadata = { title: "Settings" };

export default function SettingsPage() {
  return <SettingsDesk />;
}
