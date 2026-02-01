'use client';

import React, { useEffect, useRef, useState } from 'react';
import mapboxgl from 'mapbox-gl';
import MapboxDraw from '@mapbox/mapbox-gl-draw';

// Import Mapbox CSS (Crucial for proper rendering)
import 'mapbox-gl/dist/mapbox-gl.css';
import '@mapbox/mapbox-gl-draw/dist/mapbox-gl-draw.css';

// TypeScript Interfaces
interface MapboxMapProps {
  onLassoComplete: (polygon: any) => void; // Callback when user finishes drawing
}

// Access Token from Environment Variable
mapboxgl.accessToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN || '';

export default function MapboxMap({ onLassoComplete }: MapboxMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<mapboxgl.Map | null>(null);
  const draw = useRef<MapboxDraw | null>(null);
  
  // State to track if map is loaded
  const [isMapLoaded, setIsMapLoaded] = useState(false);

  useEffect(() => {
    if (map.current) return; // Initialize map only once

    // 1. Initialize Map
    map.current = new mapboxgl.Map({
      container: mapContainer.current!,
      style: 'mapbox://styles/mapbox/dark-v11', // Dark mode looks professional for BI
      center: [-122.5, 45.6], // Center on Clark County, WA
      zoom: 11,
      projection: { name: 'mercator' } // Standard projection
    });

    // 2. Add Navigation Controls (Zoom/Rotate)
    map.current.addControl(new mapboxgl.NavigationControl(), 'top-right');

    // 3. Initialize Lasso Draw Tool
    draw.current = new MapboxDraw({
      displayControlsDefault: false,
      controls: {
        polygon: true, // Allow drawing polygons (Lasso)
        trash: true    // Allow deleting selection
      },
      defaultMode: 'draw_polygon' // Start in drawing mode immediately (optional)
    });

    map.current.addControl(draw.current, 'top-left');

    // 4. Load Event & Layer Setup
    map.current.on('load', () => {
      setIsMapLoaded(true);

      // --- ADD PARCEL LAYER (Placeholder until your Tiles are ready) ---
      // In production, this will point to your Vector Tile Source
      /*
      map.current?.addSource('clark-parcels', {
        type: 'vector',
        url: 'mapbox://your-username.clark-county-tileset' 
      });

      map.current?.addLayer({
        'id': 'parcels-fill',
        'type': 'fill',
        'source': 'clark-parcels',
        'source-layer': 'parcels',
        'paint': {
          'fill-color': '#088',
          'fill-opacity': 0.4,
          'fill-outline-color': '#fff'
        }
      });
      */
    });

    // 5. Event Listeners for Drawing
    const updateArea = (e: any) => {
      const data = draw.current?.getAll();
      
      if (data && data.features.length > 0) {
        // Get the most recent polygon drawn
        const currentFeature = data.features[0]; 
        
        // Send GeoJSON to parent component (to trigger API)
        onLassoComplete(currentFeature.geometry);
      } else {
        // Clear selection if deleted
        onLassoComplete(null);
      }
    };

    map.current.on('draw.create', updateArea);
    map.current.on('draw.update', updateArea);
    map.current.on('draw.delete', updateArea);

    // Cleanup on unmount
    return () => {
      map.current?.remove();
    };
  }, []);

  return (
    <div className="relative w-full h-screen">
      {/* Map Container */}
      <div 
        ref={mapContainer} 
        className="absolute top-0 left-0 w-full h-full" 
      />
      
      {/* Optional: Loading Overlay */}
      {!isMapLoaded && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-80 z-50 text-white">
          <span>Loading Geospatial Engine...</span>
        </div>
      )}
      
      {/* Optional: Floating Info Panel */}
      <div className="absolute bottom-5 left-5 bg-black/80 text-white p-4 rounded-md backdrop-blur-md z-10 border border-gray-700 max-w-sm">
        <h3 className="font-bold text-sm uppercase tracking-wider text-green-400 mb-1">
          Command Center
        </h3>
        <p className="text-xs text-gray-300">
          Select the <span className="font-bold text-white">Polygon Tool</span> (top-left) 
          and draw a shape around lots to analyze.
        </p>
      </div>
    </div>
  );
}