import { useState } from "react";
import { triggerReconciliation } from "../api";

export default function ReconcileButton() {
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">(
    "idle"
  );

  async function handleClick() {
    setState("loading");
    try {
      await triggerReconciliation();
      setState("done");
      setTimeout(() => setState("idle"), 3000);
    } catch {
      setState("error");
      setTimeout(() => setState("idle"), 3000);
    }
  }

  const label = {
    idle: "Trigger Reconciliation",
    loading: "Triggering...",
    done: "Triggered",
    error: "Failed — retry?",
  }[state];

  const colors = {
    idle: "bg-indigo-600 hover:bg-indigo-700",
    loading: "bg-indigo-400 cursor-not-allowed",
    done: "bg-green-600",
    error: "bg-red-600 hover:bg-red-700",
  }[state];

  return (
    <button
      onClick={handleClick}
      disabled={state === "loading"}
      className={`px-4 py-2 rounded-lg text-white text-sm font-medium transition-colors ${colors}`}
    >
      {label}
    </button>
  );
}
