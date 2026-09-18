import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { cvsApi } from "../api/client";
import "../styles/CVPublic.css";

// Dimensions d'une page A4 à 96 dpi — mêmes constantes que CVThumbnail,
// pour un rendu à l'échelle exacte quelle que soit la largeur d'écran.
const PAGE_WIDTH = 794;
const PAGE_HEIGHT = 1123;

/**
 * Page publique d'un CV partagé (/cv/:slug) : lecture seule, sans connexion.
 * C'est le lien que le candidat envoie à un recruteur à la place d'un PDF
 * figé — et une vitrine gratuite pour MonCVPro à chaque ouverture.
 */
export function CVPublic() {
  const { slug } = useParams();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [cv, setCV] = useState(null);
  const [scale, setScale] = useState(1);
  const wrapRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    setError("");
    cvsApi
      .publicView(slug)
      .then((res) => {
        if (!cancelled) setCV(res);
      })
      .catch((err) => {
        if (!cancelled) setError(err?.detail || "Ce lien n'existe pas ou n'est plus partagé.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  useEffect(() => {
    const element = wrapRef.current;
    if (!element) return undefined;
    const update = () => setScale(Math.min(1, element.clientWidth / PAGE_WIDTH));
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, [cv]);

  if (loading) {
    return (
      <div className="cv-public-page">
        <p className="loading">Chargement du CV…</p>
      </div>
    );
  }

  if (error || !cv) {
    return (
      <div className="cv-public-page cv-public-missing">
        <h1>Lien introuvable</h1>
        <p>{error || "Ce CV n'est plus partagé publiquement."}</p>
        <Link to="/" className="btn btn-primary">Découvrir MonCVPro</Link>
      </div>
    );
  }

  const { html, candidate_name: candidateName, job_title: jobTitle } = cv;

  return (
    <div className="cv-public-page">
      <div className="cv-public-head">
        <div>
          <p className="eyebrow">CV partagé</p>
          <h1>{candidateName}</h1>
          {jobTitle && <p className="cv-public-job">{jobTitle}</p>}
        </div>
        <Link to="/register" className="btn btn-primary">Créer mon CV avec MonCVPro</Link>
      </div>

      <div className="cv-public-frame-wrap" ref={wrapRef} style={{ height: PAGE_HEIGHT * scale }}>
        <iframe
          title={`CV de ${candidateName}`}
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

      <p className="cv-public-footer">
        Ce CV a été créé avec <Link to="/">MonCVPro</Link>.
      </p>
    </div>
  );
}
