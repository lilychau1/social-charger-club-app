import React from 'react';
import { Link } from 'react-router-dom';

const HomePage = () => {
  return (
    <div className="container mt-5">
      {/* Hero Section */}
      <div className="text-center">
        <h1 className="display-4">Join Us Today!</h1>
        <p className="lead">
          Sign up now and start your journey towards a sustainable future with SocialCharger Club.
        </p>
        <div className="d-flex justify-content-center">
          {/* Use Link component for navigation */}
          <Link to="/signin" className="btn btn-primary mx-2">
            Sign In
          </Link>
          <Link to="/signup" className="btn btn-outline-primary mx-2">
            Sign Up
          </Link>
        </div>
      </div>

      {/* New Content Section */}
      <div className="mt-5">
        <h2 className="text-center mb-4">Why Choose SocialCharger Club?</h2>
        <p className="lead text-center mb-5">
          We are dedicated to building a sustainable energy ecosystem. Join us and be a part of the solution!
        </p>

        {/* Bootstrap Cards to highlight features */}
        <div className="row row-cols-1 row-cols-md-3 g-4">
          {/* Feature 1 */}
          <div className="col">
            <div className="card shadow-sm">
              <img
                src="https://via.placeholder.com/150"
                className="card-img-top"
                alt="Feature 1"
              />
              <div className="card-body">
                <h5 className="card-title">Sustainable Energy</h5>
                <p className="card-text">
                  Be part of a community that is driving the future of clean, solar energy. Reduce your carbon footprint today!
                </p>
                <a href="#learn-more" className="btn btn-primary">
                  Learn More
                </a>
              </div>
            </div>
          </div>

          {/* Feature 2 */}
          <div className="col">
            <div className="card shadow-sm">
              <img
                src="https://via.placeholder.com/150"
                className="card-img-top"
                alt="Feature 2"
              />
              <div className="card-body">
                <h5 className="card-title">Affordable Solutions</h5>
                <p className="card-text">
                  Access affordable pricing options for solar products and services to make your transition to solar energy easier.
                </p>
                <a href="#learn-more" className="btn btn-primary">
                  Learn More
                </a>
              </div>
            </div>
          </div>

          {/* Feature 3 */}
          <div className="col">
            <div className="card shadow-sm">
              <img
                src="https://via.placeholder.com/150"
                className="card-img-top"
                alt="Feature 3"
              />
              <div className="card-body">
                <h5 className="card-title">Join a Thriving Community</h5>
                <p className="card-text">
                  Connect with like-minded individuals who are passionate about renewable energy and sustainable living.
                </p>
                <a href="#learn-more" className="btn btn-primary">
                  Learn More
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Call to Action Section */}
      <div className="bg-light p-5 mt-5 text-center">
        <h3>Ready to make a difference?</h3>
        <p className="lead">
          Join the SocialCharger Club today and start your journey towards a cleaner, more sustainable future.
        </p>
        <button className="btn btn-primary btn-lg">Get Started</button>
      </div>
    </div>
  );
};

export default HomePage;
