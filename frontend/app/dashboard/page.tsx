"use client"

import React from "react";
import dynamic from "next/dynamic";

// Reuse SPA App but ensure /dashboard is directly routable in Next app router
const App = dynamic(() => import("../../src/App"), { ssr: false });

export default function DashboardPage() {
  return <App />;
}


