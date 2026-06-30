import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { Button } from "../components/Button";
import { CVPreview } from "../components/CVPreview";
import { CVLivePreview } from "../components/CVLivePreview";
import { cvsApi } from "../api/client";
import { Input } from "../components/Input";
import { useCVStore } from "../stores/cvStore";
import {
  createDefaultCVData,
  defaultEducation,
  defaultExperience,
  defaultExtraSection,
  defaultLanguage,
  normalizeCVData,
} from "../templates/cvData";
import { templateStyleLabel } from "../templates/templateLabels";
import "../styles/Builder.css";

const MAX_SOURCE_FILE_SIZE = 5 * 1024 * 1024;

const BASE_FLOW = [
  { id: "import", label: "Import" },
  { id: "analyze", label: "Analyse" },
  { id: "review", label: "Validation" },
  { id: "template", label: "Modèle" },
  { id: "edit", label: "Édition" },
  { id: "export", label: "Export" },
];

const STEP_ALIASES = {
  context: "import",
  ai: "analyze",
  payment: "access",
  cv: "edit",
  pdf: "export",
};

function buildFlow(paymentsEnforced) {
  if (!paymentsEnforced) return BASE_FLOW;
  return [
    ...BASE_FLOW.slice(0, 5),
    { id: "access", label: "Accès" },
    BASE_FLOW[5],
  ];
}

function statusLabel(cv) {
  if (!cv) return "Brouillon";
  if (cv.status === "generated") return "PDF prêt";
  if (cv.ai_status === "ready") return "Analysé";
  if (cv.ai_status === "processing") return "Analyse en cours";
  return "Brouillon";
}

function getFileName(value, fallback = "Aucun fichier choisi") {
  if (typeof value === "string" && value) return value.split("/").pop();
  return value?.name || fallback;
}

function listValue(items) {
  return (items || []).filter(Boolean).join("\n");
}

function splitLines(value) {
  return String(value || "")
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function templateImage(template) {
  return template?.preview_url || template?.thumbnail_url || template?.preview_image_url || "";
}

function sourceFileError(file) {
  if (!file) return "";
  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!isPdf) return "Importez un PDF uniquement.";
  if (file.size > MAX_SOURCE_FILE_SIZE) return "Le PDF ne doit pas dépasser 5 MB.";
  return "";
}

function PaymentPanel({ plans, access, cvId, onPay, busy, compact = false }) {
  const hasAccess = Boolean(access?.has_active_access);
  const paymentsEnabled = Boolean(access?.payments_enforced);
  const visiblePlans = plans.filter((plan) => plan.code !== "extra_ai" || access?.can_buy_extension);

  return (
    <section className={`payment-panel ${compact ? "payment-panel-compact" : ""}`}>
      <div className="panel-title-row">
        <div>
          <p className="eyebrow">Accès</p>
          <h2>{hasAccess ? "Accès actif" : "Débloquer l'export"}</h2>
        </div>
        {hasAccess && <span className="access-pill">Actif</span>}
      </div>

      {access && !access.payments_enforced && (
        <p className="soft-note">Mode test: paiement désactivé.</p>
      )}

      <div className="plan-grid">
        {visiblePlans.map((plan) => (
          <button
            type="button"
            key={plan.code}
            className="plan-card"
            onClick={() => onPay(plan.code, plan.code === "weekly" ? null : cvId)}
            disabled={busy || !paymentsEnabled || (!cvId && plan.code !== "weekly")}
          >
            <span>{plan.label}</span>
            <strong>{plan.amount_xof} F</strong>
            <small>{plan.description}</small>
          </button>
        ))}
      </div>
    </section>
  );
}

function TemplateChoice({ template, selected, onSelect }) {
  const image = templateImage(template);
  return (
    <button
      type="button"
      className={`template-choice ${selected ? "selected" : ""}`}
      onClick={() => onSelect(template)}
      aria-pressed={selected}
    >
      <span className="template-choice-preview">
        {image ? (
          <img src={image} alt={`Aperçu du modèle ${template.name}`} />
        ) : (
          <CVPreview template={template} compact />
        )}
      </span>
      <span className="template-choice-meta">
        <strong>{template.name}</strong>
        <small>{templateStyleLabel(template)}</small>
      </span>
    </button>
  );
}

function StepHint({ title, children }) {
  return (
    <div className="step-hint">
      <strong>{title}</strong>
      <span>{children}</span>
    </div>
  );
}

