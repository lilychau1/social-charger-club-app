import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext'; // Adjust the path to where your context is located
import HomePage from './components/HomePage';
import SignIn from './components/SignIn';
import SignUp from './components/SignUp';
import ConfirmAccount from './components/ConfirmAccount';
import MyAccount from './components/MyAccount';
import NewUserDetails from './components/NewUserDetails';
import ChargingMap from './components/ChargingMap';
import Header from './components/Header';
import ProtectedRoute from './components/ProtectedRoute'; 
import './App.css';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div>
          {/* Global Navbar - Header Component */}
          <Header />

          {/* Routes for different pages */}
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/signin" element={<SignIn />} />
            <Route path="/signup" element={<SignUp />} />
            <Route path="/confirm-account" element={<ConfirmAccount />} />
            <Route path="/new-user-details" element={<NewUserDetails />} />
            <Route path="/charging-map" element={<ChargingMap />} />

            {/* Protect this route */}
            <Route
              path="/my-account"
              element={<ProtectedRoute element={<MyAccount />} />}
            />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
