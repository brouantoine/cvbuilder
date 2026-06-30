import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { useEffect } from "react";
import { Layout } from "./components/Layout";
import { Home } from "./pages/Home";
import { Login } from "./pages/Login";
import { Register } from "./pages/Register";
import { Dashboard } from "./pages/Dashboard";
import { Templates } from "./pages/Templates";
import { Builder } from "./pages/Builder";
import { useAuthStore } from "./stores/authStore";
import "./App.css";

function ProtectedRoute({ children }) {
  const { access, initialized, loading } = useAuthStore();
  if (!initialized || loading) return <p className="loading">Vérification de la session…</p>;
  if (!access) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  const { loadUser, logout } = useAuthStore();
  useEffect(() => {
    loadUser();
    window.addEventListener("auth:unauthorized", logout);
    return () => window.removeEventListener("auth:unauthorized", logout);
  }, [loadUser, logout]);

  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard /> 
              </ProtectedRoute>
            }
          />
          <Route
            path="/templates"
            element={
              <ProtectedRoute>
                <Templates />
              </ProtectedRoute>
            }
          />
          <Route
            path="/builder"
            element={
              <ProtectedRoute>
                <Builder />
              </ProtectedRoute>
            }
          />
          <Route
            path="/builder/:id"
            element={
              <ProtectedRoute>
                <Builder />
              </ProtectedRoute>
            }
          />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
