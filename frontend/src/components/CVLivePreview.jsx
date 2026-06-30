import { useEffect, useMemo, useRef, useState } from "react";
import { cvsApi } from "../api/client";

// Dimensions d'une page A4 à 96 dpi (210mm × 297mm).
const PAGE_WIDTH = 794;
const PAGE_HEIGHT = 1123;

/**
 * Aperçu WYSIWYG : affiche dans une iframe le HTML rendu par le backend
 * (le même qui produit le PDF). Ce que l'utilisateur voit ici est exactement
 * ce qu'il téléchargera.
 */
export function CVLivePreview({ templateId, data }) {
  const [html, setHtml] = useState("");
  const [scale, setScale] = useState(1);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const wrapRef = useRef(null);

  // Sérialisation stable pour ne déclencher l'aperçu que si le contenu change.
  const dataKey = useMemo(() => JSON.stringify(data || {}), [data]);

  useEffect(() => {
    if (!templateId) return undefined;
    let cancelled = false;
    setLoading(true);
    const handle = setTimeout(() => {
      cvsApi
        .preview({ template: templateId, data })
        .then((res) => {
          if (cancelled) return;
          setHtml(res.html || "");
          setError("");
        })
        .catch((err) => {
          if (cancelled) return;
          setError(err?.detail || "Aperçu indisponible.");
        })
        .finally(() => {
          if (!cancelled) setLoading(false);
        });
    }, 350);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [templateId, dataKey]);

  // Mise à l'échelle de la page A4 pour remplir la largeur disponible.
  useEffect(() => {
    const element = wrapRef.current;
    if (!element) return undefined;
    const update = () => setScale(element.clientWidth / PAGE_WIDTH);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="cv-live-preview" ref={wrapRef} style={{ height: PAGE_HEIGHT * scale }}>
      {error ? (
        <p className="cv-live-preview-error">{error}</p>
      ) : (
        <iframe
          title="Aperçu du CV"
          srcDoc={html}
          className={`cv-live-preview-frame ${loading && !html ? "is-loading" : ""}`}
          style={{
            width: PAGE_WIDTH,
            height: PAGE_HEIGHT,
            transform: `scale(${scale})`,
            transformOrigin: "top left",
          }}
        />
      )}
    </div>
  );
}
