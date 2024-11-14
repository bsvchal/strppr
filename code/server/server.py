#! /usr/bin/env python3.6

"""
server.py
Stripe Card Payments Certification.
Python 3.9 or newer required.
"""

import datetime
import json
import os
import time
import stripe

# TODO: Integrate Stripe
from dotenv import find_dotenv, load_dotenv
from flask import Flask, jsonify, make_response, render_template, request
from flask_cors import CORS, cross_origin
import stripe.error

load_dotenv(find_dotenv())

PUBLISHABLE_API_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
SECRET_API_KEY = os.environ.get('STRIPE_SECRET_KEY')

stripe.api_key = SECRET_API_KEY

static_dir = str(os.path.abspath(os.path.join(
    __file__, "..", os.getenv("STATIC_DIR"))))
# TODO: Integrate Stripe


frontend = ""
if os.path.isfile("/".join([static_dir, "index.html"])):
    frontend = "vanilla"
else:
    frontend = "react"
    static_dir = str(os.path.abspath(
        os.path.join(__file__, "..", "./templates")))

server_dir = str(os.path.abspath(os.path.join(__file__, "../..")))

app = Flask(
    __name__, static_folder=static_dir, static_url_path="", template_folder=static_dir
)

cors = CORS(app)
app.config['CORS_HEADERS'] = 'X-Requested-With, Content-Type, Accept, Origin, Authorization, access-control-allow-origin'


@app.route("/", methods=["GET"])
def get_main_page():
    # Display checkout page
    if frontend == "vanilla":
        return render_template("index.html")
    else:
        return render_template("react_redirect.html")

# Fetch the Stripe publishable key
#
# Example call:
# curl -X GET http://localhost:4242/config \
#
# Returns: a JSON response of the pubblishable key
#   {
#        key: <STRIPE_PUBLISHABLE_KEY>
#   }


@app.route('/config', methods=['GET'])
def get_stripe_public_key():
    config = { 'key': PUBLISHABLE_API_KEY }
    # TODO: Integrate Stripe
    return jsonify(config), 200

# Milestone 1: Signing up
# Shows the lesson sign up page.


@app.post('/lessons')
def lessons():
    data = request.get_json()
    email = data['email']
    name = data['name']
    first_lesson = data['first_lesson']

    customer = stripe.Customer.list(limit=1, email=email)
    if customer.data != []:
        customer = customer.data.pop()
        return { 
            "error": "Customer already exists",
            "existing_customer": {
                "customer_id": customer.id,
                "customer_email": customer.email,
                "customer_name": customer.name
            }  
        }, 400

    customer = stripe.Customer.create(name=name, email=email, metadata={'first_lesson': first_lesson})
    setup_intent = stripe.SetupIntent.create(customer=customer.id, payment_method_types=["card"])

    return {
        "customer_id": customer.id,
        "client_secret": setup_intent.client_secret
    }


@app.get('/payment-method')
def get_payment_method():
    pm = request.args.get('pm')
    payment_method_response = stripe.PaymentMethod.retrieve(id=pm)
    return {'last4': payment_method_response.card.last4}


@app.get('/customer')
def get_customer():
    pm = request.args.get('pm')
    customer_payment_method_response = stripe.Customer.list_payment_methods(customer=pm, limit=1)
    if customer_payment_method_response.data == []:
        return {}, 400
    payment_method = customer_payment_method_response.data.pop()
    return {
        'customer': {
            'name': payment_method.billing_details.name,
            'email': payment_method.billing_details.email
        },
        'card': {
            'exp_month': payment_method.card.exp_month,
            'exp_year': payment_method.card.exp_year,
            'last4': payment_method.card.last4
        }
    }

@app.get('/lessons')
def get_lesson_page():
    # Display lesson signup
    if frontend == "vanilla":
        return render_template("lessons.html")
    else:
        return render_template("react_redirect.html")

# TODO: Integrate Stripe

