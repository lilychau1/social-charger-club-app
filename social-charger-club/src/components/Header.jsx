import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext'; // Use the AuthContext to access user data
import { FaUserCircle } from 'react-icons/fa';

const Header = () => {
  const { isAuthenticated, logOut, user } = useAuth(); // Get user and authentication status from context
  const [dropdownVisible, setDropdownVisible] = useState(false);

  const toggleDropdown = () => {
    setDropdownVisible((prevState) => !prevState);
  };

  const handleSignOut = () => {
    logOut(); // Call logOut to sign the user out
    setDropdownVisible(false); // Close the dropdown after signing out
  };

  return (
    <nav className="navbar navbar-expand-lg navbar-dark bg-primary">
      <div className="container-fluid">
        <Link className="navbar-brand" to="/" style={{ fontSize: '4rem' }}>
          SocialCharger Club
        </Link>

        <div className="collapse navbar-collapse">
          <ul className="navbar-nav ms-auto">
            {!isAuthenticated ? (
              <>
                <li className="nav-item">
                  <Link className="nav-link" to="/signin">
                    <button className="btn btn-primary">Sign In</button>
                  </Link>
                </li>
                <li className="nav-item">
                  <Link className="nav-link" to="/signup">
                    <button className="btn btn-outline-light">Sign Up</button>
                  </Link>
                </li>
              </>
            ) : (
              <>
                <li className="nav-item dropdown">
                  <button
                    className="nav-link dropdown-toggle btn"
                    onClick={toggleDropdown} // Handle dropdown toggle
                  >
                    <FaUserCircle size={30} />
                    {/* Show user's name or email */}
                    {user && <span className="ms-2">{user.name || user.email}</span>}
                  </button>

                  {dropdownVisible && (
                    <ul
                      className="dropdown-menu show dropdown-menu-end"
                      aria-labelledby="navbarDropdown"
                    >
                      {/* Display the user's name */}
                      <li>
                        <span className="dropdown-item-text">
                          Welcome, {user ? user.name : 'User'}
                        </span>
                      </li>

                      {/* Optionally display the email */}
                      {user && (
                        <li>
                          <span className="dropdown-item-text">
                            {user.email}
                          </span>
                        </li>
                      )}

                      <li>
                        <Link className="dropdown-item" to="/my-account">
                          Manage My Account
                        </Link>
                      </li>

                      {/* Sign out button */}
                      <li>
                        <button className="dropdown-item" onClick={handleSignOut}>
                          Sign Out
                        </button>
                      </li>
                    </ul>
                  )}
                </li>
              </>
            )}
          </ul>
        </div>
      </div>
    </nav>
  );
};

export default Header;
