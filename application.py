import os
import requests
import json
from flask import Flask, session,render_template,request,redirect,url_for,jsonify,flash
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import generate_password_hash,check_password_hash



app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")



# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"),pool_size=20, max_overflow=0)
gr_key=os.getenv("GR_key")

db = scoped_session(sessionmaker(bind=engine))

#index
@app.route("/")
def index():

    if 'email_id' in session:
        if session['email_id']:
            if session['name']:
                message = 'Logged in as %s' % session['name']
                return render_template ("index.html",account_details = message)
        else:
            return render_template("login.html")
    else:
        return render_template("login.html")

#register
@app.route("/register", methods=["GET","POST"])
def register():
    if 'email_id' in session:
        if session['email_id']:
            if session['name']:
                message = 'Logged in as %s' % session['name']
                return render_template ("index.html",message = message)

    if request.method == 'POST':
        try:
            email_id = request.form.get("email_id")
            password = request.form.get("password")
            name = request.form.get("name")
            confirm_password = request.form.get("confirmpassword")

        except ValueError:
            return render_template("register.html",err_msg="email id or password or name is required")
        

        #password length check
        if not len(password)>=6:
            password_length_err_msg = "Password length must be atleast 6 characters"
            error ="PASSWORD_LENGTH_ERROR"
            return render_template("register.html",err_msg=password_length_err_msg,type_err_msg= error,email = email_id,name=name)
        
        # check if both confirm password and password match

        if password!=confirm_password:
            confirm_password_err_msg = "Password did not match"
            error = 'PASSWORD_NOT_MATCH'
            return render_template("register.html",err_msg=confirm_password_err_msg,type_err_msg= error, email = email_id,name=name)

        if db.execute("select * from users where email_id = :email_id",{"email_id": email_id}).rowcount==0:
        # new user so register

            hash_password = generate_password_hash(password,"sha256")  
             
            db.execute("insert into users(email_id,password,name) values (:email_id,:password, :name)",
            {"email_id":email_id,"password":hash_password ,"name":name})
            
            db.commit()
            flash(u'Welcome , You were successfully registered. Please Login  ')
            return render_template("login.html")

        else:
            # display error message
            session['email_id']=""
            session['name']=""
            email_address_not_available_err_msg = "Sorry,the email address is already registered!"
            error = 'email_error'
           
            return render_template("register.html",err_msg=email_address_not_available_err_msg,type_err_msg= error)
    else:
        return render_template("register.html")
        
#login
@app.route("/login", methods=["GET","POST"])
def login():
    if 'email_id' in session:
        if session['email_id']:
            if session['name']:
                message = 'Logged in as %s' % session['name']
                return render_template ("index.html",account_details = message)

       
            
    if request.method == 'POST':
        
        email_id = request.form["email_id"]
        password = request.form["password"]
        
        
        users  = db.execute("select email_id,password,name from users where email_id=:email_id",{"email_id": email_id}).fetchall()

        #user not found
        if len(users)== 0:
            email_not_found = 'User not found'
            error ="EMAIL_NOT_FOUND"
            return render_template("login.html",err_msg=email_not_found,type_err_msg= error)
        else:
            # password check from DB
            for u in users:
                if u.email_id == email_id and (check_password_hash(u.password, password)):
                    session['name']= u.name 
                    session['email_id']=u.email_id
                    return redirect(url_for('index'))  
                else:
                    wrong_password = 'Wrong Password'
                    error ="WRONG_PASSWORD"
                    return render_template("login.html",err_msg=wrong_password,type_err_msg= error,email = u.email_id)
    else:

        return render_template("login.html")

#verify account
@app.route("/verifyaccount",methods=["GET","POST"])
def verifyaccount():
    if 'email_id' in session:
        if session['email_id']:
            if session['name']:
                message = 'Logged in as %s' % session['name']
                return render_template ("index.html",account_details = message)

    if request.method == 'POST':

        try:
            email_id = request.form.get("email_id")
            user_name = request.form.get("name")
        except ValueError:
            return render_template("authenticate.html",err_msg="email id and user name is required")

        user  = db.execute("select * from users where email_id=:email_id",{"email_id": email_id}).fetchall()
        # not user found
        if len(user)== 0:
            email_not_found = 'Email address not found'
            error ="EMAIL_NOT_FOUND"
            return render_template("authenticate.html",err_msg=email_not_found,type_err_msg=error,name=user_name)
        else:
            #verify
            for u in user:
                if u.email_id==email_id and u.name==user_name:
                    verification_status = 1
                    flash(u'Account verified sucessfully.')
                    return render_template("passwordchange.html",email=email_id,verification_status=1)
                else:
                    verification_status = 0
                    user_name_not_matched = 'User name not found'
                    error = 'NAME_NOT_FOUND'
                    return render_template("authenticate.html",err_msg=user_name_not_matched,type_err_msg=error,email=email_id)
    else:
        return render_template("authenticate.html")

