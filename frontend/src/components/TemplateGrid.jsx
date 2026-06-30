import { TemplateCard } from "./TemplateCard";
import "../styles/TemplateGrid.css";

export function TemplateGrid({ templates, loading }) {
  if (loading) {
    return (
      <div className="template-grid loading">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="template-skeleton" />
        ))}
      </div>
    );
  }

  if (!templates?.length) {
    return (
      <div className="template-grid empty">
        <div className="empty-state">
          <p className="empty-text">Aucun modèle disponible.</p>
          <p className="empty-subtext">Les modèles seront disponibles bientôt.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="template-grid">
      {templates.map((template) => (
        <TemplateCard
          key={template.id}
          template={template}
        />
      ))}
    </div>
  );
}
