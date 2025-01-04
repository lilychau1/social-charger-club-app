import React, { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';

const MyAccount = () => {
  const { user } = useAuth(); // Get the authenticated user from context
  const [userData, setUserData] = useState(null);

  useEffect(() => {
    // Ensure user is available
    if (user) {
      const customUserType = user.userType; // Access custom:userType

      const mockUserData = {
        name: user.username,  // User's username from Cognito
        email: user.email,    // User's email from Cognito
        userType: customUserType || 'consumer', // Use custom:userType or default to 'consumer'
        usageStats: {
          sessions: 15,
          energyConsumed: 120.5,
          amountSpent: 150.75,
        },
        subscription: {
          plan: 'Basic Plan',
          renewalDate: '2024-12-31',
        },
        // Optional for producer/prosumer
        stationStats: {
          totalStations: 5,
          energySupplied: 1000.5,
          earnings: 2000.0,
        }
      };

      setUserData(mockUserData);  // Set real user data or mock data for now
    }
  }, [user]);  // Re-run the effect if the user context changes

  // Render consumer's content
  const renderConsumerContent = () => (
    <div>
      <h4>Your Usage Stats</h4>
      <p>Sessions: {userData.usageStats.sessions}</p>
      <p>Energy Consumed: {userData.usageStats.energyConsumed} kWh</p>
      <p>Amount Spent: ${userData.usageStats.amountSpent}</p>

      <h4>Your Subscription</h4>
      <p>Plan: {userData.subscription.plan}</p>
      <p>Renewal Date: {userData.subscription.renewalDate}</p>
    </div>
  );

  // Render producer's content
  const renderProducerContent = () => (
    <div>
      <h4>Your Energy Supply Stats</h4>
      <p>Energy Supplied: {userData.stationStats.energySupplied} kWh</p>
      <p>Earnings from Energy Supply: ${userData.stationStats.earnings}</p>
      <p>Total Stations: {userData.stationStats.totalStations}</p>

      <h4>Your Subscription</h4>
      <p>Plan: {userData.subscription.plan}</p>
      <p>Renewal Date: {userData.subscription.renewalDate}</p>
    </div>
  );

  // Render prosumer's content
  const renderProsumerContent = () => (
    <div>
      <h4>Your Usage Stats</h4>
      <p>Sessions: {userData.usageStats.sessions}</p>
      <p>Energy Consumed: {userData.usageStats.energyConsumed} kWh</p>
      <p>Amount Spent: ${userData.usageStats.amountSpent}</p>

      <h4>Your Energy Supply Stats</h4>
      <p>Energy Supplied: {userData.stationStats.energySupplied} kWh</p>
      <p>Earnings from Energy Supply: ${userData.stationStats.earnings}</p>
      <p>Total Stations: {userData.stationStats.totalStations}</p>

      <h4>Your Subscription</h4>
      <p>Plan: {userData.subscription.plan}</p>
      <p>Renewal Date: {userData.subscription.renewalDate}</p>
    </div>
  );

  // Return loading if userData is not yet loaded
  if (!userData) return <p>Loading...</p>;

  return (
    <div className="container mt-5">
      <h2>Your Account Information</h2>
      <div className="card">
        <div className="card-body">
          <h4>Personal Information</h4>
          <p>Name: {userData.name}</p>
          <p>Email: {userData.email}</p>

          {/* Check if userType is available and safely capitalize */}
          <p>User Type: {userData.userType ? userData.userType.charAt(0).toUpperCase() + userData.userType.slice(1) : 'Unknown'}</p>

          {/* Conditionally render content based on userType */}
          {userData.userType === 'consumer' && renderConsumerContent()}
          {userData.userType === 'producer' && renderProducerContent()}
          {userData.userType === 'prosumer' && renderProsumerContent()}
        </div>
      </div>
    </div>
  );
};

export default MyAccount;
