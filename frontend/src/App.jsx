import { useState } from 'react';
// Consolidated imports (removed duplicates)
import { MapContainer, TileLayer, FeatureGroup, Polygon, useMapEvents, Popup } from 'react-leaflet';
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

// Zoning Color Palette (KEEP THIS)
const ZONING_COLORS = {
    'R': '#facc15', // Yellow (Residential)
    'C': '#ef4444', // Red (Commercial)
    'I': '#a855f7', // Purple (Industrial)
    'A': '#22c55e', // Green (Agriculture)
    'DEFAULT': '#94a3b8' // Grey (Unknown)
  };
  
// Helper to pick color based on zoning code prefix (UPDATED WITH SAFETY PATCH)
const getZoningColor = (code) => {
  if (!code) return ZONING_COLORS.DEFAULT;

  // SAFETY PATCH: Force everything to be a string first
  const safeCode = String(code); 
  
  const prefix = safeCode.charAt(0).toUpperCase();
  return ZONING_COLORS[prefix] || ZONING_COLORS.DEFAULT;
};


function App() {
  const [position] = useState([45.63, -122.60]); // Clark County Center
  const [analysis, setAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // --- NEW: State for the Single Clicked Parcel ---
  const [selectedParcel, setSelectedParcel] = useState(null);

  // --- NEW: Handle Map Clicks ---
  function ParcelClicker() {
    useMapEvents({
      click: async (e) => {
        const { lat, lng } = e.latlng;
        console.log("Clicked at:", lat, lng);

        try {
          // Call the new Lookup endpoint
          const response = await axios.get('/api/v1/parcels/lookup', {
            params: { lat, lng }
          });

          if (response.data.found) {
            console.log("Found parcel:", response.data.data);
            setSelectedParcel(response.data.data);
          } else {
            console.log("No parcel found there.");
            setSelectedParcel(null); // Deselect if clicking empty space
          }
        } catch (error) {
          console.error("Lookup failed:", error);
        }
      }
    });
    return null;
  }

  // When a user finishes drawing a shape...
  const onCreated = async (e) => {
    const layer = e.layer;
    setLoading(true);

    const rawCoords = layer.getLatLngs()[0];
    const coordinates = rawCoords.map(c => [c.lng, c.lat]);
    coordinates.push([rawCoords[0].lng, rawCoords[0].lat]);

    try {
      const response = await axios.post('/api/v1/parcels/analyze', {
        type: "Polygon",
        coordinates: [coordinates]
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
// Calculate Zoning Stats
const zoningStats = analysis ? analysis.parcels.reduce((acc, parcel) => {
    const code = parcel.zoning_code || 'Unknown';
    const type = code.charAt(0).toUpperCase(); // Group by first letter (R, C, I, etc.)
    
    if (!acc[type]) acc[type] = { count: 0, acres: 0, codes: new Set() };
    acc[type].count += 1;
    acc[type].acres += parcel.acres || 0;
    acc[type].codes.add(code);
    return acc;
  }, {}) : null;




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
        
        {/* SIDEBAR DASHBOARD */}
        {analysis && (
          <div className="w-80 bg-slate-800 text-white p-6 overflow-y-auto z-10 shadow-2xl border-r border-slate-700 absolute left-0 top-0 bottom-0 bg-opacity-95 backdrop-blur-sm transition-all">
            <h2 className="text-2xl font-bold mb-4 text-white border-b border-slate-600 pb-2">Analysis Report</h2>
            <div className="space-y-6">
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
              {analysis.ai_summary && (
                <div className="bg-slate-900 p-4 rounded border border-slate-600">
                   <h3 className="font-bold text-yellow-500 mb-2">AI Insight</h3>
                   <p className="text-sm text-slate-300 leading-relaxed">{analysis.ai_summary}</p>
                </div>
              )}
            </div>

            {/* NEW: Zoning Mix Widget */}
            <div className="bg-slate-700 p-4 rounded-lg">
                <p className="text-slate-400 text-xs uppercase mb-3">Zoning Mix</p>
                <div className="space-y-3">
                  {zoningStats && Object.entries(zoningStats).map(([type, stats]) => (
                    <div key={type} className="flex items-center text-sm">
                      <div 
                        className="w-3 h-3 rounded-full mr-2" 
                        style={{ backgroundColor: ZONING_COLORS[type] || ZONING_COLORS.DEFAULT }}
                      />
                      <div className="flex-grow">
                        <span className="font-semibold">
                          {type === 'R' ? 'Residential' : 
                           type === 'C' ? 'Commercial' : 
                           type === 'I' ? 'Industrial' : 
                           type === 'A' ? 'Agriculture' : 'Other'}
                        </span>
                        <div className="text-xs text-slate-400">
                          {Array.from(stats.codes).slice(0, 3).join(', ')}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-bold">{stats.acres.toFixed(1)} ac</div>
                        <div className="text-xs text-slate-400">{stats.count} lots</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

            <button onClick={() => setAnalysis(null)} className="mt-8 w-full py-2 bg-red-500/20 hover:bg-red-500/40 text-red-200 rounded transition">
              Clear Results
            </button>
          </div>
        )}

        {/* MAP */}
        <div className="flex-grow relative">
          <MapContainer center={position} zoom={13} scrollWheelZoom={true} className="h-full w-full">
            
            {/* 1. ACTIVATE THE CLICK LISTENER HERE */}
            <ParcelClicker />

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
                  polygon: { allowIntersection: false, showArea: true, shapeOptions: { color: '#22d3ee' } },
                }}
              />
            </FeatureGroup>
            
            {/* 2. SHOW POPUP WHEN PARCEL IS SELECTED */}
            {selectedParcel && (
              <Popup 
                position={[
                  selectedParcel.geometry.coordinates[0][0][1], // Lat
                  selectedParcel.geometry.coordinates[0][0][0]  // Lng
                ]}
                onClose={() => setSelectedParcel(null)}
              >
                <div className="text-slate-900 font-sans min-w-[200px]">
                  <h3 className="font-bold text-lg border-b pb-1 mb-2">{selectedParcel.site_address || "Unknown Address"}</h3>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-500">Owner:</span>
                      <span className="font-semibold">{selectedParcel.owner_name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Value:</span>
                      <span className="font-semibold text-emerald-600">
                        ${Number(selectedParcel.total_value).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-500">Acres:</span>
                      <span className="font-semibold">{Number(selectedParcel.acres).toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              </Popup>
            )}

            {/* 3. HIGHLIGHT SELECTED PARCEL (Blue) */}
            {selectedParcel && selectedParcel.geometry && (
                 <Polygon 
                    positions={selectedParcel.geometry.coordinates[0].map(c => [c[1], c[0]])}
                    pathOptions={{ color: '#3b82f6', weight: 3, fillOpacity: 0.2 }}
                 />
            )}

    {/* DYNAMIC ZONING LAYERS */}
    {analysis && analysis.parcels && analysis.parcels.map((parcel) => (
                parcel.geometry && (
                    <Polygon 
                        key={parcel.parcel_id}
                        positions={parcel.geometry.coordinates[0].map(coord => [coord[1], coord[0]])}
                        pathOptions={{ 
                        color: getZoningColor(parcel.zoning_code), 
                        weight: 1, 
                        fillOpacity: 0.6 
                        }}
                    >
                    <Popup>
                        <strong>{parcel.site_address}</strong><br/>
                        Zoning: {parcel.zoning_code}
                    </Popup>
                    </Polygon>
                )
                ))}

          </MapContainer>
        </div>
      </div>
    </div>
  );
}

export default App;