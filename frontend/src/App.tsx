import React from "react";
import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import ModernDashboardLayout from "@/polymet/layouts/modern-dashboard-layout";
import ContentDashboard from "@/polymet/pages/content-dashboard";
import VideoAnalysisDetail from "@/polymet/pages/video-analysis-detail";

export default function ModernSentimentAnalysis() {
  return (
    <Router>
      <Routes>
        {/* Redirect root to dashboard */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* Content Dashboard */}
        <Route
          path="/dashboard"
          element={
            <ModernDashboardLayout>
              <ContentDashboard />
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

        {/* Fallback route */}
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
}
