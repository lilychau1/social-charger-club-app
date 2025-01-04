// src/contexts/AuthContext.js
import React, { createContext, useState, useContext, useEffect } from 'react';

// Create a context for authentication
const AuthContext = createContext();

// Custom hook to use the AuthContext
export const useAuth = () => {
  return useContext(AuthContext);
};

// AuthProvider component
export const AuthProvider = ({ children }) => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null); 
  const [loading, setLoading] = useState(true); // Add loading state

  useEffect(() => {
    // Retrieve user data from localStorage if it exists
    const userData = localStorage.getItem('user');
    if (userData) {
      const parsedUser = JSON.parse(userData);
      setIsAuthenticated(true); 
      setUser(parsedUser); 
    }
    setLoading(false); // Set loading to false once user check is done
  }, []); 

  // Log in function
  const logIn = (userDetails) => {
    setIsAuthenticated(true);
    setUser(userDetails);
    localStorage.setItem('user', JSON.stringify(userDetails)); 
  };

  // Log out function
  const logOut = () => {
    setIsAuthenticated(false);
    setUser(null); 
    localStorage.removeItem('user'); 
  };

  return (
    <AuthContext.Provider value={{ isAuthenticated, logIn, logOut, user, loading }}>
      {children}
    </AuthContext.Provider>
  );
};
