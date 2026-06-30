import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { templatesApi } from "../api/client";
import cvFallback from "../assets/cv-assanvo-preview.png";

const STEPS = [
  { n: "1", title: "Choisis un modèle", text: "Plus de 20 designs prêts à l'emploi, déjà mis en page pour toi." },
  { n: "2", title: "Remplis tes infos", text: "Tu vois ton CV se construire en direct, sans rien régler." },
  { n: "3", title: "Télécharge ton PDF", text: "Un CV net, professionnel, prêt à envoyer en quelques minutes." },
];

export function Home() {
  const [previews, setPreviews] = useState([]);

  useEffect(() => {
    templatesApi
      .list()
      .then((templates) => {
        const images = (templates || [])
          .map((t) => t.preview_url || t.thumbnail_url)
          .filter(Boolean)
          .slice(0, 12);
        setPreviews(images.length ? images : [cvFallback]);
      })
      .catch(() => setPreviews([cvFallback]));
  }, []);

  const loop = previews.length ? [...previews, ...previews] : [];

  return (
    <section className="home">
      <div className="home-hero">
        <span className="home-eyebrow">CV optimisés par IA</span>
        <h1>
          Crée un CV qui décroche <span className="accent">l'entretien</span>
        </h1>
        <p className="home-sub">Choisis un modèle, remplis tes infos, télécharge. En quelques minutes.</p>
        <div className="home-cta">
          <Link className="btn btn-primary btn-lg" to="/builder">Créer mon CV</Link>
          <Link className="btn btn-outline btn-lg" to="/templates">Voir les modèles</Link>
        </div>
        <p className="home-trust">
          <strong>Compatible ATS</strong> · PDF prêt à envoyer · Photo recadrée automatiquement
        </p>
      </div>

      <div className="home-marquee" aria-label="Aperçu des modèles de CV">
        <div className="marquee-track">
          {loop.map((src, index) => (
            <img key={index} src={src} alt="" aria-hidden={index >= previews.length} loading="lazy" />
          ))}
        </div>
      </div>

      <div className="home-steps">
        {STEPS.map((step) => (
          <div className="step-card" key={step.n}>
            <span className="step-num">{step.n}</span>
            <h3>{step.title}</h3>
            <p>{step.text}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
