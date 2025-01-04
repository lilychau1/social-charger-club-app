import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

const NewUserDetails = () => {
  const { user } = useAuth();
  const [formFields, setFormFields] = useState([]);
  const [formData, setFormData] = useState({});
  const [loading, setLoading] = useState(false); // Track loading state
  const [error, setError] = useState(""); // Track error message
  const apiUrl = "YOUR_API_URL_HERE/api/user/new-user-details"; // Replace with your actual API URL
  const navigate = useNavigate();

  // Fetch form fields when user type is available
  useEffect(() => {
    const fetchFormFields = async () => {
      if (user && user.userType) {
        setLoading(true); // Start loading

        try {
          // Fetch form fields from the API based on the user type
          const response = await fetch(`${apiUrl}/form-fields`, {
            method: 'GET',
            headers: {
              'Content-Type': 'application/json',
            },
          });

          const result = await response.json();

          if (response.ok) {
            // Set the form fields based on user role
            let fields = { basic: [], consumer: [], producer: [] };

            const userRole = user.userType;
            if (userRole === 'consumer') {
              fields.basic = result.basic || [];
              fields.consumer = result.consumer || [];
            } else if (userRole === 'producer') {
              fields.basic = result.basic || [];
              fields.producer = result.producer || [];
            } else if (userRole === 'prosumer') {
              fields.basic = result.basic || [];
              fields.consumer = result.consumer || [];
              fields.producer = result.producer || [];
            }

            setFormFields(fields);
          } else {
            setError('Error fetching form fields');
          }
        } catch (err) {
          setError('Request failed');
        } finally {
          setLoading(false); // End loading
        }
      }
    };

    fetchFormFields();
  }, [user]);

  const handleInputChange = (e, key) => {
    const { name, value } = e.target;
    setFormData((prevData) => ({
      ...prevData,
      [key]: { ...prevData[key], [name]: value },
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true); // Set loading to true while submitting

    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          user_id: user.id,
          consumer_id: user.consumerId,
          producer_id: user.producerId,
          updates: formData,
        }),
      });

      const result = await response.json();

      if (response.ok) {
        alert('Data submitted successfully');
        navigate("/my-account");  // Redirect to My Account page after successful submission
      } else {
        setError('Error submitting data');
        console.error('Error:', result);
      }
    } catch (error) {
      setError('Request failed');
      console.error('Request failed:', error);
    } finally {
      setLoading(false); // End loading
    }
  };

  const renderInputField = (field, key) => {
    const { name, label, type, required, options } = field;

    if (type === 'select') {
      return (
        <div className="form-group mb-3" key={name}>
          <label htmlFor={name}>{label}</label>
          <select
            className="form-control"
            id={name}
            required={required}
            onChange={(e) => handleInputChange(e, key)}
          >
            {options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
      );
    }

    return (
      <div className="form-group mb-3" key={name}>
        <label htmlFor={name}>{label}</label>
        <input
          type={type}
          className="form-control"
          id={name}
          required={required}
          onChange={(e) => handleInputChange(e, key)}
        />
      </div>
    );
  };

  return (
    <div className="container mt-5">
      <h2>New User Details</h2>
      {error && <div className="alert alert-danger">{error}</div>}
      <form onSubmit={handleSubmit}>
        {Object.entries(formFields).map(([key, fields]) =>
          fields.length > 0 ? (
            <div key={key}>
              <div className="bg-secondary text-white p-2 mb-4 mt-4">
                <h5 className="font-weight-bold">
                  {key.charAt(0).toUpperCase() + key.slice(1)} Information
                </h5>
              </div>
              {fields.map((field) => renderInputField(field, key))}
            </div>
          ) : null
        )}
        <div className="form-group text-center mt-4">
          <button type="submit" className="btn btn-primary" disabled={loading}>
            {loading ? 'Submitting...' : 'Submit'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default NewUserDetails;
