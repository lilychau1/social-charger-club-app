import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

const ConfirmAccount = () => {
  const [confirmationCode, setConfirmationCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [error, setError] = useState('');
  const location = useLocation();
  const navigate = useNavigate();

  // Retrieve the email from the state passed during navigation
  const email = location.state?.email;

  const handleConfirmAccount = async (e) => {
    e.preventDefault();

    if (!confirmationCode) {
      setError('Please enter the confirmation code');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_EV_CHARGING_API_GATEWAY_URL}/confirm-user`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email,
          confirmationCode: confirmationCode,
        }),
      });

      const result = await response.json();
      setLoading(false);

      if (response.ok) {
        alert('Account successfully confirmed!');
        // After confirmation, mark the user as first-time login
        sessionStorage.setItem('isFirstLogin', 'true'); // Store flag in sessionStorage
        navigate('/signin'); // Redirect to sign-in page
      } else {
        setError(result.error || 'Error confirming account');
      }
    } catch (error) {
      setLoading(false);
      setError('Request failed');
      console.error('Error confirming account:', error);
    }
  };

  const handleResendCode = async () => {
    setResendLoading(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_EV_CHARGING_API_GATEWAY_URL}/resend-confirmation-code`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email,
        }),
      });

      const result = await response.json();
      setResendLoading(false);

      if (response.ok) {
        alert('Confirmation code resent successfully!');
      } else {
        setError(result.error || 'Error resending confirmation code');
      }
    } catch (error) {
      setResendLoading(false);
      setError('Request failed');
      console.error('Error resending confirmation code:', error);
    }
  };

  return (
    <div className="container mt-5">
      <h2 className="text-center">Confirm Your Account</h2>
      <form onSubmit={handleConfirmAccount} className="mt-4">
        {/* Display Email as a Disabled Textbox */}
        <div className="mb-3">
          <label className="form-label">Email</label>
          <input
            type="email"
            value={email || ''}
            className="form-control"
            disabled
          />
        </div>

        <div className="mb-3">
          <label className="form-label">Confirmation Code</label>
          <input
            type="text"
            value={confirmationCode}
            onChange={(e) => setConfirmationCode(e.target.value)}
            className="form-control"
            placeholder="Enter the code sent to your email"
            required
          />
        </div>
        {error && <div className="text-danger mb-3">{error}</div>}
        
        <button
          type="submit"
          className="btn btn-primary w-100"
          disabled={loading}
        >
          {loading ? 'Confirming...' : 'Confirm Account'}
        </button>
      </form>

      {/* Resend Code Section */}
      <div className="text-center mt-3">
        <button
          type="button"
          className="btn btn-link"
          onClick={handleResendCode}
          disabled={resendLoading}
        >
          {resendLoading ? 'Resending...' : 'Resend Confirmation Code'}
        </button>
      </div>
    </div>
  );
};

export default ConfirmAccount;
