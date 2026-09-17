import { Loader2 } from "lucide-react";
import { useLoadingStore } from "../stores/loadingStore";

/**
 * Chargement global : barre de progression en haut de page + pastille
 * « Chargement… ». Alimenté par le client API : visible à chaque clic qui
 * déclenche une requête, partout dans l'application. L'apparition est
 * différée de 250 ms en CSS pour éviter le clignotement sur les réponses
 * instantanées. N'intercepte aucun clic.
 */
export function GlobalLoader() {
  const pending = useLoadingStore((state) => state.pending);

  if (pending <= 0) return null;

  return (
    <div className="global-loader" aria-live="polite">
      <div className="global-loader-bar" />
      <div className="global-loader-pill">
        <Loader2 className="global-loader-spin" size={16} />
        Chargement…
      </div>
    </div>
  );
}
