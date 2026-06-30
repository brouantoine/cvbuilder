import { useState } from "react";
import { Link } from "react-router-dom";
import { CVPreview } from "./CVPreview";
import "../styles/TemplatePreviewModal.css";

export function TemplatePreviewModal({ template, isOpen, onClose }) {
  const [fullscreen, setFullscreen] = useState(false);

  if (!isOpen || !template) return null;

  const categoryLabel = template.category_display || "Classique";
  const canUse = template.is_active !== false;
  const previewImage = template.preview_url || template.thumbnail_url || template.preview_image_url;

  return (
    <>
      <div
        className="modal-overlay"
        onClick={onClose}
        role="presentation"
      />

      <div className={`modal-container ${fullscreen ? "fullscreen" : ""}`}>
        <div className="modal-header">
          <div className="header-left">
            <h2 className="modal-title">{template.name}</h2>
            <span className={`category-badge category-${template.category}`}>
              {categoryLabel}
            </span>
            {template.is_premium && (
              <span className="modal-premium-badge">Premium</span>
            )}
          </div>
          <div className="header-actions">
            <button
              className="btn-fullscreen"
              onClick={() => setFullscreen(!fullscreen)}
              title="Plein écran"
              aria-label="Activer le plein écran"
            >
              {fullscreen ? "Réduire" : "Agrandir"}
            </button>
            <button
              className="btn-close"
              onClick={onClose}
              title="Fermer"
              aria-label="Fermer"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="modal-content">
          <div className="preview-container">
            {previewImage ? (
              <img src={previewImage} alt={`Aperçu du modèle ${template.name}`} className="preview-image" />
            ) : (
              <CVPreview template={template} />
            )}
          </div>

          <div className="info-panel">
            <div className="info-section">
              <h3>Description</h3>
              <p>{template.description}</p>
            </div>

            {/* Long Description */}
            {template.long_description && (
              <div className="info-section">
                <h3>Caractéristiques</h3>
                <p>{template.long_description}</p>
              </div>
            )}

            <div className="info-details">
              <div className="detail-item">
                <span className="label">Catégorie:</span>
                <span className="value">{categoryLabel}</span>
              </div>
              <div className="detail-item">
                <span className="label">Type:</span>
                <span className="value">
                  {template.is_premium ? "Premium" : "Gratuit"}
                </span>
              </div>
              <div className="detail-item">
                <span className="label">Génération:</span>
                <span className="value">
                  {canUse ? "Prêt" : "À configurer"}
                </span>
              </div>
            </div>

            <div className="modal-actions">
              {canUse ? (
                <Link className="btn btn-primary btn-large" to={`/builder?template=${template.id}`}>
                  Choisir ce modèle
                </Link>
              ) : (
                <button className="btn btn-outline btn-large" type="button" disabled>
                  Modèle indisponible
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
