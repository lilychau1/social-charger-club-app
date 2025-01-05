import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext'; // Adjust path accordingly

const ProtectedRoute = ({ element }) => {
  const { isAuthenticated, loading } = useAuth();  // Get authentication state from AuthContext

  // If loading or not authenticated, redirect to sign-in
  if (loading) {
    return <div>Loading...</div>;  // Optionally display a loading spinner
  }

  if (!isAuthenticated) {
    return <Navigate to="/signin" replace />;  // Redirect to SignIn page if not authenticated
  }

  return element;  // Allow access to the protected route if authenticated
};

export default ProtectedRoute;
