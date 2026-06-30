import { useEffect, useMemo, useState } from "react";
import { useCVStore } from "../stores/cvStore";
import { useAuthStore } from "../stores/authStore";
import { TemplateGrid } from "../components/TemplateGrid";
import { normalizeSearchText, templateSearchText } from "../templates/templateLabels";
import "../styles/Templates.css";

const STYLE_FILTERS = [
  { value: "all", label: "Tous" },
  { value: "classic", label: "Classique" },
  { value: "creative", label: "Standard" },
  { value: "modern", label: "Moderne" },
  { value: "colorful", label: "Coloré" },
  { value: "minimal", label: "Minimaliste" },
];

export function Templates() {
  const { templates, loading, error, fetchTemplates, syncTemplateLibrary } = useCVStore();
  const { user } = useAuthStore();
  const [syncMessage, setSyncMessage] = useState("");
  const [query, setQuery] = useState("");
  const [styleFilter, setStyleFilter] = useState("all");

  useEffect(() => {
    fetchTemplates().catch(() => {});
  }, [fetchTemplates]);

  const canSync = Boolean(user?.is_staff || user?.is_superuser);

  const handleSync = async () => {
    setSyncMessage("");
    try {
      const result = await syncTemplateLibrary();
      const added = result.added?.length || 0;
      setSyncMessage(`${result.templates_count || 0} modèles alignés. ${added} nouveau(x).`);
    } catch {
      setSyncMessage("");
    }
  };

  const filteredTemplates = useMemo(() => {
    const normalizedQuery = normalizeSearchText(query);
    return (templates || []).filter((template) => {
      const matchesStyle = styleFilter === "all" || template.category === styleFilter;
      const matchesQuery = !normalizedQuery || templateSearchText(template).includes(normalizedQuery);
      return matchesStyle && matchesQuery;
    });
  }, [query, styleFilter, templates]);

  return (
    <div className="templates-page">
      <div className="templates-header">
        <h1>Choisir un modèle</h1>
        <p className="templates-subtitle">
          Touchez un modèle pour démarrer.
        </p>
        <div className="template-search-panel" role="search">
          <input
            className="template-search-input"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Rechercher: classique, standard, moderne, coloré, minimaliste..."
            aria-label="Rechercher un style de CV"
          />
          <div className="template-style-filters" aria-label="Filtrer les modèles par style">
            {STYLE_FILTERS.map((filter) => (
              <button
                key={filter.value}
                type="button"
                className={styleFilter === filter.value ? "style-filter active" : "style-filter"}
                onClick={() => setStyleFilter(filter.value)}
              >
                {filter.label}
              </button>
            ))}
          </div>
        </div>
        {canSync && (
          <div className="template-admin-tools">
            <button type="button" onClick={handleSync} disabled={loading}>
              {loading ? "Synchronisation..." : "Synchroniser les modèles"}
            </button>
            {(syncMessage || error) && <span className={error ? "sync-error" : "sync-ok"}>{error || syncMessage}</span>}
          </div>
        )}
      </div>
      <TemplateGrid
        templates={filteredTemplates}
        loading={loading}
      />
    </div>
  );
}
