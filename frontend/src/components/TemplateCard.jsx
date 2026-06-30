import { Link } from "react-router-dom";
import { CVPreview } from "./CVPreview";
import { templateStyleLabel } from "../templates/templateLabels";
import "../styles/TemplateCard.css";

export function TemplateCard({ template }) {
  const previewImage = template.thumbnail_url || template.preview_url || template.preview_image_url;
  const styleLabel = templateStyleLabel(template);

  return (
    <Link
      className="template-card template-card-link"
      to={`/builder?template=${template.id}`}
      aria-label={`Utiliser ${template.name}`}
      title={template.name}
    >
      <div className="template-preview">
        {previewImage ? (
          <img src={previewImage} alt={`Aperçu du modèle ${template.name}`} className="template-preview-image" />
        ) : (
          <CVPreview template={template} compact />
        )}

        <div className="badges badges-right">
          {template.is_premium && (
            <span className="badge badge-premium" title="Template premium">
              Pro
            </span>
          )}
        </div>
        <span className={`template-style-badge style-${template.category}`}>
          {styleLabel}
        </span>
      </div>
    </Link>
  );
}
