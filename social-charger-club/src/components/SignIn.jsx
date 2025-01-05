import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';  // Import useAuth to get logIn function

const SignIn = () => {
  const { logIn } = useAuth();  // Use logIn from AuthContext to store user data
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSignIn = async (e) => {
    e.preventDefault();

    if (!email || !password) {
      setError('Email and password are required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${import.meta.env.VITE_EV_CHARGING_API_GATEWAY_URL}/sign-in`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email,
          password: password,
        }),
      });

      const result = await response.json();
      setLoading(false);

      if (response.ok) {
        localStorage.setItem('idToken', result.idToken);  // Store token

        // Retrieve and store user details from the response
        const userDetails = result.user;

        logIn(userDetails); // Store the user data in the context

        alert('Sign in successful');

        // Check if it's the first login after account confirmation
        const isFirstLogin = sessionStorage.getItem('isFirstLogin');
        if (isFirstLogin === 'true') {
          sessionStorage.removeItem('isFirstLogin');
          navigate("/new-user-details"); // Redirect to New User Details page
        } else {
          navigate("/my-account"); // Redirect to My Account page on subsequent logins
        }
      } else {
        setError(result.error || 'Error during sign-in');
      }
    } catch (error) {
      setLoading(false);
      setError('Sign-in request failed');
      console.error('Sign-in failed:', error);
    }
  };

  return (
    <div className="container mt-5">
      <h2 className="text-center">Sign In</h2>
      <form onSubmit={handleSignIn} className="mt-4">
        <div className="mb-3">
          <label className="form-label">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="form-control"
            placeholder="Enter your email"
            required
          />
        </div>

        <div className="mb-3">
          <label className="form-label">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="form-control"
            placeholder="Enter your password"
            required
          />
        </div>

        {error && <div className="text-danger mb-3">{error}</div>}

        <button
          type="submit"
          className="btn btn-primary w-100"
          disabled={loading}
        >
          {loading ? 'Signing In...' : 'Sign In'}
        </button>
      </form>
    </div>
  );
};

export default SignIn;
