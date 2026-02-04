import { useState } from 'react';
import { MapContainer, TileLayer, FeatureGroup, Polygon } from 'react-leaflet';
import { EditControl } from 'react-leaflet-draw';
import axios from 'axios';

// Fix for Leaflet's default icon path issues
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import 'leaflet-draw/dist/leaflet.draw.css';

// Fix marker icons (standard Leaflet bug in React)
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
    iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

function App() {
  const [position] = useState([45.63, -122.60]); // Clark County Center
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);

  // When a user finishes drawing a shape...
  const onCreated = async (e) => {
    const layer = e.layer;
    setLoading(true);

    // 1. Get Coordinates from Leaflet (Lat, Lng)
    // Leaflet gives us objects {lat: x, lng: y}
    const rawCoords = layer.getLatLngs()[0];

    // 2. Convert to GeoJSON format for PostGIS (Lng, Lat) !!! CRITICAL STEP
    const coordinates = rawCoords.map(c => [c.lng, c.lat]);
    
    // Close the loop (repeat first point at the end)
    coordinates.push([rawCoords[0].lng, rawCoords[0].lat]);

    try {
      // 3. Send to Backend
      // We use /api because vite.config.js proxies this to localhost:8000
      const response = await axios.post('/api/v1/parcels/analyze', {
        type: "Polygon",
        coordinates: [coordinates] // GeoJSON expects an array of rings
      });

      console.log("Analysis Results:", response.data);
      setAnalysis(response.data);
    } catch (error) {
      console.error("Error analyzing area:", error);
      alert("Failed to analyze area. Check backend console.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-screen flex-col font-sans">
      {/* HEADER */}
      <div className="bg-slate-900 text-white p-4 shadow-xl z-20 flex justify-between items-center border-b border-slate-700">
        <h1 className="text-xl font-bold tracking-wider text-cyan-400">Clark County Land Scout (REBA :)</h1>
        <div className="text-sm text-slate-400">
          {loading ? <span className="animate-pulse text-yellow-400">Processing GIS Data...</span> : "Ready to Scout"}
        </div>
      </div>

      <div className="flex-grow relative flex">
        
        {/* SIDEBAR DASHBOARD (Appears when we have data) */}
        {analysis && (
          <div className="w-80 bg-slate-800 text-white p-6 overflow-y-auto z-10 shadow-2xl border-r border-slate-700 absolute left-0 top-0 bottom-0 bg-opacity-95 backdrop-blur-sm transition-all">
            <h2 className="text-2xl font-bold mb-4 text-white border-b border-slate-600 pb-2">Analysis Report</h2>
            
            <div className="space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-1 gap-4">
                <div className="bg-slate-700 p-4 rounded-lg">
                  <p className="text-slate-400 text-xs uppercase">Total Parcels</p>
                  <p className="text-3xl font-bold">{analysis.total_parcels}</p>
                </div>
                
                <div className="bg-slate-700 p-4 rounded-lg">
                  <p className="text-slate-400 text-xs uppercase">Total Acres</p>
                  <p className="text-3xl font-bold text-emerald-400">
                    {analysis.total_acreage ? analysis.total_acreage.toFixed(2) : "0"}
                  </p>
                </div>

                <div className="bg-slate-700 p-4 rounded-lg">
                  <p className="text-slate-400 text-xs uppercase">Avg AI Score</p>
                  <p className="text-3xl font-bold text-cyan-400">
                    {analysis.average_score ? analysis.average_score.toFixed(1) : "0"} / 10
                  </p>
                </div>
              </div>

              {/* AI Summary Text */}
              {analysis.ai_summary && (
                <div className="bg-slate-900 p-4 rounded border border-slate-600">
                   <h3 className="font-bold text-yellow-500 mb-2">AI Insight</h3>
                   <p className="text-sm text-slate-300 leading-relaxed">{analysis.ai_summary}</p>
                </div>
              )}
            </div>
            
            <button 
              onClick={() => setAnalysis(null)}
              className="mt-8 w-full py-2 bg-red-500/20 hover:bg-red-500/40 text-red-200 rounded transition"
            >
              Clear Results
            </button>
          </div>
        )}

        {/* MAP */}
        <div className="flex-grow relative">
          <MapContainer center={position} zoom={13} scrollWheelZoom={true} className="h-full w-full">
            <TileLayer
              attribution='&copy; <a href="https://carto.com/">CARTO</a>'
              url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            />
            
            {/* THE DRAWING TOOL */}
            <FeatureGroup>
              <EditControl
                position="topright"
                onCreated={onCreated}
                draw={{
                  rectangle: false,
                  circle: false,
                  circlemarker: false,
                  marker: false,
                  polyline: false,
                  polygon: {
                    allowIntersection: false,
                    showArea: true,
                    shapeOptions: {
                      color: '#22d3ee' // Cyan line color
                    }
                  },
                }}
              />
            </FeatureGroup>
            
            {/* Highlight Selected Parcels (Optional: If backend returns geometry) */}
            {analysis && analysis.parcels && analysis.parcels.map((parcel) => (
               parcel.geometry && (
                 <Polygon 
                    key={parcel.parcel_id}
                    positions={parcel.geometry.coordinates[0].map(coord => [coord[1], coord[0]])}
                    pathOptions={{ color: 'orange', weight: 1, fillOpacity: 0.5 }}
                 />
               )
            ))}

          </MapContainer>
        </div>
      </div>
    </div>
  );
}

export default App;