# Milestone 2: '/schedule-lesson'
# Authorize a payment for a lesson
#
# Parameters:
# customer_id: id of the customer
# amount: amount of the lesson in cents
# description: a description of this lesson
#
# Example call:
# curl --header "Content-Type:application/json" -X POST http://localhost:4242/schedule-lesson
#   -d '{"customer_id": "cus_MbJLR8io8RpVBL", "amount": "4500", "description": "Lesson on Feb 25th"}'
#
# Returns: a JSON response of one of the following forms:
# For a successful payment, return the payment intent:
#   {
#        payment: <payment_intent>
#    }
#
# For errors:
#  {
#    error:
#       code: the code returned from the Stripe error if there was one
#       message: the message returned from the Stripe error. if no payment method was
#         found for that customer return an msg "no payment methods found for <customer_id>"
#    payment_intent_id: if a payment intent was created but not successfully authorized
# }


@app.route("/schedule-lesson", methods=["POST"])
def schedule_lesson():
    data = request.get_json()
    (customer_id, amount, description) = (data['customer_id'], data['amount'], data['description'])
    try:
        payment_method_response = stripe.Customer.list_payment_methods(customer=customer_id, limit=1)
        payment_method_id = payment_method_response.data.pop().id

        response = stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',
            capture_method='manual',
            payment_method=payment_method_id,
            customer=customer_id,
            description=description,
            metadata={
                'type': 'lessons-payment'
            },
            confirm=True,
            automatic_payment_methods={
                'enabled':True,
                'allow_redirects': 'never'
            }
        )

        return {
            'payment': response
        }, 200
    except Exception as exception:
        return {
            'error': {
                'code': exception.code,
                'message': exception.user_message
            }
        }, 400
    


# Milestone 2: '/complete-lesson-payment'
# Capture a payment for a lesson.
#
# Parameters:
# amount: (optional) amount to capture if different than the original amount authorized
#
# Example call:
# curl -X POST http://localhost:4242/complete_lesson_payment \
#  -d payment_intent_id=pi_XXX \
#  -d amount=4500
#
# Returns: a JSON response of one of the following forms:
#
# For a successful payment, return the payment intent:
#   {
#        payment: <payment_intent>
#    }
#
# for errors:
#  {
#    error:
#       code: the code returned from the error
#       message: the message returned from the error from Stripe
# }
#
@app.route("/complete-lesson-payment", methods=["POST"])
def complete_lesson_payment():
    data = request.get_json()
    payment_intent_id = data['payment_intent_id']

    try:
        payment_intent = None
        if 'amount' in data:
            amount = data['amount']
            payment_intent = stripe.PaymentIntent.capture(payment_intent_id, amount_to_capture=amount)
        else:
            payment_intent = stripe.PaymentIntent.capture(payment_intent_id)
        return {
            'payment': payment_intent
        }, 200
    except Exception as exception:
        return {
            'error': {
                'code': exception.code,
                'message': exception.user_message
            }
        }, 400


# Milestone 2: '/refund-lesson'
# Refunds a lesson payment.  Refund the payment from the customer (or cancel the auth
# if a payment hasn't occurred).
# Sets the refund reason to 'requested_by_customer'
#
# Parameters:
# payment_intent_id: the payment intent to refund
# amount: (optional) amount to refund if different than the original payment
#
# Example call:
# curl -X POST http://localhost:4242/refund-lesson \
#   -d payment_intent_id=pi_XXX \
#   -d amount=2500
#
# Returns
# If the refund is successfully created returns a JSON response of the format:
#
# {
#   refund: refund.id
# }
#
# If there was an error:
#  {
#    error: {
#        code: e.error.code,
#        message: e.error.message
#      }
#  }


@app.route("/refund-lesson", methods=["POST"])
def refund_lesson():
    data = request.get_json()
    payment_intent_id = data['payment_intent_id']

    try:
        refund = None
        if 'amonut' in data:
            amount = data['amount']
            refund = stripe.Refund.create(payment_intent=payment_intent_id, amount=amount)
        else:
            refund = stripe.Refund.create(payment_intent=payment_intent_id)

        return {
            'refund': refund.id
        }, 200
    except Exception as exception:
        return {
            'error': {
                'code': exception.code,
                'message': exception.user_message
            }
        }, 400


