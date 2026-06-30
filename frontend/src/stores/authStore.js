import { create } from "zustand";
import { persist } from "zustand/middleware";
import { authApi } from "../api/client";

export const useAuthStore = create(
  persist(
    (set) => ({
      user: null,
      access: null,
      refresh: null,
      loading: false,
      initialized: false,
      error: null,

      setTokens: (access, refresh) => {
        if (access) localStorage.setItem("access", access);
        if (refresh) localStorage.setItem("refresh", refresh);
        set({ access, refresh });
      },

      login: async (username, password) => {
        set({ loading: true, error: null });
        try {
          const data = await authApi.login({ username, password });
          if (data.access) localStorage.setItem("access", data.access);
          if (data.refresh) localStorage.setItem("refresh", data.refresh);
          const user = await authApi.me().catch(() => ({ username }));
          set({
            user,
            access: data.access,
            refresh: data.refresh,
            loading: false,
            initialized: true,
            error: null,
          });
          return data;
        } catch (err) {
          set({
            loading: false,
            initialized: true,
            error: err.detail || err.username?.[0] || "Erreur de connexion",
          });
          throw err;
        }
      },

      register: async (username, email, password, password_confirm) => {
        set({ loading: true, error: null });
        try {
          const data = await authApi.register({
            username,
            email,
            password,
            password_confirm,
          });
          set({
            user: data.user,
            access: data.access,
            refresh: data.refresh,
            loading: false,
            initialized: true,
            error: null,
          });
          if (data.access) localStorage.setItem("access", data.access);
          if (data.refresh) localStorage.setItem("refresh", data.refresh);
          return data;
        } catch (err) {
          const msg =
            err.email?.[0] ||
            err.username?.[0] ||
            err.password_confirm?.[0] ||
            err.detail ||
            "Erreur d'inscription";
          set({ loading: false, initialized: true, error: msg });
          throw err;
        }
      },

      logout: () => {
        localStorage.removeItem("access");
        localStorage.removeItem("refresh");
        localStorage.removeItem("auth");
        set({ user: null, access: null, refresh: null, loading: false, initialized: true });
      },

      loadUser: async () => {
        const access = localStorage.getItem("access");
        if (!access) {
          set({ access: null, user: null, loading: false, initialized: true });
          return null;
        }

        set({ access, loading: true });
        try {
          const user = await authApi.me();
          set({ user, loading: false, initialized: true, error: null });
          return user;
        } catch {
          localStorage.removeItem("access");
          localStorage.removeItem("refresh");
          localStorage.removeItem("auth");
          set({ user: null, access: null, refresh: null, loading: false, initialized: true });
          return null;
        }
      },
    }),
    { name: "auth", partialize: (s) => ({ access: s.access, refresh: s.refresh, user: s.user }) }
  )
);
