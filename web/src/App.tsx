import { Suspense, lazy } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider, useAuth } from "./auth/AuthContext";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { HOME_POR_PAPEL } from "./auth/types";
import { Layout } from "./components/Layout";
import { Carregando } from "./components/Carregando";
import { Entrar } from "./pages/Entrar";
import { CriarConta } from "./pages/CriarConta";
import { EmCartaz } from "./pages/EmCartaz";
import { Sessao } from "./pages/Sessao";
import { Pedido } from "./pages/Pedido";
import { MeusIngressos } from "./pages/MeusIngressos";
import { IngressoCompartilhado } from "./pages/IngressoCompartilhado";
import { Organizador } from "./pages/Organizador";
import { NovaSessao } from "./pages/NovaSessao";
import { Salas } from "./pages/Salas";

/* A portaria carrega o leitor de QR, que sozinho pesa mais que o resto da
   aplicacao. Carregar sob demanda evita cobrar esse peso de quem so quer
   comprar ingresso — e a portaria e usada por um usuario, nao por todos. */
const Portaria = lazy(() =>
  import("./pages/Portaria").then((m) => ({ default: m.Portaria })),
);

/** A raiz manda cada papel para a sua área. Visitante vai para o cartaz, e não
 *  para o login: o catálogo é público e pedir conta para olhar é atrito sem
 *  contrapartida. Ver decisão D10. */
function Raiz() {
  const { user, carregando } = useAuth();
  if (carregando) return <Carregando />;
  return <Navigate to={user ? HOME_POR_PAPEL[user.role] : "/em-cartaz"} replace />;
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
          {/* Fora do layout: telas que não são do app autenticado */}
          <Route path="/entrar" element={<Entrar />} />
          <Route path="/criar-conta" element={<CriarConta />} />
          <Route path="/ingresso/:token" element={<IngressoCompartilhado />} />

          <Route element={<Layout />}>
            <Route path="/" element={<Raiz />} />

            {/* Público */}
            <Route path="/em-cartaz" element={<EmCartaz />} />
            <Route path="/sessao/:id" element={<Sessao />} />

            {/* Cliente */}
            <Route
              path="/pedido/:id"
              element={
                <ProtectedRoute permitido={["CUSTOMER"]}>
                  <Pedido />
                </ProtectedRoute>
              }
            />
            <Route
              path="/meus-ingressos"
              element={
                <ProtectedRoute permitido={["CUSTOMER"]}>
                  <MeusIngressos />
                </ProtectedRoute>
              }
            />

            {/* Organizador */}
            <Route
              path="/organizador"
              element={
                <ProtectedRoute permitido={["ORGANIZER"]}>
                  <Organizador />
                </ProtectedRoute>
              }
            />
            <Route
              path="/organizador/nova-sessao"
              element={
                <ProtectedRoute permitido={["ORGANIZER"]}>
                  <NovaSessao />
                </ProtectedRoute>
              }
            />
            <Route
              path="/organizador/salas"
              element={
                <ProtectedRoute permitido={["ORGANIZER"]}>
                  <Salas />
                </ProtectedRoute>
              }
            />

            {/* Portaria */}
            <Route
              path="/portaria"
              element={
                <ProtectedRoute permitido={["GATE"]}>
                  <Suspense fallback={<Carregando texto="Abrindo a portaria" />}>
                    <Portaria />
                  </Suspense>
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