#change password
@app.route("/changepassword/<int:verification_status>",methods=["GET","POST"])
def changepassword(verification_status):
    if 'email_id' in session:
        if session['email_id']:
            if session['name']:
                message = 'Logged in as %s' % session['name']
                return render_template ("index.html",account_details = message)

    if request.method == 'POST':
        
        try:
            email_id = request.form.get("email_id")
            new_password = request.form.get("password")
            confirm_password = request.form.get("confirmpassword")

        except ValueError:
            return render_template("passwordchange.html",err_msg="email id or password is required",verification_status=verification_status)
        
        user = db.execute("select * from users where email_id = :email_id",{"email_id": email_id}).fetchall()
        
        #email check
        if len(user) == 0:
            email_not_found = 'Email Address not found'
            error ="EMAIL_NOT_FOUND"
            return render_template("passwordchange.html",err_msg=email_not_found,type_err_msg= error,verification_status=verification_status)
        
        #password check
        if not len(new_password)>=6:
            password_length_err_msg = "Password length must be atleast 6 characters"
            error ="PASSWORD_LENGTH_ERROR"
            return render_template("passwordchange.html",err_msg=password_length_err_msg,type_err_msg= error,email = email_id,verification_status=verification_status)
        
        #password match
        if new_password!=confirm_password:
            confirm_password_err_msg = "Password did not match"
            error = 'PASSWORD_NOT_MATCH'
            return render_template("passwordchange.html",err_msg=confirm_password_err_msg,type_err_msg= error, email = email_id,verification_status=verification_status) 


        #update DB
        for u in user:
            if u.email_id == email_id:
                hash_password = generate_password_hash(new_password,"sha256") 
                db.execute("update  users set password=:password where email_id=:email_id",{"password":hash_password,"email_id":email_id})
                db.commit()
                flash(u'Welcome ,You changed your password successfully')
                return render_template("login.html")
    else:
       return render_template("passwordchange.html")

#logout
@app.route("/logout")
def logout():

    session.pop('email_id',None)
    session.pop('name',None)
    flash(u'Logged out successfully')
    return redirect(url_for('index'))

#search
@app.route("/search",methods=["GET","POST"])
def search():
    if 'email_id' in session:
        if session['email_id']:
            if session['name']:
                message = 'Logged in as %s' % session['name']
        else:
            return render_template("login.html",message="you are not logged in")   
    

 
        if request.method == 'POST':
            query = request.form["search"]
            # searchby = request.form['searchvia']

            #empty query
            if query == "":
                error ="No results"
                return render_template("index.html",error = error, account_details=message)
        
            else:
                query=query.strip()
                q1 = f"%{query}%".upper()
                search_msg= "Showing results"
                search_msg_no_results =""

                books = db.execute("select isbn,title,author,year from books where upper(isbn) like :isbn or upper(title) like :title or upper(author) like :author ",{"isbn": q1,"title":q1, "author" :q1}).fetchall() 
                
                #Handling partial query
                if len(books)== 0:
                    search_msg_no_results +='No results found for'
                    q2=""
                    if len(query)>0:
                        q2=query[0]
                        for i in range(1,len(query)):
                            q2+="%"
                        q2 = f"{q2}".upper()
                        books = db.execute("select isbn,title,author,year from books where upper(isbn) like :isbn or upper(title) like :title or upper(author) like :author ",{"isbn": q2,"title":q2, "author" :q2}).fetchall() 
                    
                
                
                average=[]

                #No books found
                if len(books) == 0:
                    error ="No books found"
                    return render_template("index.html",error=error,account_details=message)
                for b in books:
                    
                    average_rating = db.execute("select cast (avg(rating) AS DECIMAL(10,2)) from reviews where isbn =:isbn", {"isbn":b.isbn}).fetchall()

                    bookname =b.title
                    avg =average_rating[0][0]
                    if avg!=None:
                        average.append(avg)
    
            
                    return render_template("index.html",books=books,account_details=message,search_msg=search_msg,search_msg_no_results=search_msg_no_results,query=query,bookname=bookname)
        else:
            return redirect(url_for('index'))
    else:
        return render_template("login.html",message="you are not logged in")
        
