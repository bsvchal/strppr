import {
  PaymentElement, useElements, useStripe
} from "@stripe/react-stripe-js";
import React, { useState } from "react";
import SignupComplete from "./SignupComplete";
  
  const CardSetupForm = (props) => {
    const { selected, mode, details, customerId, learnerEmail, learnerName, onSuccessfulConfirmation } =
      props;
    const [paymentSucceeded, setPaymentSucceeded] = useState(false);
    const [error, setError] = useState(null);
    const [processing, setProcessing] = useState(false);
    const [last4, setLast4] = useState("");
    // TODO: Integrate Stripe
    const elements = useElements();
    const stripe = useStripe();
  
    const handleClick = async (e) => {
      // TODO: Integrate Stripe
      setProcessing(true);
      if (!stripe || !elements)
        return;

      if (mode === "update") {
        fetch(`/remove_payment_method/${customerId}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        }).then(response => response.json());
      }
        stripe.confirmSetup({
          elements,
          redirect: "if_required",
          confirmParams: {
            return_url: window.location.href,
            payment_method_data: {
              billing_details: {
                "email": learnerEmail,
                "name": learnerName 
              }
            }
          }
        }).then(result => {
          if (result.error) {
            setError(result.error.message);
          } else {
            const pmId = result.setupIntent.payment_method;
            fetch(`http://127.0.0.1:4242/payment-method?pm=${pmId}`)
              .then(response => response.json())
              .then(data => {
                setLast4(data.last4);
              });
            setPaymentSucceeded(true);
          }
          if (mode === "update") onSuccessfulConfirmation(customerId);
          setProcessing(false);
        }); 
    };

    if (selected === -1) return null;
    if (paymentSucceeded) return (
      <div className={`lesson-form`}>
        <SignupComplete
          active={paymentSucceeded}
          email={learnerEmail}
          last4={last4}
          customer_id={customerId}
        />
      </div>
    )
    return (
      // The actual checkout form, inside the !paymentSucceeded clause
        <div className={`lesson-form`}>
            <div className={`lesson-desc`}>
              <h3>Registration details</h3>
              <div id="summary-table" className="lesson-info">
                {details}
              </div>
              <div className="lesson-legal-info">
                Your card will not be charged. By registering, you hold a session
                slot which we will confirm within 24 hrs.
              </div>
              <div className="spinner" id="spinner" disabled={!processing || stripe}></div>
              <div className="lesson-grid">
                <div className="lesson-inputs">
                  <div className="lesson-input-box first">
                    <span>{learnerName} ({learnerEmail})</span>
                  </div>
                  <div className="lesson-payment-element">
                    {
                      <div>
                        <PaymentElement />
                        <button id="submit" disabled={!stripe || processing} onClick={e => handleClick(e)}>Submit</button>
                      </div>
                    }
                  </div>
                </div>
              </div>
              {error && (
                <div className="sr-field-error" id="card-errors" role="alert">
                  <div className="card-error" role="alert">
                    {error}
                  </div>
                </div>
              )}
            </div>
        </div>
    )
  };
  export default CardSetupForm;
  
