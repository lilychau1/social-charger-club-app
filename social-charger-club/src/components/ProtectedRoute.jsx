// src/components/ProtectedRoute.js
import React from 'react';
import { Navigate } from 'react-router-dom'; 
import { useAuth } from '../contexts/AuthContext';

const ProtectedRoute = ({ element: Element, ...rest }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    // Optionally, show a loading spinner or placeholder while checking authentication status
    return <div>Loading...</div>;
  }

  if (!isAuthenticated) {
    // Redirect to sign-in page if not authenticated
    return <Navigate to="/signin" replace />;
  }

  return <Element {...rest} />;
};

export default ProtectedRoute;
