Some of the features provided by this application includes:

- Full authentication flow including user registration, login , password reset, password change and more.
- Signup/SignIn with social media platforms.
- Out-of-the-box email integration that can be controlled.
- Email template customization.
- and more …

Installation
NOTE : Before we start make sure you have created the django project with simple-jwt configured.

First we need to install two packages to handle our normal as well as social authentication integration.

pip install djoser
pip install social-django


Email configuration
- Go to your google account > manage google accounts > settings > 2-step verification > App password
- Create your app password and save it to your .env file on your project.


Integrating Google oAuth2
First of all we need to create an api app for google.

- Go to console.cloud.google.com > APIs & Services > Credentials > Create Credentials
- If it does not allow you to create the credential you might need to configure the OAuth consent screen which is just below the Credential option.
- In the consent screen choose the testing one where you need to add user email in which you want to test your applications authentication. Scroll down until you see the Test users and add some emails you want to test in.
- Click on create credential and it should allow you this time.
- Give a name for your app and add these addresses to the Authorized redirect URIs and hit save.

- Note: You need to add the redirect urls for both client and server and remember to add both localhost as well as the 127.0.0.1, as localhost might not work on the social authentication.

- After you have created your app google will provide you with two keys : Client_Secret and Client_Id. You need to save that to your .env file as you don’t want to expose the secret key.
- Now in your settings.py file add these google config.


Hurrah! You have completed the configuration part now’s the time to test if it works or not. For that go to the api client that you use, Postman or any other that you use. I use thunder client which is a vs code extension.

Here is the flow of how the authentication works :

- make a GET request to http://127.0.0.1:8000/auth/o/google-oauth2/?redirect_uri=http://localhost:3000/ (example)
- you will get a authorization_url. if you notice in this authorization_url there is a state presented . this is the 'state of server side'.
- Now you need to click the authorization_url link. Then you will be redirected to the google authentication page.
- After you choose your account you will be redirect to your redirect url with a state and a code in the url. Remember this state should be the same state as the server side state.
Make a POST request to http://127.0.0.1:8000/auth/o/google-oauth2/?state=''&code=''. if your states are not the same then you will get some issue else google will provide you with the access and refresh token for authentication.


Everytime you wanna login , you need to 
- make a request to http://127.0.0.1:8000/auth/o/google-oauth2/?redirect_uri=http://localhost:3000/ and 
- then to http://127.0.0.1:8000/auth/o/google-oauth2/?state=''&code='' thus you will get the same state.


Bonus:
Customizing email templates.

Djoser has it’s own email templates that are used for sending related emails during the authentication flow. We can customize these email templates and use our own with custom styling to add the company’s branding to it. Here are the steps you need to follow to use your own custom email template:

- First to view the templates used by djoser visit djoser’s github repo here and goto djoser > templates > email . Here you can see all the template used during the authentication process to send the email.
- Now you need to create your own html files. Create a folder inside the accounts app called templates > accounts > email then create your html files here, example: activation.html. It is recommeded to use the same name convention for the html files as in the djoser package.
- Now copy the html code from the original activation.html from the djoser package to your custom activate.html file and now you can start modifying the file according to your needs.# Boilerplate
