import { Suspense } from "react";
import { HomeDesk } from "@/components/home-desk";

export default function HomePage() {
  return (
    <Suspense fallback={<p className="text-sm text-muted">Opening the desk…</p>}>
      <HomeDesk />
    </Suspense>
  );
}
