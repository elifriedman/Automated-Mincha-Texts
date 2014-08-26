Automated-Mincha-Texts
======================

An automated Mincha texting system. It sends out a text asking whether people are available to daven and manages their responses.

The application is in communication with an email account (currently it only supports IMAP and SMTP) and processes all incoming messages to that account.

Users interact with the application by sending emails or text messages to the email address with a message containing a 1 or 2 letter status code.

The following are a list of status codes to be put into the body of your email / txt:

| Email Body     |  Result / Meaning |
| ------------   | ----------------- |
| a[YOUR NAME]   | add yourself to the contact list. For example, I would text: ```aEli Friedman``` |
| y              | As a response to a request for Mincha, this says, "Yes, I can make it." |
| [1-9]          | As a response to a request for Mincha, this says, "N people can make it" where N is a number from 1 to 9.|
| i              | A request for information about the status of the next Mincha. You'll receive a response within a minute or two. |
