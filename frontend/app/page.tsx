import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-24 text-center">
      <h1 className="text-4xl font-bold">AquaSavannah LandVault</h1>
      <p className="max-w-xl text-base opacity-80">
        Platform rebuild in progress — Phase 2, Development Environment. See{" "}
        <code>docs/PHASE_GATES.md</code> for the current gate status.
      </p>
      <Button>Get started</Button>
    </main>
  );
}
