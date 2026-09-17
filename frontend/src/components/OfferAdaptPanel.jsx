import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { cvsApi } from "../api/client";
import { useCVStore } from "../stores/cvStore";
import { AdaptProposal } from "./AdaptProposal";
import { Button } from "./Button";
import { CoverLetterModal } from "./CoverLetterModal";
import { CheckCircle2, PenLine, Star, Target } from "lucide-react";

/**
 * Proposé dès l'arrivée sur l'espace CV : colle le texte d'une offre OU
 * téléverse sa capture d'écran (texte extrait automatiquement). L'analyse
 * renvoie un verdict franc et des propositions en miroir ; « Créer le CV
 * adapté » génère un nouveau CV, puis propose la lettre de motivation.
 * Le CV de référence (étoile) est présélectionné : c'est lui qu'on adapte.
 */
export function OfferAdaptPanel({ cvs }) {
  const { updateCV, uploadContext, fetchCVs } = useCVStore();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [cvId, setCvId] = useState("");
  const [offerText, setOfferText] = useState("");
  const [offerFiles, setOfferFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [report, setReport] = useState(null);
  const [createdCV, setCreatedCV] = useState(null);
  const [letterOpen, setLetterOpen] = useState(false);
  const adaptedRef = useRef(null);

  // Par défaut : le CV de référence, sinon le plus récent.
  const referenceCv = useMemo(() => cvs.find((cv) => cv.is_reference), [cvs]);
  const defaultCvId = useMemo(() => String(referenceCv?.id || cvs[0]?.id || ""), [referenceCv, cvs]);
  const selectedCvId = cvId || defaultCvId;

  if (!cvs.length) return null;

  const handleAnalyze = async () => {
    if (!offerText.trim() && !offerFiles.length) {
      setError("Colle le texte de l'offre ou ajoute sa (ses) capture(s) d'écran.");
      return;
    }
    setError("");
    setReport(null);
    setCreatedCV(null);
    setBusy(true);
    try {
      if (offerFiles.length) {
        const formData = new FormData();
        offerFiles.forEach((file) => formData.append("job_offer_file", file));
        if (offerText.trim()) formData.append("job_offer_text", offerText.trim());
        await uploadContext(selectedCvId, formData);
      } else {
        await updateCV(selectedCvId, { job_offer_text: offerText.trim() });
      }
      const res = await cvsApi.adaptPreview(selectedCvId);
      adaptedRef.current = res.adapted_data;
      setReport(res.report);
    } catch (err) {
      setError(err?.detail || err?.message || "Analyse impossible pour le moment. Réessaie.");
    } finally {
      setBusy(false);
    }
  };

  const handleReplace = async () => {
    if (!adaptedRef.current) return;
    setBusy(true);
    setError("");
    try {
      // Crée un NOUVEAU CV adapté (titré avec le poste visé) : l'original
      // reste intact et pourra être ré-adapté à d'autres offres.
      const created = await cvsApi.adaptApply(selectedCvId, adaptedRef.current);
      setReport(null);
      setCreatedCV(created);
      fetchCVs().catch(() => {});
    } catch (err) {
      setError(err?.detail || err?.message || "Impossible de créer le CV adapté. Réessaie.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className={`offer-adapt-panel ${open ? "open" : ""}`}>
      <button type="button" className="offer-adapt-head" onClick={() => setOpen(!open)}>
        <div>
          <strong><Target size={16} className="icon-inline" /> Tu postules à une offre ?</strong>
          <span>Colle l'offre ou sa capture d'écran : CV adapté + lettre de motivation, prêts à envoyer.</span>
        </div>
        <span className="offer-adapt-toggle">{open ? "Fermer" : "Adapter mon CV"}</span>
      </button>

      {open && (
        <div className="offer-adapt-body">
          <label className="offer-adapt-field">
            <span>CV à adapter {referenceCv ? "(ton CV de référence est présélectionné)" : ""}</span>
            <select value={selectedCvId} onChange={(event) => setCvId(event.target.value)} disabled={busy}>
              {cvs.map((cv) => (
                <option key={cv.id} value={cv.id}>
                  {cv.is_reference ? "★ " : ""}{cv.title} — {cv.template_name || cv.template_detail?.name || "Modèle"}
                </option>
              ))}
            </select>
          </label>

          <label className="offer-adapt-field">
            <span>Texte de l'offre</span>
            <textarea
              rows={4}
              value={offerText}
              onChange={(event) => setOfferText(event.target.value)}
              placeholder="Colle ici le texte de l'offre d'emploi…"
              disabled={busy}
            />
          </label>

          <label className="upload-box offer-adapt-upload">
            <span>… ou capture(s) d'écran / PDF de l'offre</span>
            <strong>
              {offerFiles.length > 1
                ? `${offerFiles.length} fichiers sélectionnés`
                : offerFiles[0]?.name || "Image(s) PNG/JPG ou PDF — plusieurs captures possibles"}
            </strong>
            <small>Image (une ou plusieurs captures) ou fichier PDF : le texte de l'offre est extrait automatiquement.</small>
            <input
              type="file"
              accept="image/*,application/pdf"
              multiple
              onChange={(event) => setOfferFiles(Array.from(event.target.files || []))}
              disabled={busy}
            />
          </label>

          {error && <p className="form-error global">{error}</p>}

          {!report && !createdCV && (
            <Button type="button" className="offer-adapt-cta" onClick={handleAnalyze} disabled={busy}>
              {busy ? "Analyse de l'offre… (jusqu'à 1 min)" : <><Target size={16} /> Adapter mon CV à cette offre</>}
            </Button>
          )}

          <AdaptProposal report={report} busy={busy} onReplace={handleReplace} onDismiss={() => setReport(null)} />

          {createdCV && (
            <div className="adapt-success">
              <p className="adapt-success-title">
                <CheckCircle2 size={16} className="icon-inline" /> CV adapté créé : « {createdCV.title} » — ton original est conservé.
              </p>
              <p className="adapt-success-hint">
                Prochaine étape : la lettre de motivation qui va avec, rédigée à partir de ce CV et de l'offre.
              </p>
              <div className="adapt-actions">
                <Button type="button" onClick={() => setLetterOpen(true)} disabled={busy}>
                  <PenLine size={15} /> Écrire la lettre de motivation
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate(`/builder/${createdCV.id}?step=edit`)}
                  disabled={busy}
                >
                  Ouvrir le CV adapté
                </Button>
              </div>
              {!referenceCv && (
                <p className="adapt-success-hint subtle">
                  <Star size={13} className="icon-inline" /> Astuce : définis un CV de référence (l'étoile sur ta carte CV) — il
                  sera présélectionné pour chaque nouvelle offre.
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {letterOpen && createdCV && (
        <CoverLetterModal cvId={createdCV.id} onClose={() => setLetterOpen(false)} />
      )}
    </section>
  );
}
