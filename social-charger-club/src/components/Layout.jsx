// src/components/Layout.js
import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext'; // We'll use context to manage auth state

const Layout = ({ children }) => {
  const { currentUser, logout } = useAuth(); // Get current user and logout function from context

  return (
    <div>
      {/* Upper Banner with Mint Color and Bootstrap Styling */}
      <div className="container-fluid bg-success text-white py-4">
        <div className="row">
          {/* Middle - "SocialCharger Club" */}
          <div className="col text-center">
            <h1 className="display-3 text-white fw-bold">SocialCharger Club</h1>
            <p className="lead">Empowering the Future of Green Energy</p>
          </div>

          {/* Right - Dynamic Sign In/Sign Up or My Account */}
          <div className="col d-flex justify-content-end align-items-center">
            {currentUser ? (
              <div className="dropdown">
                <button
                  className="btn btn-light btn-lg dropdown-toggle"
                  type="button"
                  id="accountDropdown"
                  data-bs-toggle="dropdown"
                  aria-expanded="false"
                >
                  <i className="bi bi-person-circle"></i> My Account
                </button>
                <ul className="dropdown-menu" aria-labelledby="accountDropdown">
                  <li><Link className="dropdown-item" to="/account">Manage My Account</Link></li>
                  <li><Link className="dropdown-item" to="#" onClick={logout}>Log Out</Link></li>
                  {/* Add any other options you like */}
                  <li><Link className="dropdown-item" to="/settings">Settings</Link></li>
                </ul>
              </div>
            ) : (
              <>
                <div className="me-3">
                  <Link to="/signin" className="btn btn-light btn-lg">Sign In</Link>
                </div>
                <div>
                  <Link to="/signup" className="btn btn-outline-light btn-lg">Sign Up</Link>
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Page Content */}
      <div className="container mt-5">
        {children} {/* Render the page-specific content */}
      </div>

      {/* Footer Section */}
      <div className="bg-dark text-white text-center py-4 mt-5">
        <p>&copy; 2024 SocialCharger Club. All Rights Reserved.</p>
      </div>
    </div>
  );
};

export default Layout;
