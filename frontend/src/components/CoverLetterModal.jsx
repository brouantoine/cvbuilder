import { useCallback, useEffect, useRef, useState } from "react";
import { Check, Copy, Download, PenLine, RefreshCw, X } from "lucide-react";
import { cvsApi } from "../api/client";
import { Button } from "./Button";
import "../styles/CoverLetterModal.css";

function saveBlob({ blob, filename }, fallbackName) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename || fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/**
 * Lettre de motivation d'un CV : rédigée par l'agent IA à partir du CV adapté
 * et de l'offre, puis librement éditable. « Régénérer » accepte une consigne
 * (ton, point à souligner…) ; le PDF reprend la palette du modèle du CV.
 */
export function CoverLetterModal({ cvId, onClose }) {
  const [letter, setLetter] = useState("");
  const [savedLetter, setSavedLetter] = useState("");
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState(false);
  const [busyLabel, setBusyLabel] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  // Offre mémorisée sur le CV (texte extrait des captures/PDF, lien ou fichier) :
  // c'est elle que l'agent utilise pour personnaliser la lettre à l'entreprise.
  const [offer, setOffer] = useState(null);
  const [copied, setCopied] = useState(false);
  const textRef = useRef(null);

  const generate = useCallback(
    async (hint = "") => {
      setBusy(true);
      setBusyLabel("Rédaction de ta lettre… (jusqu'à 1 min)");
      setError("");
      setNotice("");
      try {
        const res = await cvsApi.writeCoverLetter(cvId, hint ? { instruction: hint } : {});
        setLetter(res.letter || "");
        setSavedLetter(res.letter || "");
        setNotice("Lettre rédigée. Relis-la, ajuste-la si besoin, puis télécharge le PDF.");
      } catch (err) {
        setError(err?.detail || err?.message || "Rédaction impossible pour le moment. Réessaie.");
      } finally {
        setBusy(false);
        setBusyLabel("");
      }
    },
    [cvId]
  );

  // À l'ouverture : charge l'offre mémorisée + la lettre existante ;
  // s'il n'y a pas encore de lettre mais une offre, la rédige directement.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setBusy(true);
      setBusyLabel("Chargement…");
      try {
        const cv = await cvsApi.get(cvId);
        if (cancelled) return;
        const offerInfo = {
          text: (cv.job_offer_text || "").trim(),
          url: cv.job_offer_url || "",
          hasFile: Boolean(cv.job_offer_file),
        };
        const hasOffer = Boolean(offerInfo.text || offerInfo.url || offerInfo.hasFile);
        setOffer(hasOffer ? offerInfo : null);
        if ((cv.cover_letter || "").trim()) {
          setLetter(cv.cover_letter);
          setSavedLetter(cv.cover_letter);
          setBusy(false);
          setBusyLabel("");
        } else if (hasOffer) {
          await generate();
        } else {
          setError(
            "Aucune offre mémorisée sur ce CV : adapte-le d'abord à une offre (texte, capture ou lien) — " +
              "l'agent s'en sert pour personnaliser la lettre à l'entreprise."
          );
          setBusy(false);
          setBusyLabel("");
        }
      } catch {
        if (!cancelled) {
          setError("Impossible de charger ce CV. Réessaie.");
          setBusy(false);
          setBusyLabel("");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [cvId, generate]);

  const persistIfEdited = async () => {
    if (letter === savedLetter) return;
    await cvsApi.update(cvId, { cover_letter: letter });
    setSavedLetter(letter);
  };

  const handleSave = async () => {
    setBusy(true);
    setError("");
    try {
      await persistIfEdited();
      setNotice("Lettre enregistrée.");
    } catch (err) {
      setError(err?.detail || "Enregistrement impossible. Réessaie.");
    } finally {
      setBusy(false);
    }
  };

  // Copie la lettre telle quelle, prête à coller dans un email ou un
  // formulaire de candidature.
  const handleCopy = async () => {
    if (!letter.trim()) return;
    try {
      await navigator.clipboard.writeText(letter);
    } catch {
      // Repli (contexte non sécurisé / vieux navigateur) : sélection + copie.
      const node = textRef.current;
      if (node) {
        node.focus();
        node.select();
        document.execCommand("copy");
        node.setSelectionRange(node.value.length, node.value.length);
      }
    }
    setCopied(true);
    setNotice("");
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = async () => {
    setBusy(true);
    setBusyLabel("Préparation du PDF…");
    setError("");
    try {
      await persistIfEdited();
      const file = await cvsApi.downloadCoverLetter(cvId);
      saveBlob(file, "lettre-motivation.pdf");
    } catch (err) {
      setError(err?.detail || "Téléchargement impossible. Réessaie.");
    } finally {
      setBusy(false);
      setBusyLabel("");
    }
  };

  return (
    <>
      <div className="modal-overlay" onClick={busy ? undefined : onClose} role="presentation" />
      <div className="letter-modal" role="dialog" aria-label="Lettre de motivation">
        <div className="letter-modal-head">
          <div>
            <strong><PenLine size={16} className="icon-inline" /> Lettre de motivation</strong>
            <span>Basée sur ton CV et l'offre — courte, humaine, sans exagération. Tu peux tout modifier.</span>
          </div>
          <button type="button" className="letter-modal-close" onClick={onClose} aria-label="Fermer">
            <X size={18} />
          </button>
        </div>

        {offer && (
          <details className="letter-modal-offer">
            <summary>
              Offre mémorisée ✓ — l'agent s'en sert pour personnaliser la lettre à l'entreprise
            </summary>
            {offer.text ? (
              <p className="letter-modal-offer-text">
                {offer.text.slice(0, 600)}
                {offer.text.length > 600 ? "…" : ""}
              </p>
            ) : (
              <p className="letter-modal-offer-text">
                {offer.hasFile ? "Offre fournie en pièce jointe (capture/PDF)." : `Offre fournie via un lien : ${offer.url}`}
              </p>
            )}
          </details>
        )}

        {busy && busyLabel && <p className="letter-modal-busy">{busyLabel}</p>}
        {error && <p className="form-error global">{error}</p>}
        {notice && !error && !busy && <p className="letter-modal-notice">{notice}</p>}

        <textarea
          ref={textRef}
          className="letter-modal-text"
          value={letter}
          onChange={(event) => setLetter(event.target.value)}
          placeholder="Ta lettre apparaîtra ici…"
          disabled={busy}
          rows={16}
        />

        <label className="letter-modal-instruction">
          <span>Consigne pour la régénération (optionnel)</span>
          <input
            type="text"
            value={instruction}
            onChange={(event) => setInstruction(event.target.value)}
            placeholder="Ex. : insiste sur mon expérience chez Zenova, ton un peu plus direct…"
            disabled={busy}
          />
        </label>

        <div className="letter-modal-actions">
          <div className="letter-modal-actions-left">
            <Button
              type="button"
              variant="outline"
              className={copied ? "letter-copied" : ""}
              onClick={handleCopy}
              disabled={busy || !letter.trim()}
            >
              {copied ? <><Check size={15} /> Copié ✓</> : <><Copy size={15} /> Copier</>}
            </Button>
            <Button type="button" variant="outline" onClick={() => generate(instruction.trim())} disabled={busy || !offer}>
              <RefreshCw size={15} /> Régénérer
            </Button>
            {letter !== savedLetter && (
              <Button type="button" variant="outline" onClick={handleSave} disabled={busy}>
                Enregistrer
              </Button>
            )}
          </div>
          <Button type="button" onClick={handleDownload} disabled={busy || !letter.trim()}>
            <Download size={15} /> Télécharger le PDF
          </Button>
        </div>
      </div>
    </>
  );
}
