import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Gift, MoreHorizontal, PenLine, Plus, Share2, Star } from "lucide-react";
import { cvsApi } from "../api/client";
import { useCVStore } from "../stores/cvStore";
import { Button } from "../components/Button";
import { CoverLetterModal } from "../components/CoverLetterModal";
import { CVThumbnail } from "../components/CVThumbnail";
import { OfferAdaptPanel } from "../components/OfferAdaptPanel";
import "../styles/Dashboard.css";

function formatDate(value) {
  if (!value) return "Jamais";
  return new Intl.DateTimeFormat("fr-FR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function AccessBanner({ access, onSubscribe, busy, weeklyPrice }) {
  const days = access.days_left;
  if (access.is_trial && access.trial_active) {
    return (
      <div className="access-banner trial">
        <div>
          <strong><Gift size={15} className="icon-inline" /> Essai gratuit</strong>
          <span>Il te reste {days} jour{days > 1 ? "s" : ""}. CV illimités pendant l'essai.</span>
        </div>
        <Button variant="outline" onClick={onSubscribe} disabled={busy}>
          {busy ? "…" : "S'abonner"}
        </Button>
      </div>
    );
  }
  if (access.has_active_access && access.plan === "weekly") {
    return (
      <div className="access-banner active">
        <div>
          <strong><Star size={15} className="icon-inline" /> Abonnement actif</strong>
          <span>{access.cv_credits} CV restant{access.cv_credits > 1 ? "s" : ""} · expire dans {days} jour{days > 1 ? "s" : ""}.</span>
        </div>
      </div>
    );
  }
  return (
    <div className="access-banner ended">
      <div>
        <strong>Ton accès est terminé</strong>
        <span>Abonne-toi pour continuer : {weeklyPrice} F / semaine — 5 CV.</span>
      </div>
      <Button onClick={onSubscribe} disabled={busy}>
        {busy ? "…" : `S'abonner (${weeklyPrice} F)`}
      </Button>
    </div>
  );
}

export function Dashboard() {
  const {
    cvs,
    loading,
    error,
    access,
    fetchCVs,
    fetchPlans,
    initializePayment,
    generateCV,
    downloadCV,
    duplicateCV,
    deleteCV,
    verifyPayment,
  } = useCVStore();
  const [busyId, setBusyId] = useState(null);
  const [paymentMessage, setPaymentMessage] = useState("");
  const [payBusy, setPayBusy] = useState(false);
  const [letterCvId, setLetterCvId] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [shareMessage, setShareMessage] = useState("");
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    fetchCVs().catch(() => {});
    fetchPlans().catch(() => {});
  }, [fetchCVs, fetchPlans]);

  const handleSubscribe = async () => {
    setPayBusy(true);
    try {
      const result = await initializePayment("weekly");
      if (result?.authorization_url) window.location.href = result.authorization_url;
    } catch {
      setPaymentMessage("Paiement indisponible pour le moment. Réessaie.");
    } finally {
      setPayBusy(false);
    }
  };

  useEffect(() => {
    const reference = searchParams.get("reference") || searchParams.get("trxref");
    if (!reference) return;

    verifyPayment(reference)
      .then(() => setPaymentMessage("Paiement confirmé. Votre accès est actif."))
      .catch(() => setPaymentMessage(""))
      .finally(() => {
        setSearchParams({}, { replace: true });
        fetchCVs().catch(() => {});
      });
  }, [fetchCVs, searchParams, setSearchParams, verifyPayment]);

  const stats = useMemo(() => {
    const generated = cvs.filter((cv) => cv.status === "generated" && (cv.generated_pdf || cv.generated_file)).length;
    return {
      total: cvs.length,
      generated,
      drafts: cvs.length - generated,
    };
  }, [cvs]);

  const withBusy = async (cv, action) => {
    setBusyId(cv.id);
    try {
      await action();
    } catch {
      // L'erreur est déjà exposée dans le store.
    }
    setBusyId(null);
  };

  const handleGenerate = (cv) =>
    withBusy(cv, async () => {
      await generateCV(cv.id);
      await downloadCV(cv.id, cv.title);
    });

  const handleDownload = (cv) =>
    withBusy(cv, async () => {
      await downloadCV(cv.id, cv.title);
    });

  const handleDuplicate = (cv) =>
    withBusy(cv, async () => {
      const duplicated = await duplicateCV(cv.id);
      navigate(`/builder/${duplicated.id}`);
    });

  const handleDelete = (cv) => {
    if (!window.confirm(`Supprimer "${cv.title}" ?`)) return;
    withBusy(cv, async () => {
      await deleteCV(cv.id);
    });
  };

  // Définit ce CV comme référence : c'est lui qu'on adaptera à toutes les offres.
  const handleSetReference = (cv) =>
    withBusy(cv, async () => {
      await cvsApi.setReference(cv.id);
      await fetchCVs();
    });

  // Active le lien public (une fois généré, il ne change plus) et le copie
  // directement dans le presse-papiers — prêt à coller à un recruteur.
  const handleShare = (cv) =>
    withBusy(cv, async () => {
      const updated = await cvsApi.share(cv.id, true);
      await fetchCVs();
      const link = `${window.location.origin}${updated.public_url}`;
      try {
        await navigator.clipboard.writeText(link);
        setShareMessage(`Lien copié : ${link}`);
      } catch {
        setShareMessage(`Lien de ${cv.title} : ${link}`);
      }
      window.setTimeout(() => setShareMessage(""), 6000);
    });

  if (loading && !cvs.length) {
    return (
      <div className="dashboard dashboard-loading">
        <p className="loading">Chargement de vos CV…</p>
      </div>
    );
  }

  return (
    <div className="dashboard dashboard-premium">
      <section className="dash-hero">
        <div>
          <p className="dash-eyebrow">Espace CV</p>
          <h1>Vos CV</h1>
          <p>
            Créez un CV, adaptez-le à une offre, téléchargez le PDF.
          </p>
        </div>
        <div className="dash-hero-actions">
          <Link to="/builder">
            <Button>Créer un CV</Button>
          </Link>
          <Link to="/templates" className="dash-link-button">
            Voir les modèles
          </Link>
        </div>
      </section>

      {access?.payments_enforced && (
        <AccessBanner access={access} onSubscribe={handleSubscribe} busy={payBusy} weeklyPrice={1000} />
      )}

      <OfferAdaptPanel cvs={cvs} />

      <section className="dash-stats" aria-label="Statistiques des CV">
        <div>
          <strong>{stats.total}</strong>
          <span>CV au total</span>
        </div>
        <div className="dash-stats-sep" aria-hidden="true" />
        <div>
          <strong>{stats.generated}</strong>
          <span>Prêts à envoyer</span>
        </div>
        <div className="dash-stats-sep" aria-hidden="true" />
        <div>
          <strong>{stats.drafts}</strong>
          <span>Brouillons</span>
        </div>
      </section>

      {paymentMessage && <p className="dash-success">{paymentMessage}</p>}
      {shareMessage && <p className="dash-success">{shareMessage}</p>}
      {error && <p className="form-error global">{error}</p>}

      <section className="dash-section-head">
        <div>
          <h2>Mes CV</h2>
          <p>Reprenez un CV ou créez-en un nouveau.</p>
        </div>
        <Link to="/builder" className="dash-new-btn">
          <Plus size={16} /> Nouveau CV
        </Link>
      </section>

      {cvs.length === 0 && (
        <Link to="/builder" className="dash-empty-state">
          <span className="new-document-plus"><Plus size={20} /></span>
          <strong>Crée ton premier CV</strong>
          <small>Importe un PDF ou saisis tes infos toi-même</small>
        </Link>
      )}

      <div className="document-grid">
        {cvs.map((cv) => {
          const isGenerated = cv.status === "generated" && (cv.generated_pdf || cv.generated_file);
          const isBusy = busyId === cv.id;

          return (
            <article key={cv.id} className="document-card">
              <Link to={`/builder/${cv.id}`} className="document-preview-link" aria-label={`Modifier ${cv.title}`}>
                <div className="document-preview">
                  <CVThumbnail templateId={cv.template_detail?.id || cv.template} data={cv.data} />
                </div>
              </Link>
              <div className="document-card-body">
                <div className="document-title-row">
                  <div className="document-title-main">
                    <h3 className="document-title" title={cv.title}>{cv.title}</h3>
                    <p>{cv.template_name || cv.template_detail?.name || "Modèle"} · {isGenerated ? "Généré" : "Brouillon"}</p>
                  </div>
                  <div className="document-title-side">
                    <button
                      type="button"
                      className={`reference-star ${cv.is_reference ? "active" : ""}`}
                      title={cv.is_reference ? "CV de référence : adapté par défaut à chaque offre" : "Définir comme CV de référence"}
                      aria-label={cv.is_reference ? "CV de référence" : "Définir comme CV de référence"}
                      disabled={isBusy}
                      onClick={() => !cv.is_reference && handleSetReference(cv)}
                    >
                      <Star size={15} />
                    </button>
                    <span className={`status-pill ${isGenerated ? "ready" : "draft"}`}>
                      {isGenerated ? "Prêt" : "À finir"}
                    </span>
                    {cv.is_public && (
                      <span className="status-pill public" title="CV partagé publiquement">
                        👁 {cv.public_view_count || 0}
                      </span>
                    )}
                  </div>
                </div>
                {cv.is_reference && (
                  <p className="reference-note"><Star size={12} className="icon-inline" /> CV de référence — adapté par défaut à chaque nouvelle offre</p>
                )}
                <p className="document-date">Dernière mise à jour: {formatDate(cv.updated_at)}</p>
                <div className="document-actions">
                  <Link to={`/builder/${cv.id}`} className="dash-action-link">
                    Modifier
                  </Link>
                  {isGenerated ? (
                    <Button type="button" disabled={isBusy} onClick={() => handleDownload(cv)}>
                      Télécharger
                    </Button>
                  ) : (
                    <Button type="button" variant="outline" disabled={isBusy} onClick={() => handleGenerate(cv)}>
                      {isBusy ? "..." : "Générer PDF"}
                    </Button>
                  )}
                  <button
                    type="button"
                    className="document-more-btn"
                    aria-label="Plus d'actions"
                    onClick={() => setExpandedId(expandedId === cv.id ? null : cv.id)}
                  >
                    <MoreHorizontal size={16} />
                  </button>
                </div>
                {expandedId === cv.id && (
                  <div className="document-actions document-actions-more">
                    {isGenerated && (
                      <Button type="button" variant="outline" disabled={isBusy} onClick={() => handleGenerate(cv)}>
                        {isBusy ? "..." : "Regénérer PDF"}
                      </Button>
                    )}
                    <Button type="button" variant="outline" disabled={isBusy} onClick={() => handleShare(cv)}>
                      <Share2 size={14} /> {cv.is_public ? "Copier le lien" : "Partager"}
                    </Button>
                    <Button type="button" variant="outline" disabled={isBusy} onClick={() => handleDuplicate(cv)}>
                      Dupliquer
                    </Button>
                    {(cv.has_cover_letter || cv.has_job_offer) && (
                      <Button type="button" variant="outline" disabled={isBusy} onClick={() => setLetterCvId(cv.id)}>
                        <PenLine size={14} /> Lettre
                      </Button>
                    )}
                    <Button type="button" variant="outline" disabled={isBusy} onClick={() => handleDelete(cv)}>
                      Supprimer
                    </Button>
                  </div>
                )}
              </div>
            </article>
          );
        })}
      </div>

      {letterCvId && <CoverLetterModal cvId={letterCvId} onClose={() => setLetterCvId(null)} />}
    </div>
  );
}
