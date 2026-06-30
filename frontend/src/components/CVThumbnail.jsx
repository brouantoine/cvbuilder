import { useEffect, useRef, useState } from "react";
import { cvsApi } from "../api/client";

// Dimensions d'une page A4 à 96 dpi.
const PAGE_WIDTH = 794;
const PAGE_HEIGHT = 1123;

/**
 * Vignette d'un CV : affiche le VRAI rendu (le même HTML que le PDF), mis à
 * l'échelle pour remplir la carte. Rendu rapide (mode `fast`, sans la mesure).
 */
export function CVThumbnail({ templateId, data }) {
  const [html, setHtml] = useState("");
  const [scale, setScale] = useState(0.3);
  const wrapRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    cvsApi
      .preview({ template: templateId, data, fast: true })
      .then((res) => {
        if (!cancelled) setHtml(res.html || "");
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [templateId, data]);

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
    <div className="cv-thumb" ref={wrapRef}>
      <iframe
        title="Aperçu du CV"
        srcDoc={html}
        scrolling="no"
        style={{
          width: PAGE_WIDTH,
          height: PAGE_HEIGHT,
          transform: `scale(${scale})`,
          transformOrigin: "top left",
        }}
      />
    </div>
  );
}
