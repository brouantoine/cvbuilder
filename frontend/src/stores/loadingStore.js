import { create } from "zustand";

/**
 * Compteur global des requêtes API en vol. Alimenté automatiquement par
 * api()/apiBlob() (sauf appels marqués silent) : chaque clic qui déclenche
 * une requête affiche le chargement global, partout dans l'application.
 */
export const useLoadingStore = create((set) => ({
  pending: 0,
  start: () => set((state) => ({ pending: state.pending + 1 })),
  stop: () => set((state) => ({ pending: Math.max(0, state.pending - 1) })),
}));
