import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import newUserDetailsFormFields from '../data/newUserDetailsFormFields.json';
import { useNavigate } from 'react-router-dom';

const NewUserDetails = () => {
  const { user } = useAuth();
  const [formFields, setFormFields] = useState([]);
  const [formData, setFormData] = useState({});
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const apiUrl = `${import.meta.env.VITE_EV_CHARGING_API_GATEWAY_URL}/store-new-user-details`;
  const navigate = useNavigate(); // Initialize navigate function

  useEffect(() => {
    if (user && user.userType) {
      const userRole = user.userType;
      let fields = { basic: [], consumer: [], producer: [] };

      if (userRole === 'consumer') {
        fields.basic = newUserDetailsFormFields.basic || [];
        fields.consumer = newUserDetailsFormFields.consumer || [];
      } else if (userRole === 'producer') {
        fields.basic = newUserDetailsFormFields.basic || [];
        fields.producer = newUserDetailsFormFields.producer || [];
      } else if (userRole === 'prosumer') {
        fields.basic = newUserDetailsFormFields.basic || [];
        fields.consumer = newUserDetailsFormFields.consumer || [];
        fields.producer = newUserDetailsFormFields.producer || [];
      }

      setFormFields(fields);
    }
  }, [user]);

  const handleInputChange = (e, key) => {
    const { name, value } = e.target;

    // Ensure the name is not empty before updating formData
    if (!name || name.trim() === '') {
      console.error('Invalid input name:', name);
      return; // Ignore invalid inputs with no name
    }

    setFormData((prevData) => ({
      ...prevData,
      [key]: { ...prevData[key], [name]: value },
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!user || !user.id) {
      setErrorMessage("User information is not available.");
      return;
    }

    console.log("Form data being submitted:", formData);

    const payload = {
      userId: user.id,
      consumerId: user.consumerId,
      producerId: user.producerId,
      updates: formData,
    };

    setLoading(true);
    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      const result = await response.json();
      setLoading(false);

      if (response.ok) {
        alert('Data submitted successfully');
        navigate("/my-account");
      } else {
        console.error('Error:', result);
        setErrorMessage(result.error || 'Error submitting data');
      }
    } catch (error) {
      setLoading(false);
      console.error('Request failed:', error);
      setErrorMessage('Error submitting data');
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
          name={name} // Ensure the name attribute is properly set
          required={required}
          onChange={(e) => handleInputChange(e, key)}
        />
      </div>
    );
  };

  return (
    <div className="container mt-5">
      <h2>New User Details</h2>
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
        {errorMessage && <div className="alert alert-danger">{errorMessage}</div>}
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
