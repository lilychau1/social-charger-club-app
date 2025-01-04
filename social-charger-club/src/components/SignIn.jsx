import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext"; // Assuming you still need the context for managing logged-in user

function SignIn() {
  const navigate = useNavigate();
  const { logIn } = useAuth(); // Access logIn from AuthContext

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false); // Track loading state for the button

  const handleSignIn = async (event) => {
    event.preventDefault();
    setLoading(true); // Set loading state

    // Prepare the payload for the API
    const loginPayload = {
      email,
      password,
    };

    try {
      // Replace with the actual API endpoint for login authentication
      const response = await fetch("YOUR_API_URL_HERE/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(loginPayload),
      });

      const data = await response.json();

      // Handle errors from the API (e.g., invalid credentials)
      if (!response.ok) {
        setLoading(false); // Set loading to false after request completes
        setError(data.message || "Login failed, please try again.");
        return;
      }

      // If login is successful, extract necessary user data (e.g., token, user details)
      const { token, user } = data;

      // Log in the user (store the token and user data)
      logIn({
        name: user.name,
        email: user.email,
        userType: user.userType, // Assuming userType is part of the user data
        token: token,
      });

      // Check if it's the first login after account confirmation
      const isFirstLogin = sessionStorage.getItem("isFirstLogin");
      if (isFirstLogin === "true") {
        sessionStorage.removeItem("isFirstLogin"); // Remove the flag after the first login
        navigate("/new-user-details"); // Redirect to new user details page
      } else {
        navigate("/my-account"); // Redirect to MyAccount page on subsequent logins
      }
    } catch (err) {
      setLoading(false); // Set loading to false after request completes
      setError("An error occurred during login. Please try again.");
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
            required
          />
        </div>
        {error && <div className="text-danger">{error}</div>}
        <button type="submit" className="btn btn-primary w-100" disabled={loading}>
          {loading ? "Signing In..." : "Sign In"}
        </button>
      </form>
    </div>
  );
}

export default SignIn;
