import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import AppShell from "./components/AppShell.jsx";
import App from "./App.jsx";
import Admin from "./pages/Admin.jsx";
import AdminBilling from "./pages/AdminBilling.jsx";
import AdminBlog from "./pages/AdminBlog.jsx";
import AdminGoogle from "./pages/AdminGoogle.jsx";
import AdminSeo from "./pages/AdminSeo.jsx";
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
import ReportDetail from "./pages/ReportDetail.jsx";
import Reports from "./pages/Reports.jsx";
import RunDetail from "./pages/RunDetail.jsx";
import Runs from "./pages/Runs.jsx";
import Settings from "./pages/Settings.jsx";
import { getToken } from "./api.js";
import { AnalyticsLoader } from "./components/SeoHead.jsx";
import { initI18n } from "./i18n.js";
import "./styles.css";
import "./theme.css";
import "./landing.css";

initI18n();

createRoot(document.getElementById("root")).render(
    <StrictMode>
      <BrowserRouter>
        <AnalyticsLoader />
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
          <Route path="reports/:id" element={<ReportDetail />} />
          <Route path="api" element={<ApiAccess />} />
          <Route path="billing" element={<Billing />} />
          <Route path="settings" element={<Settings />} />
          <Route path="admin" element={<Admin />} />
          <Route path="admin/billing" element={<AdminBilling />} />
          <Route path="admin/blog" element={<AdminBlog />} />
          <Route path="admin/seo" element={<AdminSeo />} />
          <Route path="admin/google" element={<AdminGoogle />} />
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
