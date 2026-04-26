import { useEffect, useState } from "react";
import type { Dossier } from "../types";

type DossierState =
  | { status: "loading"; dossier: null; error: null }
  | { status: "ready"; dossier: Dossier; error: null }
  | { status: "error"; dossier: null; error: string };

export function useDossier(): DossierState {
  const [state, setState] = useState<DossierState>({
    status: "loading",
    dossier: null,
    error: null,
  });

  useEffect(() => {
    let cancelled = false;

    fetch("/match_dossier.json")
      .then((response) => {
        if (!response.ok) {
          throw new Error(`Failed to load dossier: ${response.status}`);
        }
        return response.json() as Promise<Dossier>;
      })
      .then((dossier) => {
        if (!cancelled) {
          setState({ status: "ready", dossier, error: null });
        }
      })
      .catch((error: unknown) => {
        if (!cancelled) {
          setState({
            status: "error",
            dossier: null,
            error: error instanceof Error ? error.message : "Failed to load dossier",
          });
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
