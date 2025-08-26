"use client"

import dynamic from "next/dynamic";

// Mount the SPA for dynamic detail routes so hard refresh works
const App = dynamic(() => import("../../../src/App"), { ssr: false });

export default function DetailPage() {
  return <App />;
}