#show book details based on author or title
@app.route("/books/<string:b>/<booksearchby>",methods=["GET"])
def books(b,booksearchby):  
    average = []
    goodreads_avg=[]
    goodreads_numberofrating=[]
    googlebookdescription=[]
    googlebookimage=[]
    googlebooknumberofrating=[]
    googlebookavg=[]
    goodreadslinks=[]
    googlebookpublisher=[]
    googlebooklinks=[]
    numberofreviews=[]
    if 'email_id' in session:
        if session['email_id']:
            if session['name']:
                message = 'Logged in as %s' % session['name']
        else:
            return render_template("login.html",message="you are not logged in")

   
        b = f"{b}".upper()
        
        if booksearchby =="title":

            book = db.execute("select isbn,title,author,year from books where upper(title)=:title",{"title":b}).fetchall()
            
        elif booksearchby == "author":
            
            book = db.execute("select isbn,title,author,year from books where upper(author)=:author",{"author":b}).fetchall()
        else:
            return render_template("index.html",search_err= " 500 Internal Server Error  ",account_details=message)

        if len(book) == 0:
            return render_template("index.html",search_err= "500 Internal Server Error",account_details=message)
        
        #get reviews for the book
        
        for b in book:
            average_rating = db.execute("select  avg(reviews.rating) as average_score from reviews where isbn =:isbn", {"isbn":b.isbn}).fetchall()
            review = db.execute("select contents, rating,reviews.email_id,name from reviews inner join users on users.email_id=reviews.email_id  where isbn =:isbn ", {"isbn":b.isbn}).fetchall() 
            numberofreviews.append(len(review))
            avg = average_rating[0][0]
            
            if avg==None:
                avg=0
            avg=float('%.2f' %(avg))
            average.append(avg)

            #Good Reads  API
            if not os.getenv("GR_key"):
                raise RuntimeError("Good reads key not set")

            gr_key=os.getenv("GR_key")
            response = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": gr_key, "isbns": b.isbn})
            
            
           
            if response.status_code == 200:
                data =response.json()
                goodreads_avg.append(data['books'][0]['average_rating'])
                goodreads_numberofrating.append(data['books'][0] ['work_ratings_count'])
                goodreadslink = "https://www.goodreads.com/search?utf8=%E2%9C%93&q="+ f"{b.title}"
                goodreadslinks.append(goodreadslink)
            
            # Google books API

            googleBooksearch= "https://www.googleapis.com/books/v1/volumes?q=" + f"{b.isbn}" + "+" + "isbn"
            googleBookresponse=requests.get(googleBooksearch)

            if googleBookresponse.status_code == 200:
                googleBookdata =googleBookresponse.json()

                
                
                
                if googleBookdata["totalItems"] > 0 :
                    googlebookDict = googleBookdata["items"][0]["volumeInfo"]
                    
                    #description
                    if "description" in googlebookDict:
                        description=googlebookDict["description"]
                        googlebookdescription.append(description)
                    else:
                        googlebookdescription.append("null")
                   
                    #image
                    if "imageLinks" in googlebookDict:
                        if "thumbnail" in googlebookDict["imageLinks"]:
                            googlebookimage.append(googlebookDict["imageLinks"]["thumbnail"])
                        elif "smallThumbnail" in googlebookDict["imageLinks"]:
                            googlebookimage.append(googlebookDict["imageLinks"]["smallThumbnail"])
                        else:
                            googlebookimage.append("null")

                    else:
                        googlebookimage.append("null")

                    #ratings
                    if "averageRating" in googlebookDict:
                        googlebookavg.append(googlebookDict["averageRating"])
                    else:
                        googlebookavg.append("null")
                    
                    if "ratingsCount" in googlebookDict:
                        googlebooknumberofrating.append(googlebookDict["ratingsCount"])
                    else:
                        googlebooknumberofrating.append("null")
                

                    #publisher
                    if "publisher" in googlebookDict:
                        
                        googlebookpublisher.append(googlebookDict["publisher"])
                    else:
                        googlebookpublisher.append("null")

                    #googlebookid
                    if "id" in googleBookdata["items"][0]:

                        googlebookid=googleBookdata["items"][0]["id"]
                        googlebooklink = "https://books.google.com/books?id="+ f"{googlebookid}"
                        googlebooklinks.append(googlebooklink)
                    else:
                        googlebooklinks.append("#")
                
        
        return render_template("book.html",book=book,  booksearchby=booksearchby,review=review,numberofreviews=numberofreviews,average_rating=average,goodreads_avg=goodreads_avg, goodreads_numberofrating=goodreads_numberofrating, googlebookdescription=googlebookdescription,googlebooknumberofrating=googlebooknumberofrating,googlebookimage=googlebookimage,googlebookavg=googlebookavg,goodreadslinks=goodreadslinks,googlebookpublisher=googlebookpublisher,googlebooklinks=googlebooklinks,account_details=message)
    else:
        return render_template("login.html",message="you are not logged in")


        
