import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

const SignUp = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [username, setUsername] = useState("");
  const [userType, setUserType] = useState("consumer");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const navigate = useNavigate();

  const validateEmail = (email) => {
    const regex = /^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}$/;
    return regex.test(email);
  };

  const validatePassword = (password) => {
    const minLength = 8;
    const hasUppercase = /[A-Z]/.test(password);
    const hasLowercase = /[a-z]/.test(password);
    const hasNumber = /[0-9]/.test(password);
    const hasSpecialChar = /[!@#$%^&*(),.?":{}|<>]/.test(password);
    return password.length >= minLength && hasUppercase && hasLowercase && hasNumber && hasSpecialChar;
  };

  const handleSignUp = async (e) => {
    e.preventDefault();
    setError("");
  
    // Validation
    if (!validateEmail(email)) {
      setError("Please enter a valid email.");
      return;
    }
    if (!validatePassword(password)) {
      setError("Password must meet the complexity requirements.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }
    if (!username) {
      setError("Please enter a username.");
      return;
    }
  
    setLoading(true);
  
    // Prepare the payload for the API
    const userPayload = {
      email,
      username,
      userType,
      password,
    };
  
    try {
      // Fetch the API URL from environment variables
      const apiGatewayUrl = process.env.REACT_APP_API_GATEWAY_URL;
  
      // Send data to the API Gateway
      const response = await fetch(`${apiGatewayUrl}/register-user`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(userPayload),
      });
  
      const responseText = await response.text();
      console.log("API Response Text:", responseText);
  
      const responseData = JSON.parse(responseText); // Assuming the response body is JSON
  
      if (!response.ok) {
        throw new Error(responseData.error || "Failed to register user.");
      }
  
      // On success, navigate to the next page
      navigate("/confirm-account", { state: { email: email } });
  
    } catch (err) {
      setLoading(false);
      setError(`Error: ${err.message}`);
    }
  };
  
  return (
    <div className="container mt-5">
      <h2 className="text-center">Sign Up</h2>
      <form onSubmit={handleSignUp} className="mt-4">
        {/* Email Field */}
        <div className="mb-3">
          <label htmlFor="email" className="form-label">Email</label>
          <input
            type="email"
            id="email"
            className="form-control"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>

        {/* Username Field */}
        <div className="mb-3">
          <label htmlFor="username" className="form-label">Username</label>
          <input
            type="text"
            id="username"
            className="form-control"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
        </div>

        {/* Password Field */}
        <div className="mb-3 position-relative">
          <label htmlFor="password" className="form-label">Password</label>
          <input
            type={showPassword ? "text" : "password"} // Toggle password visibility
            id="password"
            className="form-control"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button
            type="button"
            className="btn btn-link position-absolute top-50 end-0 translate-middle-y"
            onClick={() => setShowPassword(!showPassword)} // Toggle the showPassword state
          >
            {showPassword ? "Hide" : "Show"}
          </button>
        </div>

        {/* Confirm Password Field */}
        <div className="mb-3 position-relative">
          <label htmlFor="confirmPassword" className="form-label">Confirm Password</label>
          <input
            type={showConfirmPassword ? "text" : "password"} // Toggle confirm password visibility
            id="confirmPassword"
            className="form-control"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />
          <button
            type="button"
            className="btn btn-link position-absolute top-50 end-0 translate-middle-y"
            onClick={() => setShowConfirmPassword(!showConfirmPassword)} // Toggle showConfirmPassword
          >
            {showConfirmPassword ? "Hide" : "Show"}
          </button>
        </div>

        {/* User Type Selector */}
        <div className="mb-3">
          <label htmlFor="userType" className="form-label">User Type</label>
          <select
            id="userType"
            className="form-select"
            value={userType}
            onChange={(e) => setUserType(e.target.value)}
          >
            <option value="consumer">Consumer</option>
            <option value="producer">Producer</option>
            <option value="prosumer">Prosumer</option>
          </select>
        </div>

        {/* Error Message */}
        {error && <p className="text-danger">{error}</p>}

        {/* Submit Button */}
        <button type="submit" className="btn btn-primary w-100" disabled={loading}>
          {loading ? "Signing Up..." : "Sign Up"}
        </button>
      </form>
    </div>
  );
};

export default SignUp;
