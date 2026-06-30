import { create } from "zustand";
import { cvsApi, paymentsApi, templatesApi } from "../api/client";

function cvForList(existing, cv) {
  return {
    ...existing,
    ...cv,
    template_name: cv.template_name || cv.template_detail?.name || existing?.template_name,
  };
}

function fallbackFilename(title, format = "pdf") {
  const base = String(title || "cv")
    .trim()
    .replace(/[^a-z0-9]+/gi, "_")
    .replace(/^_+|_+$/g, "")
    .toLowerCase();
  return `${base || "cv"}.${format}`;
}

function saveBlob({ blob, filename }, title, format = "pdf") {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename || fallbackFilename(title, format);
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function messageFromError(err, fallback) {
  if (err?.status === 401) return "Session expirée. Reconnectez-vous.";
  if (err?.status === 402) return err?.detail || "Paiement requis pour continuer.";
  return err?.detail || fallback;
}

export const useCVStore = create((set, get) => ({
  cvs: [],
  templates: [],
  currentCV: null,
  selectedTemplateId: null,
  plans: [],
  access: null,
  paystackPublicKey: "",
  paymentsEnforced: false,
  loading: false,
  error: null,

  fetchTemplates: async () => {
    set({ loading: true, error: null });
    try {
      const data = await templatesApi.list();
      set({ templates: Array.isArray(data) ? data : [], loading: false });
      return get().templates;
    } catch (err) {
      set({ loading: false, error: messageFromError(err, "Erreur chargement templates") });
      throw err;
    }
  },

  syncTemplateLibrary: async () => {
    set({ loading: true, error: null });
    try {
      const result = await templatesApi.syncLibrary();
      const data = await templatesApi.list();
      set({ templates: Array.isArray(data) ? data : [], loading: false });
      return result;
    } catch (err) {
      set({ loading: false, error: messageFromError(err, "Erreur synchronisation modèles") });
      throw err;
    }
  },

  fetchPlans: async (cvId) => {
    try {
      const data = await cvsApi.plans(cvId);
      set({
        plans: data.plans || [],
        access: data.access || null,
        paystackPublicKey: data.paystack_public_key || "",
        paymentsEnforced: Boolean(data.payments_enforced),
      });
      return data;
    } catch (err) {
      set({ error: messageFromError(err, "Erreur chargement paiements") });
      throw err;
    }
  },

  fetchCVs: async () => {
    set({ loading: true, error: null });
    try {
      const data = await cvsApi.list();
      set({ cvs: Array.isArray(data) ? data : [], loading: false });
      return get().cvs;
    } catch (err) {
      set({ loading: false, error: messageFromError(err, "Erreur chargement CVs") });
      throw err;
    }
  },

  fetchCV: async (id) => {
    set({ loading: true, error: null });
    try {
      const data = await cvsApi.get(id);
      set({ currentCV: data, loading: false });
      return data;
    } catch (err) {
      set({ loading: false, error: messageFromError(err, "CV introuvable") });
      throw err;
    }
  },

  selectTemplate: (id) => set({ selectedTemplateId: id }),
  setCurrentCV: (cv) => set({ currentCV: cv }),

  createCV: async (templateId, title = "Mon CV", data = {}) => {
    set({ loading: true, error: null });
    try {
      const created = await cvsApi.create({ template: templateId, title, data });
      set((s) => ({ cvs: [cvForList({}, created), ...s.cvs], currentCV: created, loading: false }));
      return created;
    } catch (err) {
      set({ loading: false, error: messageFromError(err, "Erreur création CV") });
      throw err;
    }
  },

  updateCV: async (id, body) => {
    set({ loading: true, error: null });
    try {
      const updated = await cvsApi.update(id, body);
      const cvId = Number(id);
      set((s) => ({
        cvs: s.cvs.map((c) => (c.id === cvId ? cvForList(c, updated) : c)),
        currentCV: s.currentCV?.id === cvId ? updated : s.currentCV,
        loading: false,
      }));
      return updated;
    } catch (err) {
      set({ loading: false, error: messageFromError(err, "Erreur mise à jour") });
      throw err;
    }
  },

  uploadContext: async (id, formData) => {
    set({ loading: true, error: null });
    try {
      const updated = await cvsApi.uploadContext(id, formData);
      const cvId = Number(id);
      set((s) => ({
        cvs: s.cvs.map((c) => (c.id === cvId ? cvForList(c, updated) : c)),
        currentCV: updated,
        loading: false,
      }));
      return updated;
    } catch (err) {
      set({ loading: false, error: messageFromError(err, "Erreur upload contexte") });
      throw err;
    }
  },

  improveCV: async (id, instruction = "") => {
    set({ loading: true, error: null });
    try {
      const result = await cvsApi.improve(id, { instruction });
      const updated = result.cv;
      const cvId = Number(id);
      set((s) => ({
        cvs: updated ? s.cvs.map((c) => (c.id === cvId ? cvForList(c, updated) : c)) : s.cvs,
        currentCV: updated || s.currentCV,
        access: result.access || s.access,
        loading: false,
      }));
      return result;
    } catch (err) {
      set((s) => ({ loading: false, error: messageFromError(err, "Erreur IA"), access: err?.access || s.access }));
      throw err;
    }
  },

  generateCV: async (id) => {
    set({ loading: true, error: null });
    try {
      const result = await cvsApi.generate(id);
      const generated = result.cv;
      const cvId = Number(id);
      set((s) => ({
        cvs: generated ? s.cvs.map((c) => (c.id === cvId ? cvForList(c, generated) : c)) : s.cvs,
        currentCV: generated && s.currentCV?.id === cvId ? generated : s.currentCV,
        loading: false,
      }));
      return result;
    } catch (err) {
      set((s) => ({ loading: false, error: messageFromError(err, "Erreur génération PDF"), access: err?.access || s.access }));
      throw err;
    }
  },

  duplicateCV: async (id) => {
    set({ loading: true, error: null });
    try {
      const duplicated = await cvsApi.duplicate(id);
      set((s) => ({ cvs: [cvForList({}, duplicated), ...s.cvs], currentCV: duplicated, loading: false }));
      return duplicated;
    } catch (err) {
      set({ loading: false, error: messageFromError(err, "Erreur duplication CV") });
      throw err;
    }
  },

  deleteCV: async (id) => {
    set({ loading: true, error: null });
    try {
      await cvsApi.remove(id);
      const cvId = Number(id);
      set((s) => ({
        cvs: s.cvs.filter((cv) => cv.id !== cvId),
        currentCV: s.currentCV?.id === cvId ? null : s.currentCV,
        loading: false,
      }));
      return true;
    } catch (err) {
      set({ loading: false, error: messageFromError(err, "Erreur suppression CV") });
      throw err;
    }
  },

  downloadCV: async (id, title, format = "pdf") => {
    set({ loading: true, error: null });
    try {
      const file = await cvsApi.download(id, format);
      saveBlob(file, title, format);
      set({ loading: false });
      return file;
    } catch (err) {
      set({ loading: false, error: messageFromError(err, "Erreur téléchargement") });
      throw err;
    }
  },

  initializePayment: async (planType, cvId) => {
    set({ loading: true, error: null });
    try {
      const result = await paymentsApi.initialize({ plan_type: planType, cv: cvId || null });
      set({ loading: false });
      return result;
    } catch (err) {
      set({ loading: false, error: messageFromError(err, "Erreur paiement") });
      throw err;
    }
  },

  verifyPayment: async (reference) => {
    set({ loading: true, error: null });
    try {
      const result = await paymentsApi.verify({ reference });
      set({ access: result.access || null, loading: false });
      return result;
    } catch (err) {
      set({ loading: false, error: messageFromError(err, "Erreur vérification paiement") });
      throw err;
    }
  },
}));