export function Builder() {
  const [searchParams] = useSearchParams();
  const templateId = searchParams.get("template");
  const requestedStep = STEP_ALIASES[searchParams.get("step")] || searchParams.get("step");
  const cvId = useParams().id;
  const navigate = useNavigate();

  const {
    templates,
    currentCV,
    plans,
    access,
    paymentsEnforced,
    error,
    fetchTemplates,
    fetchCV,
    fetchPlans,
    createCV,
    updateCV,
    uploadContext,
    improveCV,
    generateCV,
    downloadCV,
    initializePayment,
  } = useCVStore();

  const flow = useMemo(() => buildFlow(paymentsEnforced), [paymentsEnforced]);
  const initialStep = flow.some((item) => item.id === requestedStep) ? requestedStep : "import";

  const [activeStep, setActiveStep] = useState(initialStep);
  const [entryMode, setEntryMode] = useState("upload");
  const [title, setTitle] = useState("Mon CV");
  const [data, setData] = useState(() => createDefaultCVData());
  const [sourceFile, setSourceFile] = useState(null);
  const [photoFile, setPhotoFile] = useState(null);
  const [jobOfferUrl, setJobOfferUrl] = useState("");
  const [jobOfferText, setJobOfferText] = useState("");
  const [instruction, setInstruction] = useState("");
  const [selectedTemplateId, setSelectedTemplateId] = useState(templateId || "");
  const [templateChosen, setTemplateChosen] = useState(Boolean(templateId));
  const [busy, setBusy] = useState(false);
  const [paymentBusy, setPaymentBusy] = useState(false);
  const [localMessage, setLocalMessage] = useState("");
  const [rewrite, setRewrite] = useState({ loading: false, text: "", error: "" });
  const [correction, setCorrection] = useState({ loading: false, ready: false, error: "" });
  const correctedRef = useRef(null);

  const normalizedData = normalizeCVData(data);
  const effectiveCvId = cvId || currentCV?.id;
  const defaultTemplate = templates.find((template) => !template.is_premium) || templates[0];
  const currentTemplateId = selectedTemplateId || currentCV?.template || templateId || defaultTemplate?.id || "";
  const visibleTemplateId = templateChosen ? (selectedTemplateId || currentCV?.template || templateId) : "";
  const selectedTemplate =
    templates.find((template) => String(template.id) === String(visibleTemplateId)) ||
    (templateChosen ? currentCV?.template_detail : null);
  // Le mode est piloté par le CHOIX de l'utilisateur, pas forcé par un CV importé.
  const isUploadMode = entryMode === "upload";
  const hasSourceCV = isUploadMode && Boolean(sourceFile || currentCV?.source_file);
  const isGenerated = Boolean(currentCV?.generated_pdf || currentCV?.generated_file);
  const aiSummary = currentCV?.ai_data || {};
  const missingQuestions = Array.isArray(aiSummary.missing_info_questions) ? aiSummary.missing_info_questions : [];
  const changeLog = Array.isArray(aiSummary.change_log) ? aiSummary.change_log : [];
  const stepIndex = Math.max(0, flow.findIndex((item) => item.id === activeStep));
  const canShowTemplatePreview = Boolean(templateChosen && selectedTemplate);
  const previewImage = activeStep === "template" && canShowTemplatePreview ? templateImage(selectedTemplate) : "";

  useEffect(() => {
    fetchTemplates().catch(() => {});
  }, [fetchTemplates]);

  useEffect(() => {
    if (templateId) {
      setSelectedTemplateId(templateId);
      setTemplateChosen(true);
    }
  }, [templateId]);

  useEffect(() => {
    if (!flow.some((item) => item.id === activeStep)) {
      setActiveStep("import");
    }
  }, [activeStep, flow]);

  useEffect(() => {
    if (cvId) {
      fetchCV(cvId)
        .then((cv) => {
          if (cv?.data) setData(normalizeCVData(cv.data));
          if (cv?.title) setTitle(cv.title);
          setJobOfferUrl(cv?.job_offer_url || "");
          setJobOfferText(cv?.job_offer_text || "");
          if (cv?.source_file) setEntryMode("upload");
          if (cv?.template && (!requestedStep || ["template", "edit", "access", "export"].includes(requestedStep))) {
            setSelectedTemplateId(String(cv.template));
            setTemplateChosen(true);
          }
          if (!requestedStep) {
            if (cv?.status === "generated") setActiveStep("export");
            else if (cv?.ai_status === "ready") setActiveStep("edit");
            else if (cv?.source_file) setActiveStep("review");
            else setActiveStep("import");
          }
        })
        .catch(() => {});
      fetchPlans(cvId).catch(() => {});
    }
  }, [cvId, fetchCV, fetchPlans, requestedStep]);

  const pickTemplateId = async () => {
    if (currentTemplateId) return Number(currentTemplateId);
    const loadedTemplates = templates.length ? templates : await fetchTemplates();
    const fallback = loadedTemplates.find((template) => !template.is_premium) || loadedTemplates[0];
    if (!fallback?.id) {
      throw new Error("Aucun modèle disponible pour créer le CV.");
    }
    return fallback.id;
  };

  const ensureCV = async () => {
    if (effectiveCvId) return currentCV || { id: effectiveCvId };
    const template = await pickTemplateId();
    const created = await createCV(template, title || "Mon CV", normalizedData);
    fetchPlans(created.id).catch(() => {});
    return created;
  };

  const saveCurrentCV = async (overrides = {}) => {
    const cv = await ensureCV();
    const template = await pickTemplateId();
    return updateCV(cv.id, {
      template,
      title,
      data: normalizeCVData(data),
      job_offer_url: jobOfferUrl,
      job_offer_text: jobOfferText,
      template_mode: "selected",
      ...overrides,
    });
  };

  const saveImportContext = async () => {
    const saved = await saveCurrentCV();
    const targetCvId = saved?.id || effectiveCvId;
    const formData = new FormData();
    if (isUploadMode && sourceFile) formData.append("source_file", sourceFile);
    if (photoFile) formData.append("photo_file", photoFile);
    formData.append("job_offer_url", jobOfferUrl);
    formData.append("job_offer_text", jobOfferText);
    formData.append("template_mode", "selected");
    return uploadContext(targetCvId, formData);
  };

  const navigateToStep = (step, targetCvId = effectiveCvId) => {
    setActiveStep(step);
    if (targetCvId) navigate(`/builder/${targetCvId}?step=${step}`, { replace: true });
  };

  const chooseEntryMode = (mode) => {
    setEntryMode(mode);
    setLocalMessage("");
    if (mode === "manual") setSourceFile(null);
  };

  const handleSourceFile = (file) => {
    const message = sourceFileError(file);
    if (message) {
      setSourceFile(null);
      setLocalMessage(message);
      return;
    }
    setSourceFile(file || null);
    setLocalMessage("");
  };

  const updateField = (field, value) => {
    setData((current) => normalizeCVData({ ...current, [field]: value }));
  };

  const updateExperience = (index, field, value) => {
    setData((current) => {
      const next = normalizeCVData(current);
      next.experiences = next.experiences.map((item, itemIndex) => (
        itemIndex === index ? { ...item, [field]: value } : item
      ));
      return next;
    });
  };

  const updateExperienceMissions = (index, value) => {
    updateExperience(index, "missions", splitLines(value));
  };

  const updateEducation = (index, field, value) => {
    setData((current) => {
      const next = normalizeCVData(current);
      next.education = next.education.map((item, itemIndex) => (
        itemIndex === index ? { ...item, [field]: value } : item
      ));
      return next;
    });
  };

  const updateLanguage = (index, field, value) => {
    setData((current) => {
      const next = normalizeCVData(current);
      next.languages = next.languages.map((item, itemIndex) => (
        itemIndex === index ? { ...item, [field]: value } : item
      ));
      return next;
    });
  };

  const updateExtraSection = (index, field, value) => {
    setData((current) => {
      const next = normalizeCVData(current);
      next.extra_sections = next.extra_sections.map((item, itemIndex) => (
        itemIndex === index ? { ...item, [field]: value } : item
      ));
      return next;
    });
  };

  const updateExtraSectionItems = (index, value) => {
    updateExtraSection(index, "items", splitLines(value));
  };

  const addItem = (field, factory) => {
    setData((current) => {
      const next = normalizeCVData(current);
      next[field] = [...next[field], factory()];
      return next;
    });
  };

  const removeItem = (field, index) => {
    setData((current) => {
      const next = normalizeCVData(current);
      next[field] = next[field].filter((_, itemIndex) => itemIndex !== index);
      return next;
    });
  };

  const addExperience = () => addItem("experiences", defaultExperience);
  const addEducation = () => addItem("education", defaultEducation);
  const addLanguage = () => addItem("languages", defaultLanguage);
  const addExtraSection = () => addItem("extra_sections", defaultExtraSection);

  const runAnalysis = async () => {
    const saved = await saveImportContext();
    const targetCvId = saved?.id || effectiveCvId;
    const result = await improveCV(targetCvId, instruction);
    if (result?.cv?.data) setData(normalizeCVData(result.cv.data));
    setLocalMessage("CV analysé. Vérifiez les informations extraites avant le design.");
    navigateToStep("review", targetCvId);
    return result;
  };

  const handleNext = async () => {
    setLocalMessage("");
    setBusy(true);
    try {
      if (activeStep === "import") {
        if (isUploadMode && !hasSourceCV) {
          setLocalMessage("Importez votre CV PDF avant de lancer l'analyse.");
          return;
        }
        if (!photoFile && !currentCV?.photo_file) {
          setLocalMessage("Ajoutez une photo de profil : elle est obligatoire.");
          return;
        }
        const saved = await saveImportContext();
        navigateToStep(isUploadMode ? "analyze" : "edit", saved?.id || effectiveCvId);
        return;
      }
      if (activeStep === "analyze") {
        await runAnalysis();
        return;
      }
      if (activeStep === "review") {
        const saved = await saveCurrentCV();
        navigateToStep("template", saved?.id || effectiveCvId);
        return;
      }
      if (activeStep === "template") {
        if (!selectedTemplateId) {
          setLocalMessage("Choisissez un modèle pour continuer.");
          return;
        }
        const saved = await saveCurrentCV();
        navigateToStep("edit", saved?.id || effectiveCvId);
        return;
      }
      if (activeStep === "edit") {
        const saved = await saveCurrentCV();
        navigateToStep(paymentsEnforced ? "access" : "export", saved?.id || effectiveCvId);
        return;
      }
      if (activeStep === "access") {
        navigateToStep("export");
      }
    } catch (err) {
      if (err?.detail || err?.message) setLocalMessage(err.detail || err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleAnalyze = async () => {
    setLocalMessage("");
    setBusy(true);
    try {
      await runAnalysis();
    } catch (err) {
      if (err?.detail || err?.message) setLocalMessage(err.detail || err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleBack = () => {
    setLocalMessage("");
    setActiveStep(flow[Math.max(stepIndex - 1, 0)].id);
  };

  const handleTemplateSelect = async (template) => {
    setSelectedTemplateId(String(template.id));
    setTemplateChosen(true);
    setLocalMessage(`Modèle sélectionné: ${template.name}.`);
    if (!effectiveCvId) return;
    try {
      await updateCV(effectiveCvId, {
        template: template.id,
        title,
        data: normalizeCVData(data),
        job_offer_url: jobOfferUrl,
        job_offer_text: jobOfferText,
        template_mode: "selected",
      });
    } catch (err) {
      if (err?.detail || err?.message) setLocalMessage(err.detail || err.message);
    }
  };

  const handleGenerate = async () => {
    if (!effectiveCvId) return;
    setLocalMessage("");
    setBusy(true);
    try {
      await saveCurrentCV();
      const result = await generateCV(effectiveCvId);
      await downloadCV(effectiveCvId, title, "pdf");
      setLocalMessage(result?.warning || "PDF généré et téléchargé. 🎉");
    } catch (err) {
      if (err?.detail || err?.message) setLocalMessage(err.detail || err.message);
    } finally {
      setBusy(false);
    }
  };

  const handleWriteProfile = async () => {
    setRewrite({ loading: true, text: "", error: "" });
    try {
      const res = await cvsApi.writeProfile({ data: normalizeCVData(data), job_offer: jobOfferText });
      setRewrite({ loading: false, text: res.profile || "", error: "" });
    } catch (err) {
      setRewrite({ loading: false, text: "", error: err?.detail || "Indisponible pour le moment. Réessaie." });
    }
  };

  const handleCorrectAll = async () => {
    setCorrection({ loading: true, ready: false, error: "" });
    try {
      const res = await cvsApi.correct({ data: normalizeCVData(data) });
      correctedRef.current = res.data;
      setCorrection({ loading: false, ready: true, error: "" });
    } catch (err) {
      setCorrection({ loading: false, ready: false, error: err?.detail || "Correction indisponible. Réessaie." });
    }
  };

  const applyCorrection = () => {
    if (correctedRef.current) {
      setData(normalizeCVData({ ...normalizeCVData(data), ...correctedRef.current }));
    }
    correctedRef.current = null;
    setCorrection({ loading: false, ready: false, error: "" });
    setLocalMessage("Corrections appliquées ✓");
  };

  const handleDownload = async (format = "pdf") => {
    if (!effectiveCvId) return;
    setLocalMessage("");
    setBusy(true);
    try {
      await downloadCV(effectiveCvId, title, format);
    } catch (err) {
      if (err?.detail || err?.message) setLocalMessage(err.detail || err.message);
    } finally {
      setBusy(false);
    }
  };

  const handlePayment = async (planType, targetCvId) => {
    setPaymentBusy(true);
    setLocalMessage("");
    try {
      const result = await initializePayment(planType, targetCvId);
      if (result.authorization_url) {
        window.location.href = result.authorization_url;
        return;
      }
      setLocalMessage("Paiement initialisé, mais aucune URL Paystack n'a été retournée.");
    } catch (err) {
      if (err?.detail || err?.message) setLocalMessage(err.detail || err.message);
    } finally {
      setPaymentBusy(false);
    }
  };

  const coreFields = (
    <>
      <div className="field-grid two">
        <Input label="Prénom" value={normalizedData.first_name} onChange={(value) => updateField("first_name", value)} name="first_name" />
        <Input label="Nom" value={normalizedData.last_name} onChange={(value) => updateField("last_name", value)} name="last_name" />
      </div>
      <Input label="Poste ciblé" value={normalizedData.job_title} onChange={(value) => updateField("job_title", value)} name="job_title" />
      <div className="field-grid two">
        <Input label="Téléphone" value={normalizedData.phone} onChange={(value) => updateField("phone", value)} name="phone" />
        <Input label="Email" value={normalizedData.email} onChange={(value) => updateField("email", value)} name="email" />
      </div>
      <Input label="Ville / adresse" value={normalizedData.address} onChange={(value) => updateField("address", value)} name="address" />
      <Input label="LinkedIn" value={normalizedData.linkedin} onChange={(value) => updateField("linkedin", value)} name="linkedin" />
      <div className="field-grid two">
        <Input label="GitHub" value={normalizedData.github} onChange={(value) => updateField("github", value)} name="github" />
        <Input label="Portfolio" value={normalizedData.portfolio} onChange={(value) => updateField("portfolio", value)} name="portfolio" />
      </div>
      <div className="form-group">
        <div className="label-row">
          <label htmlFor="profile">Profil</label>
          <button type="button" className="rewrite-btn" onClick={handleWriteProfile} disabled={rewrite.loading}>
            {rewrite.loading
              ? "Rédaction…"
              : (normalizedData.profile || "").trim()
                ? "✨ Corriger"
                : "✨ Rédiger le profil"}
          </button>
        </div>
        <textarea id="profile" rows={5} value={normalizedData.profile} onChange={(event) => updateField("profile", event.target.value)} />
        {rewrite.error && <span className="form-error">{rewrite.error}</span>}
        {rewrite.text && (
          <div className="rewrite-proposal">
            <p className="rewrite-proposal-label">Version plus courte proposée</p>
            <p className="rewrite-proposal-text">{rewrite.text}</p>
            <div className="rewrite-proposal-actions">
              <Button
                type="button"
                onClick={() => {
                  updateField("profile", rewrite.text);
                  setRewrite({ loading: false, text: "", error: "" });
                }}
              >
                Remplacer
              </Button>
              <Button type="button" variant="outline" onClick={() => setRewrite({ loading: false, text: "", error: "" })}>
                Garder l'actuel
              </Button>
            </div>
          </div>
        )}
      </div>
    </>
  );

  const editorFields = (
    <>
      {coreFields}

      <div className="edit-block-list">
        <div className="section-title-row">
          <h3>Expériences</h3>
          <Button type="button" variant="outline" onClick={addExperience}>Ajouter</Button>
        </div>
        {normalizedData.experiences.map((exp, index) => (
          <article key={index} className="edit-block">
            <div className="section-title-row small">
              <strong>Expérience {index + 1}</strong>
              <Button type="button" variant="outline" onClick={() => removeItem("experiences", index)}>Retirer</Button>
            </div>
            <Input label="Poste" value={exp.job_title} onChange={(value) => updateExperience(index, "job_title", value)} />
            <Input label="Entreprise" value={exp.company} onChange={(value) => updateExperience(index, "company", value)} />
            <div className="field-grid two">
              <Input label="Lieu" value={exp.location} onChange={(value) => updateExperience(index, "location", value)} />
              <Input label="Période" value={exp.period} onChange={(value) => updateExperience(index, "period", value)} />
            </div>
            <div className="form-group">
              <label>Missions, une par ligne</label>
              <textarea rows={4} value={listValue(exp.missions)} onChange={(event) => updateExperienceMissions(index, event.target.value)} />
            </div>
          </article>
        ))}
      </div>

      <div className="edit-block-list">
        <div className="section-title-row">
          <h3>Formation</h3>
          <Button type="button" variant="outline" onClick={addEducation}>Ajouter</Button>
        </div>
        {normalizedData.education.map((edu, index) => (
          <article key={index} className="edit-block">
            <div className="section-title-row small">
              <strong>Formation {index + 1}</strong>
              <Button type="button" variant="outline" onClick={() => removeItem("education", index)}>Retirer</Button>
            </div>
            <Input label="Diplôme" value={edu.degree} onChange={(value) => updateEducation(index, "degree", value)} />
            <Input label="Établissement" value={edu.institution} onChange={(value) => updateEducation(index, "institution", value)} />
            <div className="field-grid two">
              <Input label="Lieu" value={edu.location} onChange={(value) => updateEducation(index, "location", value)} />
              <Input label="Période" value={edu.period} onChange={(value) => updateEducation(index, "period", value)} />
            </div>
          </article>
        ))}
      </div>

      <div className="field-grid two">
        <div className="form-group">
          <label>Compétences, une par ligne</label>
          <textarea rows={6} value={listValue(normalizedData.skills)} onChange={(event) => updateField("skills", splitLines(event.target.value))} />
        </div>
        <div className="form-group">
          <label>Loisirs, un par ligne</label>
          <textarea rows={6} value={listValue(normalizedData.hobbies)} onChange={(event) => updateField("hobbies", splitLines(event.target.value))} />
        </div>
      </div>

      <div className="edit-block-list">
        <div className="section-title-row">
          <h3>Langues</h3>
          <Button type="button" variant="outline" onClick={addLanguage}>Ajouter</Button>
        </div>
        {normalizedData.languages.map((lang, index) => (
          <article key={index} className="language-row">
            <Input label="Langue" value={lang.language} onChange={(value) => updateLanguage(index, "language", value)} />
            <Input label="Niveau" value={lang.level} onChange={(value) => updateLanguage(index, "level", value)} />
            <Button type="button" variant="outline" onClick={() => removeItem("languages", index)}>Retirer</Button>
          </article>
        ))}
      </div>

      <div className="edit-block-list">
        <div className="section-title-row">
          <h3>Sections personnalisées</h3>
          <Button type="button" variant="outline" onClick={addExtraSection}>Ajouter une section</Button>
        </div>
        {normalizedData.extra_sections.map((section, index) => (
          <article key={index} className="edit-block">
            <div className="section-title-row small">
              <strong>Section {index + 1}</strong>
              <Button type="button" variant="outline" onClick={() => removeItem("extra_sections", index)}>Retirer</Button>
            </div>
            <Input label="Titre de section" value={section.title} onChange={(value) => updateExtraSection(index, "title", value)} />
            <div className="form-group">
              <label>Contenu, une ligne par élément</label>
              <textarea rows={5} value={listValue(section.items)} onChange={(event) => updateExtraSectionItems(index, event.target.value)} />
            </div>
          </article>
        ))}
      </div>
    </>
  );

  return (
    <div className="builder-mobile-page">
      <div className="builder-topbar">
        <div>
          <p className="eyebrow">Mon CV</p>
          <h1>Créer mon CV</h1>
          <span>Suis les étapes, ton CV se construit en direct.</span>
        </div>
        <Link className="quiet-link" to="/dashboard">Mes CV</Link>
      </div>

      <nav className="mobile-flow" aria-label="Étapes du CV">
        {flow.map((item, index) => (
          <button
            type="button"
            key={item.id}
            className={`flow-pill ${item.id === activeStep ? "current" : ""} ${index < stepIndex ? "done" : ""}`}
            onClick={() => setActiveStep(item.id)}
          >
            <span>{index + 1}</span>
            {item.label}
          </button>
        ))}
      </nav>

      {(error || localMessage) && (
        <div className={`builder-alert ${error ? "error" : "success"}`}>{error || localMessage}</div>
      )}

      <div className="builder-layout">
        <main className="builder-main-panel">
          {activeStep === "import" && (
            <section className="flow-section">
              <p className="eyebrow">Étape 1</p>
              <h2>Par où commencer ?</h2>
              <p className="section-copy">
                Importe un PDF pour remplir automatiquement, ou pars de zéro. Une photo est obligatoire.
              </p>

              <div className="mode-switch" aria-label="Méthode de création">
                <button type="button" className={isUploadMode ? "active" : ""} onClick={() => chooseEntryMode("upload")}>
                  Import PDF
                </button>
                <button type="button" className={entryMode === "manual" ? "active" : ""} onClick={() => chooseEntryMode("manual")}>
                  Saisie manuelle
                </button>
              </div>

              <Input label="Titre du CV" value={title} onChange={setTitle} name="title" />

              <div className="upload-grid">
                {isUploadMode && (
                  <label className="upload-box required">
                    <span>CV PDF</span>
                    <strong>{currentCV?.source_file ? "PDF déjà importé" : getFileName(sourceFile)}</strong>
                    <small>PDF uniquement, 5 MB maximum</small>
                    <input type="file" accept="application/pdf,.pdf" onChange={(event) => handleSourceFile(event.target.files?.[0] || null)} />
                  </label>
                )}

                <label className="upload-box required">
                  <span>Photo de profil *</span>
                  <strong>{photoFile ? getFileName(photoFile) : (currentCV?.photo_file ? "Photo ajoutée ✓" : "Obligatoire")}</strong>
                  <small>Obligatoire. JPG, PNG ou WebP — recadrée automatiquement en photo CV.</small>
                  <input type="file" accept="image/*" onChange={(event) => setPhotoFile(event.target.files?.[0] || null)} />
                </label>
              </div>
            </section>
          )}

          {activeStep === "analyze" && (
            <section className="flow-section">
              <p className="eyebrow">Étape 2</p>
              <h2>Lire ton CV</h2>
              <p className="section-copy">
                On lit ton PDF et on remplit les champs automatiquement.
              </p>

              {busy && (
                <div className="extract-loading" role="status" aria-live="polite">
                  <span className="spinner" aria-hidden="true" />
                  <strong>Lecture de ton CV en cours…</strong>
                  <p>Quelques secondes. On extrait toutes tes informations.</p>
                </div>
              )}

              <div className="analysis-board" hidden={busy}>
                <StepHint title="Source">
                  {hasSourceCV ? getFileName(sourceFile, "PDF déjà importé") : "Aucun PDF importé."}
                </StepHint>
                <StepHint title="Résultat attendu">
                  Un CV structuré à vérifier avant le choix du design.
                </StepHint>
                <StepHint title="Lecture renforcée">
                  Les scans sont lus par OCR local quand le moteur est installé.
                </StepHint>
              </div>
              <div className="form-group">
                <label htmlFor="instruction">Compléments à ajouter pendant l'analyse</label>
                <textarea
                  id="instruction"
                  rows={5}
                  value={instruction}
                  onChange={(event) => setInstruction(event.target.value)}
                  placeholder="Ex: ajoute une section Projets, garde le ton professionnel, cible un poste React/Django."
                />
              </div>
              <Button type="button" onClick={handleAnalyze} disabled={busy || !hasSourceCV}>
                {busy ? "Analyse..." : "Analyser le PDF"}
              </Button>
            </section>
          )}

          {activeStep === "review" && (
            <section className="flow-section">
              <p className="eyebrow">Étape 3</p>
              <h2>Vérifie tes informations</h2>
              <div className="review-notice">
                <span aria-hidden="true">⚠️</span>
                <p>
                  <strong>Relis bien chaque champ.</strong> La lecture automatique peut sauter ou mal écrire un mot.
                  Corrige et complète ce qui manque avant de continuer.
                </p>
              </div>

              <div className="review-grid">
                <div className="review-metric">
                  <span>Expériences</span>
                  <strong>{normalizedData.experiences.length}</strong>
                </div>
                <div className="review-metric">
                  <span>Formations</span>
                  <strong>{normalizedData.education.length}</strong>
                </div>
                <div className="review-metric">
                  <span>Compétences</span>
                  <strong>{normalizedData.skills.length}</strong>
                </div>
              </div>

              {(aiSummary.fit_summary || missingQuestions.length > 0 || changeLog.length > 0) && (
                <div className="ai-result-box">
                  {aiSummary.fit_summary && <p>{aiSummary.fit_summary}</p>}
                  {missingQuestions.length > 0 && (
                    <div>
                      <strong>Points à compléter</strong>
                      <ul>{missingQuestions.map((item, index) => <li key={index}>{item}</li>)}</ul>
                    </div>
                  )}
                  {changeLog.length > 0 && (
                    <div>
                      <strong>Modifications</strong>
                      <ul>{changeLog.map((item, index) => <li key={index}>{item}</li>)}</ul>
                    </div>
                  )}
                </div>
              )}

              <div className="review-fields">
                {coreFields}
              </div>
            </section>
          )}

          {activeStep === "template" && (
            <section className="flow-section">
              <p className="eyebrow">Modèle</p>
              <h2>Choisissez le rendu final</h2>
              <p className="section-copy">
                Le modèle change le design, pas les informations extraites. Vous pourrez encore modifier le contenu ensuite.
              </p>
              <div className="template-picker-grid">
                {templates.map((template) => (
                  <TemplateChoice
                    key={template.id}
                    template={template}
                    selected={String(template.id) === String(selectedTemplateId)}
                    onSelect={handleTemplateSelect}
                  />
                ))}
              </div>
            </section>
          )}

          {activeStep === "edit" && (
            <section className="flow-section">
              <p className="eyebrow">Étape 4</p>
              <h2>Complète et corrige</h2>
              <p className="section-copy">Remplis tes infos. L'IA peut rédiger ton profil et corriger les fautes.</p>

              <details className="offer-box">
                <summary>🎯 Adapter à une offre <span>(optionnel)</span></summary>
                <p className="offer-hint">Colle l'offre d'emploi visée : « Rédiger le profil » l'orientera vers ce poste.</p>
                <textarea
                  rows={4}
                  value={jobOfferText}
                  onChange={(event) => setJobOfferText(event.target.value)}
                  placeholder="Colle ici le texte de l'offre d'emploi…"
                />
              </details>

              <div className="correct-bar">
                <button type="button" className="btn btn-primary correct-all-btn" onClick={handleCorrectAll} disabled={correction.loading}>
                  {correction.loading ? "Correction en cours…" : "✨ Corriger tout le CV"}
                </button>
                <small>Fautes, accents, périodes (ex : « 2025 À 2026 » → « 2025 - 2026 »). Rien n'est supprimé.</small>
              </div>
              {correction.error && <p className="form-error global">{correction.error}</p>}
              {correction.ready && (
                <div className="rewrite-proposal">
                  <p className="rewrite-proposal-label">Corrections prêtes</p>
                  <p className="rewrite-proposal-text">L'IA a corrigé l'orthographe, les accents et le format des dates. Aucune information n'a été retirée.</p>
                  <div className="rewrite-proposal-actions">
                    <Button type="button" onClick={applyCorrection}>Appliquer les corrections</Button>
                    <Button type="button" variant="outline" onClick={() => setCorrection({ loading: false, ready: false, error: "" })}>Annuler</Button>
                  </div>
                </div>
              )}

              {editorFields}
            </section>
          )}

          {paymentsEnforced && activeStep === "access" && (
            <PaymentPanel plans={plans} access={access} cvId={effectiveCvId} onPay={handlePayment} busy={paymentBusy} />
          )}

          {activeStep === "export" && (
            <section className="flow-section">
              <p className="eyebrow">Export</p>
              <h2>Télécharger le CV</h2>
              <p className="section-copy">Générez le PDF après validation. Le DOCX reste disponible après génération.</p>
              {paymentsEnforced && (
                <PaymentPanel plans={plans} access={access} cvId={effectiveCvId} onPay={handlePayment} busy={paymentBusy} compact />
              )}
              <div className="export-actions">
                <Button type="button" onClick={handleGenerate} disabled={busy}>
                  {busy ? "Génération..." : "Générer et télécharger PDF"}
                </Button>
                {isGenerated && (
                  <>
                    <Button type="button" variant="outline" onClick={() => handleDownload("pdf")} disabled={busy}>Télécharger PDF</Button>
                    <Button type="button" variant="outline" onClick={() => handleDownload("docx")} disabled={busy}>Télécharger DOCX</Button>
                  </>
                )}
              </div>
            </section>
          )}

          <div className="builder-nav-actions">
            <Button type="button" variant="outline" onClick={handleBack} disabled={stepIndex === 0 || busy}>Retour</Button>
            {activeStep !== "export" && activeStep !== "analyze" && (
              <Button type="button" onClick={handleNext} disabled={busy}>
                {busy ? "Enregistrement..." : "Continuer"}
              </Button>
            )}
          </div>
        </main>

        <aside className="preview-rail">
          {canShowTemplatePreview ? (
            <div className="preview-card-mobile">
              <div className="preview-head">
                <div>
                  <span>Aperçu</span>
                  <strong>{selectedTemplate.name}</strong>
                </div>
                <small>{statusLabel(currentCV)}</small>
              </div>
              {previewImage ? (
                <img
                  className="selected-template-preview-image"
                  src={previewImage}
                  alt={`Aperçu du modèle ${selectedTemplate.name}`}
                />
              ) : (
                <CVLivePreview templateId={selectedTemplate.id} data={normalizedData} />
              )}
            </div>
          ) : (
            <div className="process-panel">
              <strong>{activeStep === "template" ? "Choix du modèle" : "Préparation du CV"}</strong>
              <span>
                {activeStep === "template"
                  ? "Sélectionnez un modèle pour afficher l'aperçu."
                  : "L'aperçu du design apparaîtra après le choix du modèle."}
              </span>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
