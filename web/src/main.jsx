import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import AppShell from "./components/AppShell.jsx";
import App from "./App.jsx";
import Admin from "./pages/Admin.jsx";
import AdminBilling from "./pages/AdminBilling.jsx";
import ApiAccess from "./pages/ApiAccess.jsx";
import Billing from "./pages/Billing.jsx";
import Blog from "./pages/Blog.jsx";
import BlogPostPage from "./pages/BlogPost.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import NewProject from "./pages/NewProject.jsx";
import ProjectDetail from "./pages/ProjectDetail.jsx";
import Projects from "./pages/Projects.jsx";
import Reports from "./pages/Reports.jsx";
import RunDetail from "./pages/RunDetail.jsx";
import Runs from "./pages/Runs.jsx";
import Settings from "./pages/Settings.jsx";
import { getToken } from "./api.js";
import "./styles.css";

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/blog" element={<Blog />} />
        <Route path="/blog/:slug" element={<BlogPostPage />} />
        <Route path="/app" element={<AppShell />}>
          <Route index element={<Dashboard />} />
          <Route path="projects" element={<Projects />} />
          <Route path="projects/new" element={<NewProject />} />
          <Route path="projects/:id" element={<ProjectDetail />} />
          <Route path="runs" element={<Runs />} />
          <Route path="runs/:id" element={<RunDetail />} />
          <Route path="reports" element={<Reports />} />
          <Route path="api" element={<ApiAccess />} />
          <Route path="billing" element={<Billing />} />
          <Route path="settings" element={<Settings />} />
          <Route path="admin" element={<Admin />} />
          <Route path="admin/billing" element={<AdminBilling />} />
        </Route>
        <Route
          path="*"
          element={
            getToken() ? <Navigate to="/app" replace /> : <Navigate to="/login" replace />
          }
        />
      </Routes>
    </BrowserRouter>
  </StrictMode>
);
