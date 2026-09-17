import { Button } from "./Button";
import { CheckCircle2, Lightbulb } from "lucide-react";

const VERDICTS = {
  bonne_correspondance: { label: "Bonne correspondance", tone: "good" },
  correspondance_partielle: { label: "Correspondance partielle", tone: "mid" },
  hors_profil: { label: "Offre hors profil", tone: "bad" },
};

/**
 * Propositions d'adaptation en miroir : verdict franc, puis pour chaque champ
 * le texte actuel face au texte proposé avec la raison orientée recruteur.
 * « Remplacer » applique tout dans les champs du CV ; « Ignorer » ferme.
 */
export function AdaptProposal({ report, busy, onReplace, onDismiss }) {
  if (!report) return null;
  const verdict = VERDICTS[report.verdict] || VERDICTS.correspondance_partielle;
  const changes = report.changes || [];
  const isMismatch = report.verdict === "hors_profil";

  return (
    <div className="adapt-proposal">
      <div className={`adapt-verdict ${verdict.tone}`}>
        <strong>
          {verdict.label}
          {Number.isFinite(report.score) ? ` · ${report.score}%` : ""}
        </strong>
        <p>{report.resume}</p>
      </div>

      {!isMismatch && changes.length > 0 && (
        <div className="adapt-changes">
          {changes.map((change, index) => (
            <div className="adapt-change" key={index}>
              <p className="adapt-change-field">{change.champ}</p>
              <div className="adapt-mirror">
                <div className="adapt-side current">
                  <span>Actuel</span>
                  <p>{change.actuel || "—"}</p>
                </div>
                <div className="adapt-side proposed">
                  <span>Proposé</span>
                  <p>{change.propose}</p>
                </div>
              </div>
              <p className="adapt-reason"><Lightbulb size={14} className="icon-inline" /> {change.raison}</p>
            </div>
          ))}
        </div>
      )}

      {!isMismatch && changes.length > 0 && (
        <p className="adapt-keep-note">Ton CV original reste intact : l'adaptation crée un nouveau CV dans ton espace, titré avec le poste visé.</p>
      )}
      <div className="adapt-actions">
        {!isMismatch && changes.length > 0 && (
          <Button type="button" onClick={onReplace} disabled={busy}>
            {busy ? "Création du CV adapté…" : <><CheckCircle2 size={16} /> Créer le CV adapté</>}
          </Button>
        )}
        <Button type="button" variant="outline" onClick={onDismiss} disabled={busy}>
          {isMismatch ? "Fermer" : "Ignorer"}
        </Button>
      </div>
    </div>
  );
}