#write review
@app.route("/review/<string:isbn>",methods=["GET","POST"])
def review(isbn):
    if 'email_id' in session:
        if session['email_id']:
            if session['name']:
                user_email=session['email_id']
                message = 'Logged in as %s' % session['name']
        else:
            return render_template("login.html",message="you are not logged in")

        #review =[]
        allreviews = dict()
        value = request.values 
        userReview=request.form['review']
        for item in value.items():
            allreviews[item[0]]=item[1]

        
        key ="'rating'"
        
        if db.execute("select email_id from users where email_id=:email_id",{"email_id":user_email}).rowcount !=0: 
            
            if db.execute("select isbn,email_id from reviews where isbn=:isbn and email_id=:email_id ",{"isbn":isbn,"email_id":user_email}).rowcount == 0:
                #user's first and only review
                if 'rating' in allreviews.keys():
                    rev= db.execute("insert into reviews(contents,rating,isbn,email_id) values (:contents,:rating,:isbn,:email_id)",{"contents":allreviews["review"],"rating":allreviews["rating"],"isbn":isbn,"email_id":user_email})
                    db.commit()
                    return render_template("message.html",review_sucess = "You have sucessfully submitted your review",account_details =message)
                

                else:
                    
                    if allreviews["review"] != "":
                        
                        rev= db.execute("insert into reviews(contents,isbn,email_id) values (:contents,:isbn,:email_id)",{"contents":allreviews["review"],"isbn":isbn,"email_id":user_email})
                        
                        db.commit()
                        return render_template("message.html",review_sucess = "You have sucessfully submitted your review",account_details =message)
                    else:
                        return render_template("message.html",emptyreview = "You cannot give an empty rating and comment",account_details =message)
            else:
                return render_template("message.html", reviewerr = "You already gave a review",account_details =message)
        else:
            session['email_id']=""
            session['name']=""
            return render_template("login.html",message= " Please create an account first")
    else: 
        return render_template("login.html",message="you are not logged in")

#api
@app.route("/api/<isbn>",methods=["GET"])
def book_api(isbn):
   
    
    book =db.execute("select count(reviews.email_id) as review_count,books.isbn,title,author,year,avg(reviews.rating) as average_score from books left join reviews on books.isbn=reviews.isbn where books.isbn=:isbn group by books.isbn",{"isbn":isbn}).fetchone()
    if book == None:
        return jsonify({"error": "Invalid isbn number", "status_code":404}),404

    rating=dict(book.items())
    if rating['average_score'] != None:
        rating['average_score'] =float('%.2f' %(rating['average_score']))  
    
    if rating['average_score'] == None:
        rating['average_score']=0
    return jsonify(rating)

#view my reviews
@app.route("/myreviews")
def myreviews():
    if 'email_id' in session:
        if session['email_id']:
            if session['name']:
                user_email=session['email_id']
                message = 'Logged in as %s' % session['name']
        else:
            return render_template("login.html",message="you are not logged in")

        allreviews = db.execute("select reviews.isbn,rating,contents,title from reviews inner join books on books.isbn=reviews.isbn  where email_id=:email_id",{"email_id":user_email}).fetchall()
        if len(allreviews) ==0:
            no_reviews_found_msg = "No reviews found"
            return render_template("reviews.html", account_details=message,err_msg=no_reviews_found_msg)
        else:
            
           
            return render_template("reviews.html",reviews=allreviews,account_details=message)
    else: 
        return render_template("login.html",message="you are not logged in")

        
    
    

    
    