# Milestone 3: Managing account information
# Displays the account update page for a given customer


@app.route("/account-update/<customer_id>", methods=["GET"])
def get_account_page(customer_id):
    # Display account update page
    if frontend == "vanilla":
        return render_template("account-update.html")
    else:
        return render_template("react_redirect.html")


@app.post("/remove_payment_method/<customer_id>")
def remove_payment_method(customer_id):
    customer_payment_method_response = stripe.Customer.list_payment_methods(customer=customer_id, limit=1)
    if customer_payment_method_response.data == []:
        return {}, 400
    payment_method = customer_payment_method_response.data.pop()
    stripe.PaymentMethod.detach(payment_method=payment_method.id)
    return {}, 200


@app.post("/account-update/<customer_id>")
def update_account(customer_id):
    data = request.get_json()
    name = data['name']
    email = data['email']

    customer_response = stripe.Customer.list(limit=1, email=email)
    if customer_response.data != []:
        customer_response = customer_response.data.pop()
        if customer_response.id != customer_id:
            return { 
                "error": "Customer email already exists!",
                "existing_customer": {
                    "customer_id": customer_response.id,
                    "customer_email": customer_response.email,
                    "customer_name": customer_response.name
                }  
            }, 400
    
    updated_customer_response = stripe.Customer.modify(customer_id, name=name, email=email)
    setup_intent = stripe.SetupIntent.create(customer=customer_id, payment_method_types=["card"])
    return {
        'id': updated_customer_response.id,
        'client_secret': setup_intent.client_secret
    }, 200


# Milestone 3: '/delete-account'
# Deletes a customer object if there are no uncaptured payment intents for them.
#
# Parameters:
#   customer_id: the id of the customer to delete
# Changed Example from a POST to a GET. This is bc the -d command is used.
# Example request
#   curl -X POST http://localhost:4242/delete-account \
#    -d customer_id=cusXXX
#
#
# Returns 1 of 3 responses:
# If the customer had no uncaptured charges and was successfully deleted returns the response:
#   {
#        deleted: true
#   }
#
# If the customer had uncaptured payment intents, return a list of the payment intent ids:
#   {
#     uncaptured_payments: ids of any uncaptured payment intents
#   }
#
# If there was an error:
#  {
#    error: {
#        code: e.error.code,
#        message: e.error.message
#      }
#  }
#


@app.route("/delete-account/<customer_id>", methods=["POST"])
def delete_account(customer_id):
    # TODO: Integrate Stripe
    payment_intents_response = stripe.PaymentIntent.list(customer=customer_id)
    uncaptured_payments_ids = [payment_intent.id for payment_intent in payment_intents_response.data if payment_intent.amount_capturable > 0]
    if uncaptured_payments_ids != []:
        return {
            'uncaptured_payments': uncaptured_payments_ids
        }, 400
    
    try:
        stripe.Customer.delete(customer_id)
        return {
            'deleted': True
        }, 200
    except Exception as exception:
        return {
            'code': exception.error.code,
            'message': exception.error.message
        }, 400


# Milestone 4: '/calculate-lesson-total'
# Returns the total amounts for payments for lessons, ignoring payments
# for videos and concert tickets, ranging over the last 36 hours.
#
# Example call: curl -X GET http://localhost:4242/calculate-lesson-total
#
# Returns a JSON response of the format:
# {
#      payment_total: Total before fees and refunds (including disputes), and excluding payments
#         that haven't yet been captured.
#      fee_total: Total amount in fees that the store has paid to Stripe
#      net_total: Total amount the store has collected from payments, minus their fees.
# }
@app.route("/calculate-lesson-total", methods=["GET"])
def calculate_lesson_total():
    t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=36)
    unix = int(time.mktime(t.timetuple()))
    (payment_total, fee_total, net_total) = (0, 0, 0)
    transactions_response = stripe.BalanceTransaction.list()
    start = transactions_response.data[-1].id
    for transaction in transactions_response.data:
        if unix > transaction.created: 
            return {
                'payment_total': payment_total,
                'fee_total': fee_total,
                'net_total': net_total
            }
        if transaction.amount < 0: continue
        payment_total += transaction.amount
        fee_total += transaction.fee 
        net_total += transaction.net
    while transactions_response.has_more:
        transactions_response = stripe.BalanceTransaction.list(starting_after=start)
        start = transactions_response.data[-1].id
        for transaction in transactions_response.data:
            if unix > transaction.created: 
                return {
                    'payment_total': payment_total,
                    'fee_total': fee_total,
                    'net_total': net_total
                }
            if transaction.amount < 0: continue
            payment_total += transaction.amount
            fee_total += transaction.fee
            net_total += transaction.net

    return {
        'payment_total': payment_total,
        'fee_total': fee_total,
        'net_total': net_total
    }
    


