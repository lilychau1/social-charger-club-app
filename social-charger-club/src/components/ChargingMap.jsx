import React, { useState, useEffect, useCallback } from "react";
import L from "leaflet";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import awsconfig from "../aws-exports"; // Ensure this is your AWS config file

const ChargingMap = () => {
  const [stations, setStations] = useState([]);
  const [radius, setRadius] = useState(5); // Default radius in km
  const [postcode, setPostcode] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  // Construct the base URL dynamically from awsconfig
  const apiUrl = `${awsconfig.aws_api_gateway_url}/charging-point`; // This should be your API Gateway URL

  // Move handleViewDetails definition above initMap
  const handleViewDetails = async (stationId) => {
    try {
      const response = await axios.post(`${apiUrl}/get-station-details`, { stationId });
      const station = response.data.station;
      // Open the booking modal or navigate to a booking page
      navigate(`/booking/${stationId}`, { state: { station } });
    } catch (error) {
      console.error("Error fetching station details:", error);
      alert(`Error fetching station details: ${error.response?.status || error.message}`);
    }
  };

  // Memoize initMap to avoid unnecessary re-renders
  const initMap = useCallback(() => {
    const map = L.map("map").setView([51.505, -0.09], 13); // Default location

    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png").addTo(map);

    stations.forEach(station => {
      const marker = L.marker([station.latitude, station.longitude]).addTo(map);

      // Bind popup with the proper onClick handler
      marker.bindPopup(`
        <strong>${station.name}</strong><br>
        <b>Price:</b> ${station.price}<br>
        <b>Status:</b> ${station.status}<br>
        <button id="viewDetails-${station.id}">View Details</button>
      `);

      // Use event delegation to handle the click
      map.on('popupopen', (event) => {
        const { id } = event.popup._contentNode.querySelector('button').id.split('-');
        const button = event.popup._contentNode.querySelector('button');
        button.onclick = () => handleViewDetails(id); // Attach handleViewDetails function
      });
    });
  }, [stations, handleViewDetails]); // Don't forget to add handleViewDetails to the dependency array

  // Handle station search
  const handleSearch = async () => {
    if (!postcode) {
      alert("Please enter a postcode.");
      return;
    }

    setLoading(true);
    try {
      const response = await axios.post(`${apiUrl}/get-stations`, { postcode, radius });
      setStations(response.data.stations);
      setLoading(false);
    } catch (error) {
      setLoading(false);
      console.error("Error fetching stations:", error);
      alert(`Error fetching stations: ${error.response?.status || error.message}`);
    }
  };

  // Only initialize the map when stations are loaded
  useEffect(() => {
    if (stations.length) {
      initMap();
    }
  }, [stations, initMap]);

  return (
    <div className="container">
      <h1>Find Charging Stations</h1>
      <div className="form-group">
        <label>Postcode:</label>
        <input
          type="text"
          className="form-control"
          value={postcode}
          onChange={(e) => setPostcode(e.target.value)}
        />
      </div>
      <div className="form-group">
        <label>Radius (km):</label>
        <input
          type="number"
          className="form-control"
          value={radius}
          onChange={(e) => setRadius(e.target.value)}
        />
      </div>
      <button className="btn btn-primary" onClick={handleSearch} disabled={loading}>
        {loading ? "Loading..." : "Search"}
      </button>

      <div id="map" style={{ height: "500px", marginTop: "20px" }}></div>
    </div>
  );
};

export default ChargingMap;
