import type { Metadata } from "next";
import { Fraunces, Outfit } from "next/font/google";
import { Shell } from "@/components/shell";
import "./globals.css";

const display = Fraunces({ subsets: ["latin"], variable: "--font-fraunces" });
const sans = Outfit({ subsets: ["latin"], variable: "--font-outfit" });

export const metadata: Metadata = {
  title: { default: "Research Agent", template: "%s · Research Agent" },
  description: "A reading desk for multi-agent research with cited sources",
  applicationName: "Research Agent",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${display.variable} ${sans.variable}`} suppressHydrationWarning>
      <body>
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
