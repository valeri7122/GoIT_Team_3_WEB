## REST API Service for Posting, Transforming, and Commenting on Images
This is a REST API service that allows users to post images, transform them and comment on them. It is built using Python, FastAPI, SQLAlchemy, Cloudinary, and qrcode.

### Technologies
Python - Programming language
FastAPI - Web framework for building APIs
SQLAlchemy - Object-relational mapping library
Cloudinary - Cloud-based image and video management service
qrcode - QR code generator library

## Features
### The API supports the following features:

+ User registration and authentication
+ Uploading and storing images
+ Adding image tags and filtering images by tags
+ Transforming images (e.g., resizing, cropping, rotating, adding text or watermark)
+ Rating images and commenting on them

# Introduction

### Installation
## To install the dependencies, you can run the following command:

bash Copy code
```
pip install -r requirements.txt
```


After that, you can run the app using the following command:

bash Copy code
```
uvicorn app.main:app --reload
```



## How to use it?
### Authorization

+ Before use User should be signed up with a unique username, first name, last name, email, and password.
+ After signing up User should confirm their email.

### Features

+ Users can post images and add image tags.
+ Posted images can be rated and commented on by other users.

### Endpoints
The API supports the following endpoints described in project documentation [GoIT Team 3 WEB project](docs/_build/static/index.html)


### Our Team 3:
Developer: [Olga Nazarenko](https://github.com/OlgaNazarenko)  
Developer: [Serhii Pidkopai](https://github.com/SSP0d)  
Developer: [Valeri Tretiakov](https://github.com/valeri7122)  
Developer: [Taras Plaksii](https://github.com/TT1410)  
Developer + Scrum Muster: [Yaroslav Zhuk](https://github.com/YaroslavZq)  
Developer + Team Lead : [Andrii Cheban](https://github.com/AndrewCheUA)
