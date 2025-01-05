import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import newUserDetailsFormFields from '../data/newUserDetailsFormFields.json';
import { useNavigate } from 'react-router-dom';

const NewUserDetails = () => {
  const { user } = useAuth();
  const [formFields, setFormFields] = useState([]);
  const [formData, setFormData] = useState({});
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
    setFormData((prevData) => ({
      ...prevData,
      [key]: { ...prevData[key], [name]: value },
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
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
        console.error('Error:', result);
        alert('Error submitting data');
      }
    } catch (error) {
      console.error('Request failed:', error);
      alert('Error submitting data');
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
          <button type="submit" className="btn btn-primary">
            Submit
          </button>
        </div>
      </form>
    </div>
  );
};

export default NewUserDetails;
