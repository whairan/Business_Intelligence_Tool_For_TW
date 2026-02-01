'use client';

import MapboxMap from '@/components/map/MapboxMap';

export default function Dashboard() {
  
  const handleAnalysis = (geometry: any) => {
    if (!geometry) {
      console.log("Selection cleared");
      return;
    }
    
    console.log("Lasso Geometry Captured:", geometry);
    // TODO: Send this 'geometry' to your FastAPI backend 
    // fetch('http://localhost:8000/api/analyze', { ... })
  };

  return (
    <main className="flex min-h-screen flex-col">
      <MapboxMap onLassoComplete={handleAnalysis} />
    </main>
  );
}