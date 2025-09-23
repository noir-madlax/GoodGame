import React from "react";
import { HashRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import ModernDashboardLayout from "@/polymet/layouts/modern-dashboard-layout";
import ContentDashboard from "@/polymet/pages/content-dashboard";
import ContentRetrievalSettings from "@/polymet/pages/content-retrieval-settings";
import VideoAnalysisDetail from "@/polymet/pages/video-analysis-detail";
import MarkActionsPage from "@/polymet/pages/mark-actions";
import HandlingSuggestionsPage from "@/polymet/pages/handling-suggestions";
import { ProjectProvider, useProject } from "@/polymet/lib/project-context";

export default function ModernSentimentAnalysis() {
  const RootRedirect: React.FC = () => {
    const { settings } = useProject();
    const allowOverview = settings ? settings.nav_overview_enabled : true;
    const target = allowOverview ? "/dashboard" : "/marks";
    return <Navigate to={target} replace />;
  };
  return (
    <ProjectProvider>
      <Router>
        <Routes>
        {/* Redirect root based on project settings */}
        <Route path="/" element={<RootRedirect />} />

        {/* Content Dashboard */}
        <Route
          path="/dashboard"
          element={
            <ModernDashboardLayout>
              <ContentDashboard />
            </ModernDashboardLayout>
          }
        />

        {/* Content Marks & Actions */}
        <Route
          path="/marks"
          element={
            <ModernDashboardLayout>
              <MarkActionsPage />
            </ModernDashboardLayout>
          }
        />

        {/* Content Retrieval & Filter Settings (新增一级页面) */}
        <Route
          path="/search-filter"
          element={
            <ModernDashboardLayout>
              <ContentRetrievalSettings />
            </ModernDashboardLayout>
          }
        />

        {/* Video Analysis Detail */}
        <Route
          path="/detail/:id"
          element={
            <ModernDashboardLayout>
              <VideoAnalysisDetail />
            </ModernDashboardLayout>
          }
        />

        {/* Handling Suggestions */}
        <Route
          path="/suggestions/:id"
          element={
            <ModernDashboardLayout>
              <HandlingSuggestionsPage />
            </ModernDashboardLayout>
          }
        />

        {/* Fallback route */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Router>
    </ProjectProvider>
  );
}