# Milestone 4: '/find-customers-with-failed-payments'
# Returns any customer who meets the following conditions:
# The last attempt to make a payment for that customer failed.
# The payment method associated with that customer is the same payment method used
# for the failed payment, in other words, the customer has not yet supplied a new payment method.
#
# Example request: curl -X GET http://localhost:4242/find-customers-with-failed-payments
#
# Returns a JSON response with information about each customer identified and their associated last payment
# attempt and, info about the payment method on file.
# [
#     {
#         customer: {
#             id: customer.id,
#             email: customer.email,
#             name: customer.name,
#         },
#         payment_intent: {
#             created: created timestamp for the payment intent
#             description: description from the payment intent
#             status: the status of the payment intent
#             error: the reason that the payment attempt was declined
#         },
#         payment_method: {
#             last4: last four of the card stored on the customer
#             brand: brand of the card stored on the customer
#         }
#     },
#     {},
#     {},
# ]
#
@app.route("/find-customers-with-failed-payments", methods=["GET"])
def find_customers():
    result = []
    t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=36)
    unix = int(time.mktime(t.timetuple()))
    payment_intents_response = stripe.PaymentIntent.list()
    start = payment_intents_response.data[-1].id
    cancelled_intents = []
    for intent in payment_intents_response.data:
        if intent.created < unix: return jsonify(result)
        if intent.last_payment_error is not None: cancelled_intents.append(intent)
    for intent in cancelled_intents:
        customer_payment_methods = stripe.Customer.list_payment_methods(customer=intent.customer, limit=1)

        if customer_payment_methods.data != [] and customer_payment_methods.data.pop().id != intent.last_payment_error.payment_method.id: continue
        result.append({
            'customer': {
                'id': intent.customer,
                'email': intent.last_payment_error.payment_method.billing_details.email,
                'name': intent.last_payment_error.payment_method.billing_details.name
            },
            'payment_intent': {
                'created': intent.created,
                'description': intent.description,
                'status': 'failed',
                'error': intent.last_payment_error.decline_code
            },
            'payment_method': {
                'last4': intent.last_payment_error.payment_method.card.last4,
                'brand': intent.last_payment_error.payment_method.card.brand
            }
        })

    while payment_intents_response.has_more:
        payment_intents_response = stripe.PaymentIntent.list(starting_after=start)
        start = payment_intents_response.data[-1].id
 
        cancelled_intents = []
        for intent in payment_intents_response.data:
            if intent.created < unix: return jsonify(result)
            if intent.last_payment_error is not None: cancelled_intents.append(intent)
        for intent in cancelled_intents:
            customer_payment_methods = stripe.Customer.list_payment_methods(customer=intent.customer, limit=1)

            if customer_payment_methods.data != [] and customer_payment_methods.data.pop().id != intent.last_payment_error.payment_method.id: continue
            result.append({
                'customer': {
                    'id': intent.customer,
                    'email': intent.last_payment_error.payment_method.billing_details.email,
                    'name': intent.last_payment_error.payment_method.billing_details.name
                },
                'payment_intent': {
                    'created': intent.created,
                    'description': intent.description,
                    'status': 'failed',
                    'error': intent.last_payment_error.decline_code
                },
                'payment_method': {
                    'last4': intent.last_payment_error.payment_method.card.last4,
                    'brand': intent.last_payment_error.payment_method.card.brand
                }
            })

    return jsonify(result) 



if __name__ == "__main__":
    app.run()
