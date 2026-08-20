import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { HOME_POR_PAPEL } from "./auth/types";
import { Layout } from "./components/Layout";
import { Carregando } from "./components/Carregando";
import { Entrar } from "./pages/Entrar";
import { CriarConta } from "./pages/CriarConta";
import { EmBreve } from "./pages/EmBreve";

/** A raiz manda cada um para a própria área; quem não entrou, para o login. */
function Raiz() {
  const { user, carregando } = useAuth();
  if (carregando) return <Carregando />;
  return <Navigate to={user ? HOME_POR_PAPEL[user.role] : "/entrar"} replace />;
}

function NaoEncontrado() {
  return (
    <section className="stack" style={{ gap: "var(--space-4)", maxWidth: "50ch" }}>
      <h1>Página não encontrada</h1>
      <p className="muted">O endereço acessado não existe ou foi movido.</p>
    </section>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<Raiz />} />
          <Route path="/entrar" element={<Entrar />} />
          <Route path="/criar-conta" element={<CriarConta />} />

          <Route element={<Layout />}>
            <Route
              path="/organizador"
              element={
                <ProtectedRoute permitido={["ORGANIZER"]}>
                  <EmBreve
                    titulo="Painel do organizador"
                    descricao="Aqui você vai buscar filmes no catálogo e publicar sessões, definindo data, sala, preço e capacidade."
                    sprint="Sprint 2"
                  />
                </ProtectedRoute>
              }
            />

            <Route
              path="/eventos"
              element={
                <ProtectedRoute permitido={["CUSTOMER"]}>
                  <EmBreve
                    titulo="Sessões em cartaz"
                    descricao="Aqui você vai navegar pelas sessões publicadas, escolher o assento e comprar o ingresso."
                    sprint="Sprints 2 e 3"
                  />
                </ProtectedRoute>
              }
            />

            <Route
              path="/portaria"
              element={
                <ProtectedRoute permitido={["GATE"]}>
                  <EmBreve
                    titulo="Portaria"
                    descricao="Aqui você vai ler o QR do ingresso pela câmera, ou digitar o código, e receber de volta se ele é válido."
                    sprint="Sprint 4"
                  />
                </ProtectedRoute>
              }
            />

            <Route path="*" element={<NaoEncontrado />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
